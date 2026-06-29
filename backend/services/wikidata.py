"""Wikidata client — бесключевой фолбэк, который знает русские книги.

Зачем third source поверх Google Books и Open Library:
  - Google Books — основной поиск, но анонимная квота крошечная и общая на IP
    (429 → пусто), а без неё нужен платный ключ.
  - Open Library англоцентричен и по-русски слабый.
  - Wikidata — свободная, без API-ключа и без дневной квоты на IP, с сильным
    русским покрытием (русские названия + связь «автор → произведения»). Её и
    подставляем, когда Google молчит, до отката на Open Library.

Поиск идёт одним SPARQL-запросом через query.wikidata.org: встроенный
EntitySearch резолвит строку («Бродский» → Иосиф Бродский), дальше берём либо
само произведение, либо все works этого автора (всё, у чего есть автор P50).

Детали книги тянем Action API (``wbgetentities``). Идентификатор хранится как
``wd:Q12345`` (Google — ``gb:…``, Open Library — ``OL…W``), чтобы диспетчер
``book_search`` понимал по префиксу, куда идти.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

import httpx

from backend.models.book import BookBase, BookSearchResult

log = logging.getLogger(__name__)

_PREFIX = "wd:"
_SPARQL_URL = "https://query.wikidata.org/sparql"
_API_URL = "https://www.wikidata.org/w/api.php"
# Wikidata просит осмысленный User-Agent (дефолтный UA клиентов могут резать).
_UA = "LentochkaBot/1.0 (https://lentochka.up.railway.app; book search)"
_TIMEOUT = httpx.Timeout(15.0)
_QID_RE = re.compile(r"Q\d+$")

# Один запрос: EntitySearch резолвит строку → берём произведение или works автора.
# «Что-то с автором (P50)» — дешёвый и надёжный признак книги/стихов/эссе,
# без дорогого обхода иерархии классов (P279*), который любит уходить в таймаут.
_SEARCH_SPARQL = """
SELECT DISTINCT ?work ?workLabel ?authorLabel (YEAR(?pub) AS ?year) ?image WHERE {
  SERVICE wikibase:mwapi {
    bd:serviceParam wikibase:endpoint "www.wikidata.org";
                    wikibase:api "EntitySearch";
                    mwapi:search %(q)s;
                    mwapi:language "ru".
    ?match wikibase:apiOutputItem mwapi:item.
  }
  { ?match wdt:P50 ?selfAuthor. BIND(?match AS ?work) }
  UNION
  { ?work wdt:P50 ?match. }
  ?work wdt:P50 ?author.
  OPTIONAL { ?work wdt:P577 ?pub. }
  OPTIONAL { ?work wdt:P18 ?image. }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "ru,en". }
}
LIMIT 20
"""


def _sparql_string(value: str) -> str:
    """Экранировать строку для подстановки как SPARQL-литерал в кавычках."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _qid_from_uri(uri: str) -> Optional[str]:
    """'http://www.wikidata.org/entity/Q123' → 'Q123'."""
    if not uri:
        return None
    m = _QID_RE.search(uri)
    return m.group() if m else None


def _strip_prefix(work_key: str) -> str:
    """'wd:Q123' → 'Q123'. Idempotent для голого QID."""
    return work_key[len(_PREFIX):] if work_key.startswith(_PREFIX) else work_key


def _commons_cover(image_value: Optional[str], *, width: int = 300) -> Optional[str]:
    """P18 → URL обложки через Special:FilePath.

    SPARQL отдаёт IRI вида .../Special:FilePath/Файл.jpg; Action API — голое имя
    файла. Оба сводим к https-ссылке нужной ширины.
    """
    if not image_value:
        return None
    if "Special:FilePath" in image_value:
        url = image_value
    else:
        url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{image_value}"
    url = url.replace("http://", "https://")
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}width={width}"


class WikidataService:
    """Поиск книг через Wikidata (SPARQL для списка, Action API для деталей)."""

    async def search_books(self, query: str) -> list[BookSearchResult]:
        """Карточки книг по строке. Любая ошибка/таймаут → [] (это фолбэк)."""
        query = query.strip()
        if not query:
            return []
        sparql = _SEARCH_SPARQL % {"q": _sparql_string(query)}
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(
                    _SPARQL_URL,
                    params={"query": sparql, "format": "json"},
                    headers={"User-Agent": _UA, "Accept": "application/sparql-results+json"},
                )
                if resp.status_code != 200:
                    log.info("Wikidata SPARQL %s for q=%r", resp.status_code, query)
                    return []
                data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("Wikidata SPARQL failed for q=%r: %s", query, exc)
            return []

        results: list[BookSearchResult] = []
        seen: set[str] = set()
        for row in data.get("results", {}).get("bindings", []):
            qid = _qid_from_uri(row.get("work", {}).get("value", ""))
            title = row.get("workLabel", {}).get("value")
            # Лейбл-сервис при отсутствии русского/английского лейбла отдаёт сам
            # QID как «название» — такие пустышки пропускаем.
            if not qid or not title or title == qid or qid in seen:
                continue
            seen.add(qid)
            year = row.get("year", {}).get("value")
            results.append(BookSearchResult(
                work_key=f"{_PREFIX}{qid}",
                title=title,
                author=row.get("authorLabel", {}).get("value") or None,
                year=str(year) if year else None,
                cover_url=_commons_cover(row.get("image", {}).get("value")),
            ))
        return results

    async def get_book_by_key(self, work_key: str) -> Optional[BookBase]:
        """Полные метаданные по ``wd:Q…`` (или голому QID)."""
        qid = _strip_prefix(work_key)
        if not _QID_RE.match(qid):
            return None
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                entity = await self._get_entity(client, qid)
                if not entity:
                    return None

                labels = entity.get("labels", {})
                descriptions = entity.get("descriptions", {})
                claims = entity.get("claims", {})

                title = _pick_lang(labels)
                if not title:
                    return None

                author_ids = _claim_qids(claims, "P50")
                genre_ids = _claim_qids(claims, "P136")
                # Имена авторов/жанров одним батчем (labels всех ссылок разом).
                names = await self._resolve_labels(client, author_ids + genre_ids)

            authors = [names[a] for a in author_ids if a in names][:3]
            subjects = [names[g] for g in genre_ids if g in names][:8]
            return BookBase(
                work_key=f"{_PREFIX}{qid}",
                title=title,
                authors=authors,
                year=_claim_year(claims, "P577"),
                subjects=subjects,
                description=_pick_lang(descriptions),
                cover_url=_commons_cover(_claim_string(claims, "P18")),
                rating=None,
            )
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("Wikidata entity fetch failed for %s: %s", qid, exc)
            return None

    async def _get_entity(self, client: httpx.AsyncClient, qid: str) -> Optional[dict]:
        resp = await client.get(_API_URL, params={
            "action": "wbgetentities", "ids": qid,
            "props": "labels|descriptions|claims",
            "languages": "ru|en", "format": "json",
        }, headers={"User-Agent": _UA})
        if resp.status_code != 200:
            return None
        return resp.json().get("entities", {}).get(qid)

    async def _resolve_labels(
        self, client: httpx.AsyncClient, qids: list[str]
    ) -> dict[str, str]:
        """QID → читаемое имя (ru, иначе en) одним wbgetentities на все ссылки."""
        ids = [q for q in dict.fromkeys(qids)][:20]  # дедуп, бережём лимит на ids
        if not ids:
            return {}
        resp = await client.get(_API_URL, params={
            "action": "wbgetentities", "ids": "|".join(ids),
            "props": "labels", "languages": "ru|en", "format": "json",
        }, headers={"User-Agent": _UA})
        if resp.status_code != 200:
            return {}
        out: dict[str, str] = {}
        for q, ent in (resp.json().get("entities", {}) or {}).items():
            name = _pick_lang(ent.get("labels", {}))
            if name:
                out[q] = name
        return out


def _pick_lang(label_map: dict) -> Optional[str]:
    """Из {'ru': {...}, 'en': {...}} выбрать русское, иначе английское значение."""
    for lang in ("ru", "en"):
        entry = label_map.get(lang)
        if entry and entry.get("value"):
            return entry["value"]
    return None


def _claim_qids(claims: dict, prop: str) -> list[str]:
    """QID-значения свойства (напр. P50 авторы, P136 жанры)."""
    out: list[str] = []
    for snak in claims.get(prop, []):
        value = (snak.get("mainsnak", {}).get("datavalue", {}) or {}).get("value")
        if isinstance(value, dict) and value.get("id"):
            out.append(value["id"])
    return out


def _claim_string(claims: dict, prop: str) -> Optional[str]:
    """Первое строковое значение свойства (напр. P18 — имя файла обложки)."""
    for snak in claims.get(prop, []):
        value = (snak.get("mainsnak", {}).get("datavalue", {}) or {}).get("value")
        if isinstance(value, str):
            return value
    return None


def _claim_year(claims: dict, prop: str) -> Optional[int]:
    """4-значный год из time-свойства (P577 — дата публикации)."""
    for snak in claims.get(prop, []):
        value = (snak.get("mainsnak", {}).get("datavalue", {}) or {}).get("value")
        time = value.get("time") if isinstance(value, dict) else None
        if time:
            m = re.search(r"\d{4}", time)
            if m:
                return int(m.group())
    return None


def is_wikidata_key(work_key: str) -> bool:
    return bool(work_key) and work_key.startswith(_PREFIX)


wikidata_service = WikidataService()
