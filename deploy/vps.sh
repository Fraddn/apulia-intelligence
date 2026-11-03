#!/bin/sh
# Runs on the server from the app folder. Requires Docker + compose and a .env file.
set -eu

mkdir -p data/raw
docker compose up -d --build
docker image prune -f
