# Apulia Intelligence

Company and market intelligence platform for businesses in Puglia.

## Run locally

```bash
cp .env.example .env   # then set SECRET_KEY
```

With Python (3.12+):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

With Docker:

```bash
docker compose up --build
```

API docs: http://localhost:8000/api/docs
Health check: http://localhost:8000/api/health

## Tests

```bash
cd backend && python manage.py test
```

## Versioning

CalVer `vYYYY.MM.PATCH`, tagged automatically by CI on every push to `main`.
