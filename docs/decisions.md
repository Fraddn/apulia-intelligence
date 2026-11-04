# Decisions

| Date | Decision | Why |
|---|---|---|
| 2026-11-03 | Django + django-ninja + allauth (headless), Vue frontend later | Typed API, auth that works with a separate SPA |
| 2026-11-03 | SQLite as the only database | Low cost; data size (about 55k companies) fits easily |
| 2026-11-03 | Free data sources only | Keep costs down in the early phase |
| 2026-11-03 | CalVer `vYYYY.MM.PATCH` from git tags, no VERSION file | Automatic, no release commits |
| 2026-11-03 | Deploy to Serverplan (not Fly.io), host-agnostic setup | Change of hosting plans; plan type still to be confirmed |
| 2026-11-03 | OpenCoesione Soggetti as the main seed source | CC BY 4.0, has VAT number and ATECO; startup register not reusable |
| 2026-11-03 | Raw files kept in `data/raw/`, imported by management commands | Traceability; no repeated downloads |
| 2026-11-03 | Jev for company classification | Type-safe structured classification |
| 2026-11-03 | Serverplan VPS with Docker Compose (not shared hosting) | Same setup as local; long imports and background jobs allowed |
| 2026-11-03 | Per-field provenance table (`FieldProvenance`) instead of columns on `Company` | Every value traceable to a snapshot with an assurance level, as the requirements demand |
| 2026-11-03 | Store ATECO version (empty when unknown) | Sources use 2007/2022 codes; ATECO 2025 renumbers sections |
| 2026-11-04 | Companies only: legal forms 1.2, 1.3, 1.4, 1.5, 1.9 | Sole traders' names are personal data (GDPR); associations, foundations and anonymous records are not companies |
