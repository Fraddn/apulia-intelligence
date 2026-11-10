FROM node:26-alpine AS frontend

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM caddy:2-alpine AS web

COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=frontend /frontend/dist /srv

FROM python:3.13-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}
ENV DATA_DIR=/app/data
ARG APP_UID=1000

WORKDIR /app
RUN useradd --uid ${APP_UID} --user-group --no-create-home --home-dir /app --shell /usr/sbin/nologin app

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .
RUN SECRET_KEY=build-only python manage.py collectstatic --noinput
RUN mkdir -p /app/data/raw && chown -R app:app /app/data

USER app

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --threads 4 --timeout 90"]
