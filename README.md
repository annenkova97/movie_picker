# Movie Picker

Веб-приложение для управления списком фильмов с AI-рекомендациями.

## Возможности

- Добавление фильмов по названию или IMDb ID
- Автоматическое получение информации из OMDB (данные IMDb)
- Генерация кратких описаний на русском языке через Claude AI
- Рекомендации фильмов по свободному запросу («что-то лёгкое», «драма с Ди Каприо»)
- Предзагруженный список топ-100 фильмов IMDb
- Фильтрация: к просмотру / просмотрено

## Требования

- Python 3.11+
- OMDB API Key (бесплатно)
- Anthropic API Key (Claude)

## Установка

1. Клонируйте репозиторий и перейдите в директорию:
```bash
cd movie-picker
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate     # Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Скопируйте файл конфигурации и добавьте API ключи:
```bash
cp .env.example .env
```

Отредактируйте `.env`:
```
OMDB_API_KEY=ваш_ключ_omdb
ANTHROPIC_API_KEY=ваш_ключ_anthropic
```

## Получение API ключей

### OMDB API Key
1. Перейдите на http://www.omdbapi.com/apikey.aspx
2. Выберите FREE tier (1000 запросов/день)
3. Введите email и получите ключ

### Anthropic API Key
1. Перейдите на https://console.anthropic.com/
2. Зарегистрируйтесь и создайте API ключ

## Запуск

```bash
python run.py
```

Приложение будет доступно по адресу: http://localhost:8000

API документация (Swagger): http://localhost:8000/docs

## Использование

### Мой список
- Просматривайте добавленные фильмы
- Отмечайте просмотренные
- Фильтруйте по статусу

### Поиск
- Введите название фильма
- Выберите из результатов и добавьте в список

### Рекомендации
Напишите в свободной форме, что хотите посмотреть:
- «что-то лёгкое и смешное»
- «драму про семью»
- «фильм с Бенедиктом Камбербэтчем»
- «триллер, но не слишком страшный»

AI подберёт 1-3 фильма из вашего списка.

### Топ-100
Предзагруженный список лучших фильмов по версии IMDb. Добавляйте в свой список одним кликом.

## Структура проекта

```
movie-picker/
├── backend/
│   ├── main.py           # FastAPI приложение
│   ├── config.py         # Настройки
│   ├── database.py       # SQLite операции
│   ├── models/
│   │   └── movie.py      # Pydantic модели
│   ├── services/
│   │   ├── omdb.py       # OMDB API клиент
│   │   └── llm.py        # Claude API клиент
│   ├── routers/
│   │   ├── movies.py     # CRUD фильмов
│   │   ├── search.py     # Поиск в OMDB
│   │   └── recommend.py  # Рекомендации
│   └── data/
│       └── movies.db     # SQLite база (создаётся автоматически)
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── requirements.txt
├── run.py
├── .env.example
└── README.md
```

## API Endpoints

| Метод | Путь | Описание |
|-------|------|----------|
| GET | /api/movies | Список всех фильмов |
| POST | /api/movies | Добавить фильм |
| PATCH | /api/movies/{id} | Обновить статус |
| DELETE | /api/movies/{id} | Удалить фильм |
| GET | /api/search?q=... | Поиск в OMDB |
| POST | /api/recommend | Получить рекомендации |
