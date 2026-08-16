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

## Приложения

- `accounts` — пользователь, регистрация, вход, профиль.
- `promocodes` — промокоды, погашение, rate limiting, загрузка через xlsx.
- `giveaway` — ежедневный розыгрыш, призы, победители, публичная страница.
- `analytics` — статистика по дням, экспорт в Excel.
