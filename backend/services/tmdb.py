"""TMDB (The Movie Database) — русскоязычный поиск фильмов И сериалов.

OMDB — англоязычный, кириллический запрос там почти ничего не найдёт, а
сериалы по русскому названию он не находит вовсе. TMDB официально поддерживает
любой язык через ``language=ru-RU`` и хорошо покрывает международные и
российские фильмы И сериалы (с русскими названиями).

Что делаем:
1. Поиск ``/search/movie`` или ``/search/tv`` (``language=ru-RU``) → TMDB id'ы.
   Хиты локально ре-ранжируем по близости названия (``text_match``), чтобы
   старый оригинал не тонул под более «популярным» ремейком. Год из «Название
   (1975)» используем как мягкий тай-брейк, НЕ как жёсткий фильтр TMDb: даты
   релиза в TMDb часто на год расходятся (фестиваль/прокат/ТВ), и строгий фильтр
   просто выкинул бы нужный фильм.
2. Для каждого хита достаём IMDb id, чтобы связать запись с OMDB-метадатой. Но
   если IMDb-связки нет (частый случай у старых/советских фильмов) — хит больше
   НЕ выбрасываем: отдаём синтетический ключ ``tmdb:movie:<id>`` /
   ``tmdb:tv:<id>``, по которому метадату строим прямо из TMDb (``get_by_key``).
3. Конвертируем в ``OMDBSearchResult`` — стандартный «карточный» формат.

Ключ — обобщённый внешний id (как ``work_key`` у книг): ``tt…`` → OMDB/IMDb,
``tmdb:…`` → TMDb. Диспетчеризацию делает ``title_search.get_movie_by_key``.

Конфигурация: ``TMDB_API_KEY`` в .env. Если ключа нет — сервис тихо ничего
не возвращает, и пайплайн откатывается на OMDB+LLM-перевод.
Ключ бесплатный, выпускается на https://www.themoviedb.org/settings/api.
"""

from __future__ import annotations

import asyncio
from typing import Optional

import httpx

from backend.config import TMDB_API_KEY, TMDB_BASE_URL
from backend.models.movie import MovieBase, OMDBSearchResult
from backend.services.text_match import extract_year, title_score


# TMDB иногда возвращает мусорные совпадения (порно, чужие языки и т.п.). Берём
# top-N после локального ре-ранжирования; держим запас (>5), чтобы старый фильм,
# проигравший ремейку в популярности, всё равно попал в выдачу.
_MAX_SEARCH_RESULTS = 10
_MAX_CAST = 10
_TMDB_POSTER_BASE = "https://image.tmdb.org/t/p/w500"
_TMDB_LOGO_BASE = "https://image.tmdb.org/t/p/original"
_TMDB_KEY_PREFIX = "tmdb:"

# Movie и TV отличаются именами полей и тем, откуда брать imdb_id. Держим эти
# различия в одном месте, чтобы логика поиска (``_search``) оставалась общей.
_KIND = {
    "movie": {
        "search_path": "/search/movie",
        "title_keys": ("title", "original_title"),
        "date_key": "release_date",
        # imdb_id и детали лежат прямо в /movie/{id}.
        "imdb_path": "/movie/{id}",
        "detail_path": "/movie/{id}",
    },
    "tv": {
        "search_path": "/search/tv",
        "title_keys": ("name", "original_name"),
        "date_key": "first_air_date",
        # у сериалов imdb_id отдаёт только отдельная ручка external_ids.
        "imdb_path": "/tv/{id}/external_ids",
        "detail_path": "/tv/{id}",
    },
}


def is_tmdb_key(key: str) -> bool:
    """Ключ-указатель на TMDb-источник (зеркало ``is_google_key`` у книг)."""
    return bool(key) and key.startswith(_TMDB_KEY_PREFIX)


def parse_tmdb_key(key: str) -> Optional[tuple[str, str]]:
    """``tmdb:movie:123`` → ``("movie", "123")``. None, если формат не наш."""
    if not is_tmdb_key(key):
        return None
    parts = key.split(":")
    if len(parts) != 3 or parts[1] not in _KIND or not parts[2].isdigit():
        return None
    return parts[1], parts[2]


class TMDBService:
    def __init__(self) -> None:
        self.api_key = TMDB_API_KEY
        self.base_url = TMDB_BASE_URL

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def search(
        self, query: str, *, language: str = "ru-RU",
    ) -> list[OMDBSearchResult]:
        """Ищет фильмы (back-compat: исходная сигнатура сервиса)."""
        return await self._search(query, "movie", language=language)

    async def search_tv(
        self, query: str, *, language: str = "ru-RU",
    ) -> list[OMDBSearchResult]:
        """Ищет сериалы. TMDb знает русские названия сериалов, а OMDB по
        кириллице их не находит вообще — это «другое место» для сериалов."""
        return await self._search(query, "tv", language=language)

    async def search_any(
        self, query: str, *, language: str = "ru-RU",
    ) -> list[OMDBSearchResult]:
        """Фильмы + сериалы одним вызовом: фильмы первыми, дедуп по ключу."""
        movies = await self.search(query, language=language)
        tv = await self.search_tv(query, language=language)

        seen = {r.imdb_id for r in movies}
        merged = list(movies)
        for r in tv:
            if r.imdb_id not in seen:
                seen.add(r.imdb_id)
                merged.append(r)
        return merged

    async def _search(
        self, query: str, kind: str, *, language: str,
    ) -> list[OMDBSearchResult]:
        """Общая логика поиска для фильмов и сериалов (различия — в ``_KIND``)."""
        if not self.enabled or not query.strip():
            return []

        cfg = _KIND[kind]
        title_query, year = extract_year(query)
        search_query = title_query or query.strip()

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Год НЕ шлём в TMDb как фильтр (его даты часто на год расходятся) —
            # ниже он работает мягким бонусом в ``_hit_rank``.
            params = {
                "api_key": self.api_key,
                "query": search_query,
                "language": language,
                "include_adult": "false",
            }
            try:
                search_resp = await client.get(
                    f"{self.base_url}{cfg['search_path']}", params=params,
                )
                search_resp.raise_for_status()
            except httpx.HTTPError as exc:
                print(f"[tmdb] {kind} search failed: {exc}")
                return []

            payload = search_resp.json() or {}
            hits = [h for h in (payload.get("results") or []) if h.get("id")]
            # Ре-ранжирование: ближайшее по названию — выше, совпавший год —
            # сильный бонус. Stable-sort по исходному индексу сохраняет порядок
            # TMDb (по популярности) на равных очках.
            ranked = sorted(
                enumerate(hits),
                key=lambda iv: (-self._hit_rank(iv[1], cfg, search_query, year), iv[0]),
            )
            hits = [h for _, h in ranked][:_MAX_SEARCH_RESULTS]
            if not hits:
                return []

            # Параллельно тянем imdb_id — N маленьких запросов быстрее цепочки.
            imdb_ids = await asyncio.gather(*[
                self._fetch_imdb_id(client, hit["id"], cfg["imdb_path"])
                for hit in hits
            ])

        results: list[OMDBSearchResult] = []
        for hit, imdb_id in zip(hits, imdb_ids):
            title = next((hit.get(k) for k in cfg["title_keys"] if hit.get(k)), "")
            date = hit.get(cfg["date_key"]) or ""
            poster_path = hit.get("poster_path")
            poster_url = f"{_TMDB_POSTER_BASE}{poster_path}" if poster_path else None
            # Нет IMDb id → синтетический ключ вместо отбрасывания: старые фильмы
            # без IMDb-связки тоже попадают в выдачу и сохраняются (get_by_key).
            external_id = imdb_id or f"{_TMDB_KEY_PREFIX}{kind}:{hit['id']}"

            results.append(OMDBSearchResult(
                imdb_id=external_id,
                title=title,
                year=date[:4] if date else "",
                poster_url=poster_url,
            ))

        return results

    @staticmethod
    def _hit_rank(hit: dict, cfg: dict, query: str, year: Optional[int]) -> float:
        """Оценка хита: лучшее совпадение по любому из названий + бонус за год.

        Год сравниваем с допуском ±1: даты релиза в TMDb регулярно на год
        отличаются от «народного» (премьера на фестивале / прокат / ТВ-эфир),
        поэтому «(1975)» должен поднимать и фильм, помеченный 1976-м.
        """
        best = max(
            (title_score(query, hit.get(k)) for k in cfg["title_keys"] if hit.get(k)),
            default=0.0,
        )
        if year:
            hit_year = (hit.get(cfg["date_key"]) or "")[:4]
            if hit_year.isdigit() and abs(int(hit_year) - year) <= 1:
                best += 0.5
        return best

    async def _fetch_imdb_id(
        self, client: httpx.AsyncClient, tmdb_id: int, imdb_path: str,
    ) -> str | None:
        """Достаёт imdb_id (вида ``tt1234567``) из детальной ручки TMDb."""
        try:
            resp = await client.get(
                f"{self.base_url}{imdb_path.format(id=tmdb_id)}",
                params={"api_key": self.api_key},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            print(f"[tmdb] imdb id fetch failed for {tmdb_id}: {exc}")
            return None

        # TMDB иногда отдаёт пустую строку — нормализуем в None.
        return (resp.json() or {}).get("imdb_id") or None

    async def get_by_key(self, key: str) -> Optional[MovieBase]:
        """Полная ``MovieBase`` по синтетическому ключу ``tmdb:movie|tv:<id>``.

        Источник метадаты для фильмов/сериалов, у которых нет IMDb id (их OMDB
        не знает). Тянем ``/movie/{id}`` или ``/tv/{id}`` на ru-RU c кредитами.
        ``imdb_rating`` оставляем ``None`` — TMDb ``vote_average`` это не IMDb,
        подмешивать его под меткой IMDb было бы неверно.
        """
        parsed = parse_tmdb_key(key)
        if not parsed or not self.enabled:
            return None
        kind, tmdb_id = parsed
        cfg = _KIND[kind]

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(
                    f"{self.base_url}{cfg['detail_path'].format(id=tmdb_id)}",
                    params={
                        "api_key": self.api_key,
                        "language": "ru-RU",
                        "append_to_response": "credits",
                    },
                )
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                print(f"[tmdb] detail fetch failed for {key}: {exc}")
                return None
            data = resp.json() or {}

        return self._parse_details(kind, key, data, cfg)

    async def resolve_tmdb_ref(self, key: str) -> Optional[tuple[str, str]]:
        """``(media_type, tmdb_id)`` для ключа фильма.

        Синтетический ключ ``tmdb:movie|tv:<id>`` разбираем напрямую; реальный
        IMDb id (``tt…``) резолвим через ``/find`` (external_source=imdb_id).
        None, если TMDb выключен / формат чужой / в ``/find`` ничего не нашлось.
        """
        parsed = parse_tmdb_key(key)
        if parsed:
            return parsed
        if not self.enabled or not key or not key.startswith("tt"):
            return None
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/find/{key}",
                    params={"api_key": self.api_key, "external_source": "imdb_id"},
                )
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                print(f"[tmdb] find failed for {key}: {exc}")
                return None
            data = resp.json() or {}
        # Фильм приоритетнее сериала, если вдруг IMDb id оказался в обоих.
        for kind, results_key in (("movie", "movie_results"), ("tv", "tv_results")):
            results = data.get(results_key) or []
            if results and results[0].get("id"):
                return kind, str(results[0]["id"])
        return None

    @staticmethod
    def _normalize_providers(items: Optional[list[dict]]) -> list[dict]:
        """TMDb-список провайдеров → наш формат ``{provider_id, name, logo_url}``.

        Сортируем по ``display_priority`` (TMDb так ранжирует «главные» сервисы),
        нормализуем логотип в полный URL. Нормализация — в одном месте."""
        out: list[dict] = []
        for p in sorted(items or [], key=lambda x: x.get("display_priority", 999)):
            pid = p.get("provider_id")
            name = p.get("provider_name")
            if pid is None or not name:
                continue
            logo = p.get("logo_path")
            out.append({
                "provider_id": pid,
                "name": name,
                "logo_url": f"{_TMDB_LOGO_BASE}{logo}" if logo else None,
            })
        return out

    async def get_watch_providers(self, key: str, region: str) -> Optional[dict]:
        """Где тайтл доступен в ``region`` (нормализованный watch-providers TMDb).

        Возвращает ``{region, link, flatrate[], rent[], buy[]}``. Если HTTP-запрос
        прошёл, но региона в данных нет — отдаём пустые списки (это валидный
        «проверено, ничего нет», его тоже кэшируем). None только при выключенном
        TMDb, нерезолвимом ключе или сетевой ошибке.
        """
        if not self.enabled:
            return None
        ref = await self.resolve_tmdb_ref(key)
        if not ref:
            return None
        kind, tmdb_id = ref
        region = (region or "").upper()
        path = (
            "/movie/{id}/watch/providers" if kind == "movie"
            else "/tv/{id}/watch/providers"
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(
                    f"{self.base_url}{path.format(id=tmdb_id)}",
                    params={"api_key": self.api_key},
                )
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                print(f"[tmdb] watch providers fetch failed for {key}: {exc}")
                return None
            data = resp.json() or {}

        entry = (data.get("results") or {}).get(region) or {}
        return {
            "region": region,
            "link": entry.get("link"),
            "flatrate": self._normalize_providers(entry.get("flatrate")),
            "rent": self._normalize_providers(entry.get("rent")),
            "buy": self._normalize_providers(entry.get("buy")),
        }

    @staticmethod
    def _parse_details(kind: str, key: str, data: dict, cfg: dict) -> Optional[MovieBase]:
        original_key = cfg["title_keys"][1]
        title = next((data.get(k) for k in cfg["title_keys"] if data.get(k)), "")
        original = data.get(original_key) or None
        if not title:
            return None

        date = (data.get(cfg["date_key"]) or "")[:4]
        year = int(date) if date.isdigit() else None
        genres = [g["name"] for g in (data.get("genres") or []) if g.get("name")]
        overview = data.get("overview") or None

        credits = data.get("credits") or {}
        cast = [c["name"] for c in (credits.get("cast") or [])[:_MAX_CAST] if c.get("name")]

        director: Optional[str] = None
        if kind == "movie":
            for c in credits.get("crew") or []:
                if c.get("job") == "Director" and c.get("name"):
                    director = c["name"]
                    break
        else:
            creators = data.get("created_by") or []
            if creators and creators[0].get("name"):
                director = creators[0]["name"]

        poster_path = data.get("poster_path")
        poster_url = f"{_TMDB_POSTER_BASE}{poster_path}" if poster_path else None

        return MovieBase(
            imdb_id=key,
            title=title,
            original_title=original,
            year=year,
            media_type="series" if kind == "tv" else "movie",
            genres=genres,
            plot=overview,
            cast=cast,
            director=director,
            poster_url=poster_url,
            imdb_rating=None,
        )


tmdb_service = TMDBService()
