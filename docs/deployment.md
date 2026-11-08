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

## First launch on the Serverplan VPS

The examples use the domain `pugliaimprese.it`, the server IP `203.0.113.10`, the user `apulia` and the app folder `/home/apulia/app`. Replace them with yours. Commands marked **local** run on your computer, **server** in an SSH session on the VPS.

### 1. The VPS

Order a Serverplan VPS with a plain **Ubuntu 24.04 LTS** (or Debian 12), no control panel. A panel like Plesk or cPanel runs its own web server on ports 80/443, which Caddy needs. 2 GB RAM and 20 GB disk are enough (the database is about 0.7 GB). Serverplan emails the IP address and the root password.

### 2. Domain

In the DNS settings of the domain (Serverplan panel or your registrar), add an **A record** `pugliaimprese.it → 203.0.113.10` (and `www` too if you want it). Changes can take from minutes to a few hours. Check with:

```bash
dig +short pugliaimprese.it      # local: must print the VPS IP
```

### 3. Prepare the server (one time)

**server**, logged in as root (`ssh root@203.0.113.10`):

```bash
apt update && apt upgrade -y

# Docker + compose plugin
curl -fsSL https://get.docker.com | sh

# a normal user that runs the app and can use Docker
adduser apulia
usermod -aG docker apulia

# firewall: SSH, HTTP, HTTPS only
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443
ufw enable
```

Let your SSH key log in as `apulia`, so you don't need the password every time. **local**:

```bash
ssh-copy-id apulia@203.0.113.10
ssh apulia@203.0.113.10          # should log in without a password
```

### 4. Upload the code

**local**, from the project folder (the same excludes as the CI deploy):

```bash
rsync -az --delete \
  --exclude='.git/' --exclude='.github/' --exclude='.claude/' \
  --exclude='data/' --exclude='.env' --exclude='docs/' \
  --exclude='node_modules/' --exclude='.venv/' --exclude='frontend/dist/' \
  ./ apulia@203.0.113.10:/home/apulia/app/
```

### 5. Production `.env`

**server**, as `apulia`:

```bash
cd ~/app
python3 -c "import secrets; print(secrets.token_urlsafe(50))"   # copy the output for SECRET_KEY
nano .env
```

```
SECRET_KEY=<the generated value>
DEBUG=False
SITE_ADDRESS=pugliaimprese.it
ALLOWED_HOSTS=pugliaimprese.it
CSRF_TRUSTED_ORIGINS=https://pugliaimprese.it
CORS_FRONTEND_URL=https://pugliaimprese.it
ACCOUNT_EMAIL_VERIFICATION=none
# optional: only these IPs can open /admin (space-separated)
# ADMIN_ALLOWED_IPS=93.40.1.2
```

Then `chmod 600 .env` so only `apulia` can read it. Email (SMTP) settings are only needed before switching `ACCOUNT_EMAIL_VERIFICATION` to `mandatory`: `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` (see `.env.example`).

### 6. Upload the database (first launch only)

**local**: stop `runserver` and any import command first, then check that `data/` has no `db.sqlite3-wal` file (if it does, something still has the database open). Then:

```bash
ssh apulia@203.0.113.10 "mkdir -p ~/app/data/raw"
rsync -P data/db.sqlite3 apulia@203.0.113.10:/home/apulia/app/data/
```

The raw files in `data/raw/` are only needed to re-run imports on the server. After launch, **never upload the whole database again**: it would erase the user accounts created on the server (see [Populating production](#populating-production)).

### 7. Start

**server**:

```bash
cd ~/app
sh deploy/vps.sh                 # builds both images and starts them; takes a few minutes the first time
docker compose ps                # backend and web should be "Up"
docker compose logs web          # look for "certificate obtained successfully"
```

Open **https://pugliaimprese.it**. Check the API with `curl https://pugliaimprese.it/api/health`.

### 8. Admin account

**server**:

```bash
cd ~/app
docker compose exec backend python manage.py createsuperuser
```

The admin is at `https://pugliaimprese.it/admin/`.

### 9. Automatic deploys (optional, recommended)

Instead of steps 4 and 7 by hand, GitHub can deploy every push to `main`. Fill in the secrets and variables in [Enabling deploys](#enabling-deploys) with `DEPLOY_USER=apulia` and `DEPLOY_PATH=/home/apulia/app`. For `DEPLOY_SSH_KEY`, create a separate key just for GitHub:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/apulia_deploy -N ""                 # local
ssh-copy-id -i ~/.ssh/apulia_deploy.pub apulia@203.0.113.10        # local
cat ~/.ssh/apulia_deploy                                            # paste into DEPLOY_SSH_KEY
ssh-keyscan 203.0.113.10                                            # paste into DEPLOY_KNOWN_HOSTS
```

Then set `DEPLOY_ENABLED=true`. The deploy never touches `.env` or `data/`.

## Everyday operations

**server**, in `~/app`:

| Task | Command |
|---|---|
| Update by hand (after uploading code as in step 4) | `sh deploy/vps.sh` |
| Status | `docker compose ps` |
| Logs (live) | `docker compose logs -f` (only Django: `logs -f backend`) |
| Restart after editing `.env` | `docker compose up -d` |
| Stop / start | `docker compose down` / `docker compose up -d` |
| Django shell or commands | `docker compose exec backend python manage.py <command>` |

Containers restart by themselves after a crash or a server reboot (`restart: unless-stopped`).

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Browser can't connect, or `logs web` shows certificate errors | DNS doesn't point to the VPS yet (`dig +short`), or ports 80/443 are closed (`ufw status`) or taken by another web server (`sudo ss -tlnp \| grep -E ':80\|:443'`). Fix it and run `docker compose restart web`. |
| "Bad Request (400)" | The domain is missing from `ALLOWED_HOSTS`. |
| Login fails with a CSRF error | `CSRF_TRUSTED_ORIGINS` must be exactly `https://<domain>`. |
| Site loads but shows no companies | The database wasn't uploaded (step 6); `migrate` created an empty one. |
| `permission denied` on the Docker socket | `apulia` isn't in the `docker` group yet: log out and back in after `usermod`. |
| Build stops, out of memory | Add swap: `sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile`. |

## Containers

`docker-compose.yml` runs two containers, both built from the one `Dockerfile`:

| Service | Stage | What it does |
|---|---|---|
| `web` | `web` | Caddy. Owns ports 80/443, gets and renews the HTTPS certificate for `SITE_ADDRESS` automatically, redirects http to https, serves the built Vue app (`frontend/dist`, built in the `frontend` stage) and forwards `/api`, `/_allauth`, `/admin` and `/static` to `backend`. Config: `deploy/Caddyfile`. Certificates live in the `caddy_data` volume. |
| `backend` | `backend` | Django + gunicorn on port 8000, reachable only from the server itself and from Caddy. |

Unknown routes fall back to `index.html` so Vue router URLs like `/companies/123` work on reload. Without `SITE_ADDRESS` Caddy serves `https://localhost` with a self-signed certificate.

## Security settings

What protects the live site, and where it is set:

| Protection | Where |
|---|---|
| HTTPS everywhere, browsers told to always use it (HSTS, 1 year, not sent for `localhost`) | `deploy/Caddyfile` |
| Headers against clickjacking, content sniffing and referrer leaks; a basic Content-Security-Policy on the Vue pages | `deploy/Caddyfile` |
| `/admin` limited to `ADMIN_ALLOWED_IPS` (optional, default everyone) | `.env` → `deploy/Caddyfile` |
| Login limits per visitor (allauth) and on the admin login (5 failed tries per username every 5 minutes, 10 per minute per IP) | `ALLAUTH_TRUSTED_PROXY_COUNT=1` in `docker-compose.yml`, `apps/core/admin.py` |
| The backend container runs as a normal user, not root. `deploy/vps.sh` builds it with the deploy user's id and gives it `data/` | `Dockerfile`, `deploy/vps.sh` |
| Website fetching only reaches public internet addresses (never the server itself, Docker or a private network, redirects included) | `apps/companies/enrichment/websites.py` |

Login limits and the admin allowlist rely on Caddy seeing the visitor's real IP. Docker keeps it for normal IPv4 traffic. If the server also has IPv6, check `docker compose logs web` after a visit: if every request shows a `172.x` address, Docker is hiding the real IP and the allowlist must include that address.

If you run `sh deploy/vps.sh` as root, the container user gets id 1000.

## Backups

The database is `data/db.sqlite3`. Back it up off-server, e.g. a daily `sqlite3 data/db.sqlite3 ".backup ..."` or Litestream to object storage. Set this up before real users arrive.

## Populating production

First deploy: build the database locally with the import commands and upload `data/db.sqlite3`. After launch, never replace the whole file, because it would overwrite user accounts. Run the import commands on the server, or load only the company tables.
