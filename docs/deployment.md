# Deployment

## Local gate

`scripts/check.sh` runs the same checks as the `test` job in `tests.yml`. The pre-push hook in `.githooks/pre-push` runs it and blocks the push if it fails. Enable the hook once per clone with `git config core.hooksPath .githooks`.

## Pipeline

Two workflows in `.github/workflows/`:

- `tests.yml`: runs on pull requests and on pushes to any branch except `main`. Other workflows can also call it.
- `deploy.yml`: runs on pushes to `main`. It calls `tests.yml` first and only releases and deploys if the tests pass.

```
PR / branch push ──► tests.yml (test + docker)

push to main ──► deploy.yml: tests.yml ──► release ──► deploy (if enabled) ──► health check
```

| Job | What it does |
|---|---|
| `test` | Django deploy checks, missing-migration check, test suite |
| `docker` | Builds the image, starts it, checks `/api/health` |
| `release` | Creates a CalVer tag and GitHub release, `vYYYY.MM.PATCH` |
| `deploy` | Copies code over SSH (rsync), runs `deploy/vps.sh` (Docker Compose rebuild + restart), checks `DEPLOY_URL/api/health` |

Pull requests only run `test` and `docker`. Nothing deploys if a test fails.

## Enabling deploys

In GitHub, go to **Settings → Environments → `production`**. Add a required reviewer if you want manual approval before each deploy.

Secrets:

| Secret | Example |
|---|---|
| `DEPLOY_HOST` | `server.example.it` |
| `DEPLOY_USER` | `apulia` |
| `DEPLOY_PORT` | `22` (optional) |
| `DEPLOY_PATH` | `/home/apulia/app` |
| `DEPLOY_SSH_KEY` | private key (create a dedicated deploy key) |
| `DEPLOY_KNOWN_HOSTS` | output of `ssh-keyscan -p 22 server.example.it` |

Variables:

| Variable | Value |
|---|---|
| `DEPLOY_ENABLED` | `true` turns on deploys |
| `DEPLOY_URL` | `https://apulia.example.it` (used for the health check) |

## Server setup (one time)

Serverplan VPS:
1. Install Docker with the compose plugin.
2. Create a deploy user and add the public half of the deploy key to its `~/.ssh/authorized_keys`. The user needs permission to run Docker (the `docker` group).
3. Create `DEPLOY_PATH` and put a production `.env` in it (`DEBUG=False`, a real `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_FRONTEND_URL` set to the public site URL, and SMTP settings: `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`). SMTP is optional while `ACCOUNT_EMAIL_VERIFICATION=none` (the default); it is needed before switching verification to `mandatory`.
4. The `data/` folder (database and raw files) lives in `DEPLOY_PATH/data` and is never overwritten by deploys.
5. Put a reverse proxy with HTTPS (e.g. Caddy) in front of the app on port 8000, and don't expose port 8000 publicly.

## Backups

The database is `data/db.sqlite3`. Back it up off-server, e.g. a daily `sqlite3 data/db.sqlite3 ".backup ..."` or Litestream to object storage. Set this up before real users arrive.

## Populating production

First deploy: build the database locally with the import commands and upload `data/db.sqlite3`. After launch, never replace the whole file, because it would overwrite user accounts. Run the import commands on the server, or load only the company tables.
