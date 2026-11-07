# Apulia Intelligence

**Puglia Imprese**: company and market intelligence platform for businesses in Puglia.

Documentation: [docs/](docs/README.md)

## Run locally

Needs Python 3.12+ and Node 24. Docker is only needed for option B.

### First time

```bash
cp .env.example .env
```

Open `.env` and set `SECRET_KEY` to any long random string, e.g. the output of `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`. Keep `DEBUG=True` locally.

The database is `data/db.sqlite3`. If you don't have it, `migrate` creates an empty one; fill it with the import commands described in [docs/data-sources.md](docs/data-sources.md).

### Option A: development servers (for working on the code)

Terminal 1, backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # first time only
pip install -r requirements.txt                     # first time and when requirements change
python manage.py migrate
python manage.py createsuperuser                    # first time only, for /admin
python manage.py runserver                          # http://localhost:8000
```

Next time, only `cd backend && source .venv/bin/activate && python manage.py runserver` is needed.

Terminal 2, frontend:

```bash
cd frontend
npm install       # first time and when package.json changes
npm run dev       # http://localhost:5173
```

Open **http://localhost:5173**. Vite reloads pages on save and forwards `/api`, `/_allauth`, `/admin` and `/static` to Django on port 8000.

- API docs: http://localhost:8000/api/docs
- Health check: http://localhost:8000/api/health
- Admin: http://localhost:5173/admin/

### Option B: the production setup, on your machine (Docker)

Runs the same two containers as the VPS: Caddy (Vue app + HTTPS) in front of Django. Use it to check a build before deploying.

1. Stop `runserver` if it's running (both use port 8000), and free ports 80 and 443.
2. In `.env`, add `https://localhost` to `CSRF_TRUSTED_ORIGINS`, otherwise login fails with a CSRF error:
   ```
   CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://localhost:8000,https://localhost
   ```
3. Start:
   ```bash
   docker compose up --build        # add -d to run in the background
   ```
4. Open **https://localhost**. The browser warns about the certificate (Caddy makes a self-signed one for localhost): accept it.

It uses the same `data/db.sqlite3`. Stop with `Ctrl+C`, or `docker compose down` if started with `-d`. Logs: `docker compose logs -f`.

## Run on the server

Step-by-step first launch on the Serverplan VPS, updates and troubleshooting: [docs/deployment.md](docs/deployment.md).

## Tests

```bash
sh scripts/check.sh   # same checks as CI (backend, plus frontend if node_modules exists)
```

Enable the pre-push hook once per clone, so pushes are blocked when checks fail:

```bash
git config core.hooksPath .githooks
```

## CI/CD

Every push and PR runs the tests and a Docker smoke test. On `main`, a passing build is tagged with CalVer (`vYYYY.MM.PATCH`) and deployed when enabled. See [docs/deployment.md](docs/deployment.md).
