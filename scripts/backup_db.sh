#!/bin/sh
# Ежедневный дамп базы promo_draw в сжатый файл, старые дампы старше
# RETENTION_DAYS удаляются. Запускается по cron на сервере из корня
# проекта (см. README, раздел "Резервные копии базы").
set -eu

cd "$(dirname "$0")/.."

set -a
. ./.env
set +a

RETENTION_DAYS=14
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"

STAMP=$(date +%Y%m%d_%H%M%S)
FILE="$BACKUP_DIR/promo_draw_${STAMP}.sql.gz"

docker compose exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip > "$FILE"

find "$BACKUP_DIR" -name "promo_draw_*.sql.gz" -type f -mtime "+${RETENTION_DAYS}" -delete
