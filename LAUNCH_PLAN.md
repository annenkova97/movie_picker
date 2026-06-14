# Launch Plan — Ленточка (friends-only beta)

Цель: отдать <50 друзьям проверить идею. НЕ полноценный публичный запуск.

**Стратегия**: минимум инфры, максимум валидации. Если через 2 недели продукт «зайдёт» — возвращаемся к отложенным пунктам (домен, email-верификация, forgot password).

## Принятые решения

- **Хостинг**: Railway (Trial → Hobby при необходимости)
- **URL**: `lentochka.up.railway.app` (без своего домена пока)
- **Error tracking**: Sentry Developer (free, 5k ошибок/мес)
- **Аналитика**: Railway-логи на первое время (Umami потом, если нужно)
- **Бэкапы Postgres**: GitHub Actions → `pg_dump` → приватный репо
- **Auth v1**: email + пароль, БЕЗ верификации, БЕЗ forgot password
  - Если друг забыл пароль → пишет тебе → ты сбрасываешь руками в БД
  - Это осознанный tradeoff для быстрого теста идеи

## Блокеры — обязательно до раздачи друзьям

- [ ] **Step 1 — Sentry** (код готов; осталось завести проекты и DSN)
  - [x] Backend: `sentry-sdk[fastapi]`, включается переменной `SENTRY_DSN`
  - [x] Frontend: `@sentry/react`, включается `VITE_SENTRY_DSN` (на сборке)
  - [ ] Завести 2 проекта в sentry.io, прописать DSN в Railway, бросить
        тестовую ошибку с обеих сторон и проверить, что долетают
- [x] **Step 2 — Rate limiting** (`slowapi`; реализация в `backend/rate_limit.py`)
  - [x] `slowapi` на бэке — лимитер + `SlowAPIMiddleware` + 429-handler в `backend/main.py`
  - [x] `/api/recommend` — 30/час per-user (fallback на IP); дорогой Claude-вызов
  - [x] `/auth/login` 10/мин, `/auth/register` 5/час, `/auth/google` 20/мин (по IP, анти-брутфорс)
  - [x] `/api/instagram/{parse,import,search}` — 10/час; `/api/search` + `/preview` — 60/мин
  - [x] `/movies/add` и `/movies/by-imdb` — 60/час per-user
- [x] **Security hardening** (вне исходного плана — сделано заодно с rate-limit)
  - [x] CORS прибит к `CORS_ALLOW_ORIGINS` из env (было `allow_origins=["*"]`)
  - [x] `JWT_SECRET` обязателен — старт без него падает (был небезопасный дефолт-ключ)
  - [x] Пароль: `min_length` 6 → 8
  - [x] Убрана миграция «первый юзер забирает 62 бесхозных фильма» — латентная утечка библиотеки на любой копии БД
- [x] **Step 3 — Error boundaries в React** (глобальный fallback + кнопка перезагрузки, ошибки уходят в Sentry)
- [ ] **Step 4 — Бэкапы** (workflow готов; осталось завести secrets)
  - [x] GitHub Action: `pg_dump` раз в день (`.github/workflows/backup.yml`)
  - [x] Дамп шифруется (gpg) и коммитится в приватный backup-репо
  - [x] Procedure restore — `docs/BACKUPS.md`
  - [ ] Создать приватный backup-репо + secrets (см. docs/BACKUPS.md), прогнать руками
- [x] **Step 5 — Мини Privacy Policy**
  - [x] Одна страница: что храним, зачем, внешние сервисы, как удалить аккаунт
  - [x] Страница `/privacy` на фронте, ссылка в меню аккаунта
- [ ] **Step 6 — Mobile проверка** (iOS Safari + Android Chrome, реальные устройства, не эмулятор)

## Опционально, если будет время

- [ ] **Hard spend caps у провайдеров** — Anthropic Console spend limit + OpenAI usage limits. Страховка поверх rate-limit: лимиты по запросам не спасут от дорогого инцидента, а потолок по деньгам — да.
- [ ] **Error boundary для iframe/embeds** если есть
- [ ] **Account deletion endpoint** (можно пока руками в БД)
- [ ] **Простой фидбек**: не форма, просто `mailto:` или tg-ссылка в настройках

## Отложено до после валидации

**Auth / email:**
- Покупка домена `lentochka.app`
- Resend интеграция (API key уже в Railway env, но не используем)
- Forgot password
- Email-верификация
- Google OAuth (код подготовлен в `auth.py`, но нужен фронт)

**Прочее:**
- Terms of Service (пока одной Privacy хватит для friends)
- Umami аналитика
- Staging-окружение
- Форма фидбека
- PostHog / funnel-аналитика

## Решённые вопросы

- ~~Email-верификация для существующих аккаунтов~~ → не делаем, верификации не будет
- ~~i18n полная?~~ → да, все ключи переведены ru+en
- ~~Что менялось в `backend/routers/auth.py`?~~ → подготовка под Google OAuth, не мешает

## Эксплуатационные ссылки (заполнить по ходу)

- Production URL: https://lentochka.up.railway.app (проверить точный)
- Sentry backend DSN: _TBD_
- Sentry frontend DSN: _TBD_
- Backup репо: _TBD_

## После теста — критерии «идея зашла»

Пересматриваем отложенные пункты если:
- ≥5 из ~20 друзей активно пользуются через 2 недели (>1 движения в неделю)
- Есть положительный фидбек по UX
- Видим органическое расшаривание (друзья друзьям)

Если не зашло — думаем что менять в продукте, а не в инфре.
