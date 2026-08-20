# promo_draw

Сервис личного кабинета для акции с промокодами: регистрация, ввод промокода,
ежедневный розыгрыш призов.

## Стек

Django 5.2, PostgreSQL, Redis, Celery + Celery Beat (`django-celery-beat`).

## Локальный запуск

```bash
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env  # и подставить значения
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Для Celery (в отдельных терминалах, нужны запущенные Postgres и Redis):

```bash
celery -A promo_draw worker --loglevel=info --pool=solo
celery -A promo_draw beat --loglevel=info
```

## Docker

```bash
cp .env.example .env  # и подставить значения

docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Локально (`docker-compose.override.yml` подхватывается автоматически) сайт
доступен на `http://localhost:8000/` (сразу через runserver) и на
`http://localhost/` (через nginx). `POSTGRES_HOST`/`POSTGRES_PORT`,
`CELERY_BROKER_URL` и `REDIS_CACHE_URL` для контейнеров переопределены прямо
в `docker-compose.yml` — значения из `.env` для них не используются.

CI (`.github/workflows/ci.yml`) на каждый push/PR в `main` гоняет ruff, mypy,
pytest и собирает образ. Деплой по SSH пока не настроен — сервер под
promo_draw ещё не выбран.

## Приложения

- `accounts` — пользователь, регистрация, вход, профиль.
- `promocodes` — промокоды, погашение, rate limiting, загрузка через xlsx.
- `giveaway` — ежедневный розыгрыш, призы, победители, публичная страница.
- `analytics` — статистика по дням, экспорт в Excel.
