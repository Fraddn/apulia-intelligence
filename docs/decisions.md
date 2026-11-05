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
| 2026-11-04 | Vue 3 + Vite + TS frontend, vue-i18n IT/EN, light/dark theme | User's frontend rules |
| 2026-11-04 | Product name "Puglia Imprese" (replaces "Apilia"); blue accent, small corner radius (4–6px) | User's choice |
| 2026-11-04 | Company funding = public funding of projects where it is the **sole** beneficiary; shared projects listed but not summed | Project amounts are whole-project totals; summing across shared projects or non-beneficiary roles inflated figures (€70bn) |
| 2026-11-04 | Exclude tax codes starting 8/9 and out-of-region VATs with any non-Puglia municipality | Removed public bodies (CNR, universities) and national companies (RFI, Telecom) from the Puglia list |
| 2026-11-05 | RNA state aid imported for our companies; keep all raw monthly files (~3–4 GB) | Real aid amounts per company and SME/large size; keeping raw files follows the traceability rule |
| 2026-11-05 | New size value "SME" (from RNA), only filled when size is unknown | RNA only distinguishes SME vs large |
| 2026-11-05 | OpenStreetMap lookup on demand when a company page opens, via Nominatim, cached, new assurance `community` | User's choice; Overpass public server unreliable; respects fair use |
| 2026-11-05 | **Removed** the OpenStreetMap lookup; focus on company websites for address and contacts | Only ~7% matches even in the best sectors, wrong matches when loosened, unreliable service |
| 2026-11-05 | Websites entered manually (admin or CSV), then read and verified by VAT number | No usable free search API (Google closed, Bing retired, Brave needs a card and forbids storing results) |
| 2026-11-05 | Automatic website discovery by guessing domains from the name, kept only if the site shows the company's VAT number | Free, no API key; ~16–18% found with no wrong matches |
| 2026-11-04 | All CSS in one global `<style>` in App.vue, enforced by ESLint | User's choice: no scoped styles, no CSS files |
| 2026-11-04 | Companies only: legal forms 1.2, 1.3, 1.4, 1.5, 1.9 | Sole traders' names are personal data (GDPR); associations, foundations and anonymous records are not companies |
