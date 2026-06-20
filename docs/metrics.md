# Эксперимент «доступность»: метрики и правило решения

3-недельный тест: меняет ли фича «где смотреть» поведение (открываю Ленточку
вместо того, чтобы идти сразу в Netflix). Все события пишутся в таблицу
`events` (web — `source='web'`, бот — `source='bot'`). Идентичность: `user_id`
для залогиненных/бота, `anon_id` для гостей.

## Какие события собираем

| Событие | Где срабатывает |
|---|---|
| `app_open` | загрузка веб-приложения; `/start` в боте |
| `recommendation_requested` | отправка запроса в Tonight (props: `onlyAvailable`, `region`, `hasServices`) |
| `tonight_pick_viewed` | показан экран подбора (props: `count`, `onlyAvailable`) |
| `availability_filter_used` | переключён тоггл «только доступное» (props: `on`) |
| `availability_viewed` | показаны бейджи провайдеров в карточке фильма |
| `movie_added` | фильм добавлен (web и бот; props: `source`/`via`) |
| `marked_watched` | фильм отмечен просмотренным |
| `share_opened` | открыт шеринг списка |
| `launch_clicked` | клик «Запустить» — прокси «пошёл смотреть» |

## Правило решения — Вариант 1 (личное поведение)

Главный сигнал — владелец сам. Порог (пример, подвинуть по вкусу):
**≥6 «решающих» сессий за 3 недели, из них ≥3 с фильтром доступности.**
«Решающая» сессия = `recommendation_requested → tonight_pick_viewed → launch_clicked`.

Если не дотянули → потребительский продукт убиваем/пивотим; сам эксперимент с
решением идёт в PM-кейс.

## SQL (SQLite локально; для Postgres замени `date(ts)` → `ts::date`)

Свой `user_id` найти:
```sql
SELECT id, email, name FROM users WHERE email LIKE '%nannenkova%';  -- или свой email
```

### Решающие сессии (воронка для Варианта 1)
```sql
-- Сколько раз доходил до «Запустить» за период.
SELECT count(*) AS launches
FROM events
WHERE name = 'launch_clicked'
  AND user_id = :me
  AND ts >= date('now', '-21 days');
```

```sql
-- Воронка по дням: запросы → показы → запуски.
SELECT date(ts) AS day,
       sum(name = 'recommendation_requested') AS requested,
       sum(name = 'tonight_pick_viewed')      AS viewed,
       sum(name = 'launch_clicked')           AS launched
FROM events
WHERE user_id = :me AND ts >= date('now', '-21 days')
GROUP BY day ORDER BY day;
```

### Использование фильтра доступности
```sql
SELECT
  sum(name = 'availability_filter_used') AS filter_toggles,
  sum(name = 'availability_viewed')      AS badges_seen,
  sum(name = 'recommendation_requested' AND props LIKE '%"onlyAvailable": true%') AS recs_only_available
FROM events
WHERE user_id = :me AND ts >= date('now', '-21 days');
```

### DAU / возврат (для Вариантов 2/3 — друзья)
```sql
-- Уникальные открыватели по дням.
SELECT date(ts) AS day,
       count(DISTINCT coalesce(user_id, anon_id)) AS users
FROM events
WHERE name = 'app_open'
GROUP BY day ORDER BY day;
```

```sql
-- W1→W2 retention: кто открывал и на 1-й, и на 2-й неделе.
WITH wk AS (
  SELECT coalesce(user_id, anon_id) AS u,
         CAST((julianday(date(ts)) - julianday(date('now','-21 days'))) / 7 AS INT) AS week
  FROM events WHERE name = 'app_open'
)
SELECT count(DISTINCT a.u) AS returned_w2
FROM wk a JOIN wk b ON a.u = b.u AND a.week = 0 AND b.week = 1;
```

## Заметки
- `props` хранится как JSON-текст; для точных выборок по полям в Postgres
  лучше `props::jsonb ->> 'onlyAvailable'`, в SQLite — `json_extract(props,'$.onlyAvailable')`.
- Опциональный `GET /api/metrics` под `METRICS_TOKEN` не делали — для n≈5 за
  3 недели хватает этих запросов. Добавить, если захочется смотреть в браузере.
