# Architecture

## Stack

| Layer | Choice |
|---|---|
| Backend | Django 6, django-ninja (REST API), django-allauth (headless auth) |
| Database | SQLite (WAL mode) |
| Frontend | Vue 3, Vite, TypeScript, Vue Router, vue-i18n (IT/EN), light and dark theme (blue accent), ESLint |
| AI classification | Jev (type-safe classification model) |
| Hosting | Serverplan VPS, Docker Compose |

## Layout

```
backend/            Django project
  config/           settings, urls, api.py (NinjaAPI root)
  apps/             Django apps, each exposing a ninja Router in api.py
frontend/           Vue app (src/views, src/components, src/locales)
data/               SQLite database + raw source files (git-ignored)
  raw/              downloaded source files, kept for traceability
deploy/             server-side deploy scripts
docs/               documentation
```

## URLs

| Path | Purpose |
|---|---|
| `/api/` | Application API (docs at `/api/docs`) |
| `/_allauth/browser/v1/` | Authentication for the SPA |
| `/admin/` | Django admin |

## Data flow

```
source files (data/raw/)  →  import commands  →  SQLite  →  API  →  Vue
```

- Each source has a management command (e.g. `import_opencoesione`).
- By default a command reads the newest file already in `data/raw/`. Use `--file` to import a specific file and `--download` to fetch a new version.
- Imports upsert by VAT number, save in batches, and record the provenance of each value.
- The app only reads the database, never the raw files.

Coverage happens in two stages:
1. **Candidates:** about 55k Puglia businesses, with basic identity data.
2. **Profiles:** 300–500 selected companies, enriched from their websites, Jev classification and other open data.

## Data model (`apps/companies`)

| Model | Purpose |
|---|---|
| `Company` | One per VAT number (validated). Identity, ATECO (section + code, version 2007), province (BA, BT, BR, FG, LE, TA), size, status. `profile_level` is `candidate` or `profile`. |
| `Source` | A data provider (OpenCoesione, RNA, websites, Jev, manual) with licence and attribution. |
| `SourceSnapshot` | One retrieval from a source: file name or URL, checksum, date of the data, stats. |
| `Project` | A funded project from OpenCoesione: title, description, theme, status, public/EU funding, payments, dates, number of beneficiaries, link |
| `StateAid` | One grant from the national state-aid register (RNA): measure, granting body, project, date, procedures, objectives, instruments, aid amount (summed across components), size stated, transparency link |
| `ProjectRole` | Company ↔ project with role: beneficiary, implementer, contractor, programmer |
| `WebsiteCheck` | Latest reading of a company's website: URL, status (verified / VAT not found / unreachable / blocked / no website), pages, time |
| `WebsitePage` | Text of each page read from the company's website (for classification) |
| `FieldProvenance` | For a company field: raw value, snapshot, assurance (`official`, `company`, `inferred`, `derived`, `manual`) and optional confidence 0–1. |

- `Company.record_provenance(field, raw_value, snapshot, assurance, confidence)` adds a row, or skips it if the same value from the same snapshot already exists.
- `Company.provenance_for(field)` returns the latest row.

Helpers:
- `vat.py`: checksum validation; `province_from_vat` reads the province from the tax-office code (digits 8–10). Store it as `derived`.
- `ateco.py`: `normalize_ateco("C-25.62.00")` returns `("C", "25.62.00")`; for plain codes the section is worked out from the division.

## API

| Endpoint | Returns |
|---|---|
| `GET /api/companies?search=&province=&section=&division=&theme=&funded=&ateco=&sort=&page=&page_size=` | `{items, count}`, 25 per page (max 100). `division` is the 2-digit ATECO division; `theme` and `funded` match companies that were **beneficiaries** of projects; `sort` is `name` (default), `funding` (sole-beneficiary funding, empty last) or `projects` (beneficiary project count). Items include `beneficiary_projects` and `sole_beneficiary_funding` |
| `GET /api/companies/{vat}` | All company fields, `provenance` (latest entry per field with source, assurance, confidence), `funding` (beneficiary/sole/shared project counts, sole-beneficiary funding, counts per role) and `projects` (up to 50, beneficiary roles first, newest first) with `projects_total` |
| `GET /api/stats` | Totals, counts by province and ATECO section, sources with the company-data date, and `funding` (beneficiary companies and projects, sole-beneficiary funding, projects by theme) |

## Frontend

Pages: dashboard (`/`), company explorer (`/companies`, filters kept in the URL) and company profile (`/companies/:vat`, including a "Funded projects" section).

- In development, Vite proxies `/api`, `/_allauth`, `/accounts`, `/admin` and `/static` to Django (`API_PROXY_TARGET`, default `http://localhost:8000`), so no CORS setup is needed. Production needs the same paths routed to Django.
- Auth: the header reads `/_allauth/browser/v1/auth/session` and shows "Signed in as …" with a logout button (DELETE on the same URL with the `csrftoken` cookie as `X-CSRFToken`), or a "Log in" link to allauth's `/accounts/login/` (plain allauth page for now; redirects back to `/`).
- Conventions are in `frontend/README.md`.
- Charts follow one rule set: single-series bars use one colour (validated for light and dark), values at the bar tip, a hover/focus tooltip, and the explorer table as the accessible table view.

## Configuration

Everything is set through environment variables. See `.env.example`.

| Variable | Default |
|---|---|
| `DATA_DIR` | `./data` |
| `SQLITE_PATH` | `$DATA_DIR/db.sqlite3` |
| `APP_VERSION` | set at build/deploy time. If unset, the latest git tag is used (local dev), else `dev`. Returned by `/api/health` and shown next to the app name in the header |
