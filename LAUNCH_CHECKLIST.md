# Launch Checklist

Что нужно сделать перед тем, как давать ссылку на «Ленточку» людям.

## Уже сделано

- [x] Auth: email/пароль (bcrypt) + Google OAuth с настоящей проверкой ID-токена
- [x] JWT-токены, срок жизни 30 дней
- [x] Фронт: логин/логаут, меню пользователя, RU/EN, dark/light
- [x] Деплой на Railway (`*.up.railway.app`), Postgres, per-user изоляция данных

## Безопасность

- [ ] **CORS прибить к конкретным origins** — `backend/main.py:46` сейчас `allow_origins=["*"]` + `allow_credentials=True`. Заменить на список (Railway URL фронта + `http://localhost:5173` для dev).
- [ ] **JWT_SECRET без дефолта** — `backend/config.py:12` имеет fallback `"dev-only-insecure-secret-change-me"`. Фейлить старт, если переменная не задана.
- [ ] **Password policy** — `backend/models/user.py:16` поднять `min_length` 6 → 8.
- [ ] **Rate-limit на auth** — `slowapi` на `/auth/login`, `/auth/register`, `/auth/google` (анти-брутфорс).
- [ ] **Rate-limit на платные API** — `/api/recommend`, `/api/instagram/*`, `/api/search` (за ними OMDB / Claude / OpenAI).

## Деньги

- [ ] **Per-user дневные лимиты** на вызовы Anthropic / OpenAI / OMDB.
- [ ] **Hard cap у провайдеров** — Anthropic Console → spend limit, OpenAI → usage limits.

## Данные

- [ ] **Daily backup Postgres** в Railway (настройка в UI).
- [ ] **Выпилить «первый юзер забирает 62 бесхозных фильма»** — `backend/routers/auth.py:38-50` и `:101-104`. На текущем инстансе уже сработало; оставлять опасно для копий.

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
