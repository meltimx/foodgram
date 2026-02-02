# Foodgram - продуктовый помощник

Веб-приложение для публикации и обмена рецептами. Пользователи могут создавать рецепты, добавлять их в избранное, подписываться на авторов и формировать список покупок с возможностью скачивания в PDF.

## Развёрнутый проект

https://meltim.sytes.net/

## Автор

**Губайдуллин Тимур**
- GitHub: [meltimx](https://github.com/meltimx)
- Telegram: [@meltimx](https://t.me/meltimx)

## Технологии

- Python 3.14
- Django 5.2
- Django REST Framework 3.16
- PostgreSQL 16
- Gunicorn
- Nginx
- Docker / Docker Compose
- GitHub Actions (CI/CD)

## CI/CD

Проект настроен на автоматический деплой при пуше в ветку `main`:

1. **Тесты** — проверка кода flake8
2. **Сборка** — билд и пуш Docker-образов на Docker Hub
3. **Деплой** — обновление контейнеров на сервере
4. **Уведомление** — отправка сообщения в Telegram

## Локальное развёртывание с Docker

### 1. Клонирование репозитория

```bash
git clone https://github.com/meltimx/foodgram.git
cd foodgram
```

### 2. Настройка переменных окружения

Создайте файл `infra/.env` на основе примера `backend/.env.example`.

Обязательные настройки для Docker:

```env
SECRET_KEY=ваш-секретный-ключ
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1
USE_SQLITE=False
POSTGRES_DB=foodgram
POSTGRES_USER=foodgram_user
POSTGRES_PASSWORD=foodgram_pass
DB_HOST=db
DB_PORT=5432
```

### 3. Запуск контейнеров

```bash
cd infra
docker compose up -d --build
```

### 4. Подготовка базы данных

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py import_ingredients data/ingredients.json
```

### 5. Сборка статики

```bash
docker compose exec backend python manage.py collectstatic --noinput
```

### 6. Проверка

Откройте в браузере: http://localhost:8000/

## Локальное развёртывание без Docker

### 1. Клонирование репозитория

```bash
git clone https://github.com/meltimx/foodgram.git
cd foodgram
```

### 2. Переход в директорию backend

```bash
cd backend
```

### 3. Создание виртуального окружения

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate     # Windows
```

### 4. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 5. Настройка переменных окружения

Скопируйте `.env.example` в `.env` и при необходимости отредактируйте:

```bash
cp .env.example .env
```

По умолчанию используется SQLite (`USE_SQLITE=True`).

### 6. Применение миграций и создание суперпользователя

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 7. Импорт ингредиентов

```bash
python manage.py import_ingredients data/ingredients.json
```

### 8. Запуск сервера

```bash
python manage.py runserver
```

### 9. Проверка

- Сайт: http://localhost:8000/
- Админ-панель: http://localhost:8000/admin/
- API документация: http://localhost:8000/api/docs/
