# Launch Checklist

Что нужно сделать перед тем, как давать ссылку на «Ленточку» людям.

## Уже сделано

- [x] Auth: email/пароль (bcrypt) + Google OAuth с настоящей проверкой ID-токена
- [x] JWT-токены, срок жизни 30 дней
- [x] Фронт: логин/логаут, меню пользователя, RU/EN, dark/light
- [x] Деплой на Railway (`*.up.railway.app`), Postgres, per-user изоляция данных

## Безопасность

- [x] **CORS прибить к конкретным origins** — список через env-переменную `CORS_ALLOW_ORIGINS` (запятая как разделитель). На Railway надо проставить URL фронта.
- [x] **JWT_SECRET без дефолта** — старт фейлится, если переменная не задана.
- [x] **Password policy** — `min_length` поднят до 8.
- [x] **Rate-limit на auth** — `slowapi`: `/auth/login` 10/мин, `/auth/register` 5/час, `/auth/google` 20/мин (по IP).
- [x] **Rate-limit на платные API** — per-user (fallback на IP): `/api/recommend` 30/час, `/api/instagram/*` 10/час, `/api/search` + `/api/search/preview` 60/мин.

## Деньги

- [ ] **Per-user дневные лимиты** на вызовы Anthropic / OpenAI / OMDB.
- [ ] **Hard cap у провайдеров** — Anthropic Console → spend limit, OpenAI → usage limits.

## Данные

- [ ] **Daily backup Postgres** в Railway (настройка в UI).
- [x] **Выпилить «первый юзер забирает 62 бесхозных фильма»** — удалён код в `auth.py` и helper-функции в `db_sqlite.py` / `db_postgres.py`.

## Контентные фичи

- [ ] **Instagram-импорт на проде** — сейчас сломан без cookies. Либо починить через Volume, либо временно скрыть на фронте.

## Мониторинг

- [ ] **Sentry** (или хотя бы ловить unhandled exceptions и логировать структурированно).
- [ ] **Uptime-check на `/api/health`** — внешний.

## Юридическое (минимум)

- [ ] **Privacy-блок** в футере: что храним (email, фильмы, Google avatar), кому отдаём (никому), как удалить аккаунт.

## Отложено намеренно

- ⏸ Восстановление пароля — если забудут, сбросим вручную в БД.
- ⏸ Свой домен — живём на `*.up.railway.app`.
