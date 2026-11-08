#!/bin/sh
# Runs on the server from the app folder. Requires Docker + compose and a .env file.
set -eu

# The backend runs as this user id inside the container, so it owns data/ (never root).
APP_UID="$(id -u)"
[ "$APP_UID" != 0 ] || APP_UID=1000
export APP_UID

mkdir -p data/raw
docker compose build
docker compose run --rm --no-deps --user root backend chown -R "$APP_UID:$APP_UID" /app/data
docker compose up -d
docker image prune -f
