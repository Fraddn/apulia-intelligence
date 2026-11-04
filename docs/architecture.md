# Architecture

## Stack

| Layer | Choice |
|---|---|
| Backend | Django 6, django-ninja (REST API), django-allauth (headless auth) |
| Database | SQLite (WAL mode) |
| Frontend | Vue (not yet created), talks to the API and allauth headless |
| AI classification | Jev (type-safe classification model) |
| Hosting | Serverplan VPS, Docker Compose |

## Layout

```
backend/            Django project
  config/           settings, urls, api.py (NinjaAPI root)
  apps/             Django apps, each exposing a ninja Router in api.py
frontend/           Vue app (placeholder)
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
| `FieldProvenance` | For a company field: raw value, snapshot, assurance (`official`, `company`, `inferred`, `derived`, `manual`) and optional confidence 0–1. |

- `Company.record_provenance(field, raw_value, snapshot, assurance, confidence)` adds a row, or skips it if the same value from the same snapshot already exists.
- `Company.provenance_for(field)` returns the latest row.

Helpers:
- `vat.py`: checksum validation; `province_from_vat` reads the province from the tax-office code (digits 8–10). Store it as `derived`.
- `ateco.py`: `normalize_ateco("C-25.62.00")` returns `("C", "25.62.00")`; for plain codes the section is worked out from the division.

## Configuration

Everything is set through environment variables. See `.env.example`.

| Variable | Default |
|---|---|
| `DATA_DIR` | `./data` |
| `SQLITE_PATH` | `$DATA_DIR/db.sqlite3` |
| `APP_VERSION` | set at build/deploy time, shown at `/api/health` |
