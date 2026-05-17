# Деплой на Railway — пошагово

Всё, что нужно я уже положил в репо: `Procfile`, `runtime.txt`, `requirements.txt`.

## 1. Запушить в GitHub

Если ещё не запушено:
```bash
git add Procfile runtime.txt openapi.json LOVABLE_PROMPT.md DEPLOY.md
git commit -m "Add deploy config for Railway"
git push
```

## 2. Создать проект на Railway

1. Зайди на https://railway.app, войди через GitHub.
2. **New Project** → **Deploy from GitHub repo** → выбери `movie_picker`.
3. Railway автоматически определит Python, установит `requirements.txt` и запустит команду из `Procfile`.

## 3. Добавить переменные окружения

В панели проекта: **Variables** → **New Variable**. Добавь по очереди:

- `OMDB_API_KEY` — из твоего локального `.env`
- `ANTHROPIC_API_KEY` — из `.env`
- `OPENAI_API_KEY` — из `.env`
- `TELEGRAM_BOT_TOKEN` — можно не добавлять, если бот не нужен на этом деплое

Нажми **Deploy** — Railway пересоберёт проект.

## 4. Получить публичный URL

В панели: **Settings** → **Networking** → **Generate Domain**.
Получишь URL вида `https://movie-picker-production.up.railway.app`.

## 5. Проверить, что всё работает

Открой в браузере:
- `https://твой-url/api/health` → должно вернуть `{"status":"ok"}`
- `https://твой-url/docs` → Swagger с твоими ручками

## 6. Подводные камни

### SQLite теряет данные при передеплое
Railway использует эфемерную файловую систему. База `backend/data/movies.db` будет пересоздаваться при каждом деплое. Варианты:

- **Пока не критично** — просто игнорируй, данные свежие каждый раз.
- **Подключить Volume** — в Railway добавь Volume, смонтируй в `/app/backend/data`. Данные сохранятся между деплоями.
- **Перейти на Postgres** (надолго правильное решение) — добавь Postgres в Railway одной кнопкой, поменяй `aiosqlite` → `asyncpg` в коде. Скажи, если хочешь сделать.

### Instagram через Apify
Парсинг Instagram-рилзов идёт через [Apify Instagram Scraper](https://apify.com/apify/instagram-scraper). Никаких куки и сессий держать не надо — нужен только `APIFY_TOKEN` в переменных окружения Railway.

Возьми токен в Apify Console → Settings → Integrations и добавь его в Railway → Variables как `APIFY_TOKEN`.

## 7. Дальше

Когда получишь публичный URL и `/docs` открывается — иди в `LOVABLE_PROMPT.md`, замени `https://YOUR-API-URL` на свой реальный URL, и вставь всё в Lovable.
