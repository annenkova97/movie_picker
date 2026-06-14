# Бэкапы базы данных

Ежедневный workflow `.github/workflows/backup.yml` снимает `pg_dump` с
Railway-Postgres, шифрует его gpg-паролем и кладёт в приватный репозиторий.
Хранятся 30 последних дампов (~месяц истории).

## Что настроить один раз

1. Создать **приватный** репозиторий для дампов, например
   `annenkova97/lentochka-backups`.
2. Создать fine-grained PAT (GitHub → Settings → Developer settings →
   Fine-grained tokens) с доступом только к этому репозиторию,
   право **Contents: Read and write**.
3. В репозитории `movie_picker` добавить Actions-secrets:
   - `DATABASE_PUBLIC_URL` — публичная строка подключения из Railway
     (Postgres → Connect → Public Network). Внутренний `DATABASE_URL` с
     GitHub-раннера недоступен.
   - `BACKUP_PASSPHRASE` — длинная парольная фраза; сохранить в менеджере
     паролей. Без неё дампы не расшифровать.
   - `BACKUP_REPO` — `annenkova97/lentochka-backups`.
   - `BACKUP_REPO_TOKEN` — PAT из шага 2.
4. Запустить workflow руками (Actions → db-backup → Run workflow) и убедиться,
   что в backup-репозитории появился `dumps/lentochka_<дата>.dump.gpg`.

## Restore (проверить процедуру ДО того, как она понадобится)

```bash
# 1. Скачать нужный дамп из backup-репозитория
git clone git@github.com:annenkova97/lentochka-backups.git
cd lentochka-backups/dumps

# 2. Расшифровать (спросит BACKUP_PASSPHRASE)
gpg --decrypt --output lentochka.dump lentochka_2026-06-11_0300.dump.gpg

# 3. Восстановить в БД (ВНИМАНИЕ: --clean удаляет существующие таблицы).
#    URL — публичный connection string целевой базы.
docker run --rm -i postgres:17 \
  pg_restore --no-owner --no-privileges --clean --if-exists \
  --dbname "postgresql://USER:PASS@HOST:PORT/railway" < lentochka.dump
```

После restore перезапустить сервис на Railway (он на старте прогонит
idempotent-миграции `init_db`).

## Проверка целостности (раз в месяц)

Расшифровать свежий дамп и восстановить его в локальный Postgres
(`docker run -d -p 5433:5432 -e POSTGRES_PASSWORD=x postgres:17`), убедиться,
что `SELECT count(*) FROM movies;` отдаёт разумное число.
