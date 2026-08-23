# promo_draw

Сервис личного кабинета для акции с промокодами: регистрация пользователей,
ввод промокода с ограничением на количество попыток, ежедневный розыгрыш
призов среди погасивших код, публичная страница победителей, email-уведомления
и загрузка промокодов пачками через админку.

Продакшн: https://promo-draw.duckdns.org

## Возможности

- Регистрация и вход по email, подтверждение почты по ссылке, сброс пароля.
- Заполнение профиля — обязательно перед вводом промокода.
- Погашение промокода с блокировкой на 5 минут после 3 неудачных попыток подряд.
- Загрузка промокодов из xlsx-файла через админку с отчётом о результатах.
- Ежедневный розыгрыш призов: шанс на победу пропорционален числу погашенных
  за день кодов, один пользователь не может выиграть дважды за акцию.
- Автоматическое подведение итогов дня по расписанию (Celery Beat) и ручной
  запуск из админки — без риска задвоить результат.
- Публичная страница победителей по дням.
- Email-уведомления о регистрации промокода (можно отключить в профиле) и о
  победе в розыгрыше (отключить нельзя).
- Дневная статистика по регистрациям и попыткам погашения с выгрузкой в Excel.

## Стек

Python 3.12, Django 5.2, PostgreSQL, Redis, Celery + Celery Beat
(`django-celery-beat`), gunicorn, nginx, Docker Compose.

## Требования

- Python 3.12 — для запуска без Docker.
- Docker и Docker Compose — для запуска через контейнеры (рекомендуемый способ).
- PostgreSQL и Redis — поднимаются автоматически через Docker Compose; для
  запуска без Docker нужны установленными отдельно.

## Переменные окружения

Перед первым запуском скопируйте `.env.example` в `.env` и подставьте реальные
значения:

```
cp .env.example .env
```

- `SECRET_KEY` — обязателен, без значения по умолчанию. Сгенерировать новый:
  `python -c "import secrets; print(secrets.token_urlsafe(50))"`.
- `DEBUG` — `True` только для локальной разработки, на боевом сервере `False`.
- `ALLOWED_HOSTS` — домены/IP через запятую, без пробелов.
- `CSRF_TRUSTED_ORIGINS` — домены со схемой (`https://example.com`), через
  запятую; нужен только когда сайт открыт по HTTPS через nginx.
- `SITE_URL` — домен сайта для ссылок в письмах, без слэша на конце.
- `CELERY_BROKER_URL` / `REDIS_CACHE_URL` — адреса Redis для брокера Celery и
  для кэша соответственно (разные базы одного Redis). Через Docker Compose
  переопределяются на `redis://redis:6379/...` прямо в `docker-compose.yml`,
  значения из `.env` для контейнеров не используются.
- `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` — обязательны, без
  значений по умолчанию. `POSTGRES_HOST` / `POSTGRES_PORT` при запуске через
  Docker Compose тоже переопределяются в `docker-compose.yml`.
- `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` /
  `EMAIL_USE_TLS` — настройки SMTP. При `DEBUG=True` не используются, письма
  выводятся в консоль. Если провайдер блокирует исходящие 587/465 (частая
  практика у VDS-хостеров), стоит попробовать порт 2525 — большинство
  почтовых сервисов держат его как раз на такой случай.
- `DEFAULT_FROM_EMAIL` — адрес отправителя.

## Локальный запуск без Docker

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

## Запуск через Docker

```bash
cp .env.example .env  # и подставить значения

docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Локально (`docker-compose.override.yml` подхватывается автоматически) сайт
доступен на `http://localhost:8000/` (напрямую через runserver) и на
`http://localhost/` (через nginx).

## Тесты

```bash
pytest
```

Тесты лежат в `tests/` на уровне проекта, а не по одному `tests.py` в каждом
приложении. `pytest-django` сам поднимает и удаляет отдельную тестовую базу.

## Управляющие команды

- `python manage.py generate_promo_codes --count N` — генерирует `N`
  промокодов пачками и сохраняет их в базу.

## CI/CD

`.github/workflows/deploy.yml` на каждый push и pull request в `main` гоняет
ruff, mypy и pytest, затем собирает Docker-образ. При пуше непосредственно в
`main` (не на pull request) следом идёт автодеплой на боевой сервер по SSH:
`git pull`, пересборка и перезапуск контейнеров, миграции, сборка статики.

## Приложения

- `accounts` — пользователь, регистрация, вход, профиль.
- `promocodes` — промокоды, погашение, rate limiting, загрузка через xlsx.
- `giveaway` — ежедневный розыгрыш, призы, победители, публичная страница.
- `analytics` — статистика по дням, экспорт в Excel.
