# Apulia Intelligence

Company and market intelligence platform for businesses in Puglia.

Documentation: [docs/](docs/README.md)

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
sh scripts/check.sh   # same checks as CI
```

Enable the pre-push hook once per clone, so pushes are blocked when checks fail:

```bash
git config core.hooksPath .githooks
```

## CI/CD

Every push and PR runs the tests and a Docker smoke test. On `main`, a passing build is tagged with CalVer (`vYYYY.MM.PATCH`) and deployed when enabled. See [docs/deployment.md](docs/deployment.md).
