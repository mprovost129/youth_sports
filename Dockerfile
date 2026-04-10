FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Build-time fallback values so collectstatic can run even when .env is not part of the build context.
RUN SECRET_KEY=build-secret-key \
    ALLOWED_HOSTS=localhost \
    DJANGO_SETTINGS_MODULE=config.Settings.prod \
    DB_NAME=build_db \
    DB_USER=build_user \
    DB_PASSWORD=build_password \
    python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2"]
