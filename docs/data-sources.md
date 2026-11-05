# Data sources

Rules: use free sources only (for now), respect each licence, never invent values, and record the provenance of every value.

## Glossary

- **VAT number (Partita IVA):** 11-digit business tax ID. The primary key for matching companies across sources. Digits 8–10 are the code of the provincial tax office that issued it.
- **Codice fiscale:** tax code. For companies it's usually the same as the VAT number.
- **ATECO:** Italian classification of economic activities (the national version of NACE), e.g. `J-62.01` for software production.

## ATECO in practice

ATECO is a tree, from broad to specific: **section** (letter) → **division** (2 digits) → group → **class** (4 digits, the same as NACE across the EU) → category (6 digits, Italian-only).

```
J  →  62  →  62.0  →  62.01  →  62.01.00
ICT   programming      software production
```

- The division (first two digits) determines the section. `ateco.py` holds this lookup table for ATECO 2007.
- **ATECO 2007 vs 2025:** ATECO 2025 (NACE Rev. 2.1) reshuffles sections; for example, software moves from J to K. Always store `ateco_version`. OpenCoesione says it uses 2007; the import must check for and report codes that look like 2025 instead of mislabelling them.
- `normalize_ateco` turns `C-25.62.00` and `25.62.00` into `("C", "25.62.00")`, and turns anything it can't parse into `(None, None)`.

## Data handling rules

1. **Never change the source.** Raw files stay in `data/raw/` as published, and the raw value is kept in `FieldProvenance`.
2. **Clean in one place.** All normalisation lives in small tested helpers (`vat.py`, `ateco.py`), so every import cleans data the same way.
3. **Never guess silently.** Values that can't be cleaned stay empty and are shown as unknown. Values worked out by a rule are marked `derived` with a confidence; AI output is marked `inferred`.

Flow: raw file → import command (validate, normalise, filter) → `Company` (clean current values) + `FieldProvenance` (raw value, source, date, assurance) → admin / API / frontend.

## OpenCoesione: Soggetti (primary seed)

- URL: https://opencoesione.gov.it/it/opendata/ (file `soggetti.zip`, about 119 MB zipped, 2.2 GB CSV)
- Licence: CC BY 4.0 (as stated on the site; confirm before release). Attribution: "Fonte: OpenCoesione".
- Updated every two months. Analysed snapshot: `soggetti_20260630.csv`, 7.4M rows.
- Format: semicolon-separated CSV, UTF-8, one row per entity per project (`COD_LOCALE_PROGETTO`).
- Useful fields: `OC_CODICE_FISCALE_SOGG`, `OC_DENOMINAZIONE_SOGG`, `COD_FORMA_GIURIDICA_SOGG` (1.x = business), `COD_COMUNE_SEDE_SOGG` (region+province+comune, Puglia = `016`), `INDIRIZZO_SOGG`, `CAP_SOGG`, `COD_ATECO_SOGG`, `COD_ADDETTI_SOGG`, `COD_DIMENSIONE_SOGG`.

Import: `python manage.py import_opencoesione [--file PATH | --download] [--force]` (code in `apps/companies/importers/opencoesione.py`).

Import rules:
- **Legal forms kept:** partnerships (1.2), limited companies (1.3), cooperatives (1.4), consortia (1.5), foreign companies (1.9). **Excluded:** sole traders and freelancers (1.1, personal names under GDPR), public economic bodies (1.6), associations, foundations and other non-profits (1.7, 1.8), and non-1.x public bodies.
- **Location:** a company is kept if its registered municipality is in Puglia (province marked `official`), or if the municipality is missing and the VAT office is in Puglia (province marked `derived`, confidence 0.7). If the most frequent municipality is outside Puglia, the company is excluded.
- **Rows merged per VAT number:** the first non-empty value of each column wins.
- **Excluded:** records without a real name (name is the VAT number), invalid VAT checksums, and tax codes starting with 8 or 9 (non-commercial bodies such as CNR, universities and associations, even when labelled as companies).
- **Out-of-region VAT numbers:** a company whose VAT number was issued outside Puglia is kept only if every municipality recorded for it, anywhere in Italy, is in Puglia. This removed national companies such as RFI and Telecom Italia.
- **Legal form:** the most frequent value across the company's rows.
- **Prune:** `--prune` deletes companies no longer in the file, unless they have provenance from another source (e.g. manual edits). After the stricter rules: **41,988 companies**.
- **ATECO formats:** `C-25.62.00` (2007), `25.62.00_2007`, `47.11.40_2022` (2022 update, same sections), `P_2007` (section only). Codes marked `_2025` are kept without a section and counted.
- **Text:** double- and triple-encoded UTF-8 and cp1252 mojibake are fixed; `§;` is an escaped `;`. **Names:** CSV-escaped quotes (`"""NAME`), wrapping quotes and unbalanced quotes are removed; balanced inner quotes (`ASILO "LE COCCOLE" SRL`) and accent apostrophes (`SOCIETA'`) are kept (157 names affected). The clean value goes in `Company`, the raw value in `FieldProvenance`.
- **Re-runs:** a file already imported (same checksum) is skipped unless `--force`. Values whose latest provenance comes from another source (e.g. manual edits) are never overwritten.

First import (snapshot 2026-06-30, 2026-11-04): 7.4M rows read in about 1.5 minutes; **42,485 companies** (BA 18,794, LE 9,032, FG 6,181, TA 5,065, BR 3,407, BT 6); 98.7% have ATECO; sections J+M 4,012, software (62.x) 630; database about 90 MB.

Findings from exploring the data:
- `COD_COMUNE_SEDE_SOGG` is empty in 83% of rows. Filtering on it finds only about 1,050 Puglia businesses.
- Filtering on the VAT tax-office code (`071` FG, `072` BA, `073` TA, `074` BR, `075` LE, `110` BAT) finds about **55k businesses**: Bari 23.7k, Lecce 12.2k, Foggia 8.1k, Taranto 6.6k, Brindisi 4.5k. 87% have an ATECO code.
- The VAT office is where the number was issued, not necessarily today's registered office. Store it as a likely location and confirm it from another source.
- BAT companies mostly have Bari-issued VAT numbers.
- Company size is almost never filled. ATECO comes in mixed formats (`C-25.62.00` and plain digits).
- Coverage is limited to companies involved in funded projects, which is not the whole economy.

## OpenCoesione: Progetti (funded projects)

- File: `progetti.zip` (about 190 MB zipped, 2.6 GB CSV), stored as `data/raw/opencoesione_progetti_YYYYMMDD.zip`. Same source and licence as Soggetti.
- Import: `python manage.py import_opencoesione_projects [--projects-file] [--soggetti-file] [--download] [--force]` (code in `apps/companies/importers/opencoesione_projects.py`). It uses the newest progetti and soggetti files in `data/raw/`.
- Links: the Soggetti file connects company ↔ project (`COD_LOCALE_PROGETTO`) with a role (`SOGG_COD_RUOLO`): 1 programmatore → `programmer`, 2 attuatore → `implementer`, 3 beneficiario → `beneficiary`, 4 realizzatore → `contractor`.
- Stored per project (`Project`): code, CUP, title, description (`OC_SINTESI_PROGETTO`, 77% filled), synthetic theme (code + label), cycle, status (not started/ongoing/completed/settled), net public funding (`OC_FINANZ_TOT_PUB_NETTO`), EU funding, payments, start and end dates, **number of beneficiaries**, and the OpenCoesione link. Roles go in `ProjectRole`.
- Only projects linked to our companies are imported. Projects left without any company are deleted.
- Formats: amounts use a decimal comma (`526265,43`); dates are `YYYYMMDD` (sometimes empty).

**How funding is counted:** a project's amount is the whole project's public funding, not money paid to one company. Only the *beneficiary* role means the company received funding. Projects can be shared by many beneficiaries (one giant shared project made two small SRLs look like €1.38bn each). So:
- **Company funding = sum of public funding of projects where it is the sole beneficiary** (`beneficiaries_count = 1`).
- Shared projects are counted and listed, never added to the company's total.
- Other roles (implementer, contractor) are shown as context, never as funding received.

First import (2026-11-04, progetti 2026-08-31 + soggetti 2026-06-30): 37,936 projects, 117,442 company–project links, 99.8% of linked projects found.

## RNA: Registro Nazionale degli Aiuti di Stato (state aid)

- Listing: https://www.incentivitalia.gov.it/rna/rna-open-data/aiuti (paged, `?page=N`). Files: `https://www.incentivitalia.gov.it/open-data/aiuti/OpenData_Aiuti_YYYY_MM[_NNN].zip`, one per month from 2016-11. **Busy months are split into parts** of 500,000 records (`_002`, `_003`, `_004`); there were 142 files as of 2026-11.
- Stored as `data/raw/rna/rna_aiuti_YYYY_MM[_NNN].zip`. **All raw files are kept** (decision 2026-11-05), about 3–4 GB in total.
- Import: `python manage.py import_rna [--download] [--file PATH] [--force]` (code in `apps/companies/importers/rna.py`). `--download` reads the listing pages and fetches only missing files; files are imported in name order, one snapshot each, and skipped if already imported.
- Licence: none named ("senza restrizioni di copyright"). Attribution: "Fonte: Registro Nazionale degli Aiuti di Stato".
- Format: XML with namespace `http://www.rna.it/RNA_aiuto/schema`, 0.5–1.8 GB per file unzipped, so it is streamed from the zip. **It contains invalid control characters** (e.g. `\x02` in "COVID\x02 19"), which are stripped while reading. ISO dates, dot decimals, `CUP` "n.d." when missing.
- One grant (`AIUTO`, unique `COR`) can have **several components**, each with procedure (e.g. De Minimis, Esenzione), objective, sector and instruments. Amounts (`ELEMENTO_DI_AIUTO`, `IMPORTO_NOMINALE`) are **summed across components**. Sector codes switch to NACE 2.1 from 2026.
- Matching: only grants whose `CODICE_FISCALE_BENEFICIARIO` is one of our companies are stored (`StateAid`). About 18% of our companies appear in any single month.
- **Size:** `DES_TIPO_BENEFICIARIO` is only "PMI" (→ `sme`) or "Grande impresa" (→ `large`), sometimes "Non classificata" (ignored). It is set from the most recent grant, and only when the company's size is unknown or was previously set by RNA, so more detailed sizes from other sources are never overwritten.
- About 16,000 Puglia beneficiaries per month are not in our list, but RNA has no legal form (companies can't be told apart from sole traders), so they are not added.

## OpenStreetMap (tried and removed, 2026-11-05)

An on-demand lookup when a company page opened (Nominatim; Overpass was overloaded) was built and then **removed**. In the sectors most likely to be mapped (hotels, restaurants, shops) it matched only **4 of 60** companies (7%), because the map lists shop signs rather than legal names and most companies aren't mapped. Looser matching produced mostly wrong matches (e.g. a bar matched to a nursery school), and the service was often slow or returned 503 errors. Migration `0006_remove_osm` deletes its data. Don't retry without a new idea for matching.

## Company websites (address and contacts)

- **Finding websites** (search APIs were rejected: Google Custom Search is closed to new customers, Bing is retired, and Brave requires a card and forbids storing results):
  - **Automatic, by guessing domains:** `python manage.py discover_websites [--limit N] [--workers 8] [--force] [--fetch]` (code in `apps/companies/enrichment/discovery.py`). From the name without legal forms and owner names ("BAR CENTRALE S.N.C. DI ROSSI MARIO" → bar centrale) it tries up to 12 domains (full name, first two words, hyphenated, first word; `.it`/`.com`/`.eu`). Only domains that exist (DNS) are fetched (`www.` then bare, respecting `robots.txt`), and a site is kept **only if the homepage or one of its contact/about pages shows the company's VAT number**. Saved as `derived` (confidence 0.95, source "Website discovery"); existing websites are never replaced. Every attempt is recorded in `WebsiteDiscovery` (outcome, domains tried), so runs can resume; failures are retried after 180 days or with `--force`. Network work runs in parallel workers; the main process writes to the database.
  - Measured: 11/60 (18%) on a random sample of limited companies, 16/100 (16%) on the first live batch, with no wrong sites. About 3 seconds per company with 8 workers including `--fetch`, so roughly 30+ hours for all companies (run in batches or overnight).
  - **On demand:** opening a company page with no website check calls `POST /api/companies/{vat}/discover`. It runs the same discovery (25-second limit; at most 2 searches at once per server process, otherwise status `busy`) and reads the contacts if a site is found. Companies with a website but no check just get their contacts read. Results are remembered (180 days); timeouts and busy aren't, so the next visit retries. The page shows "Looking for the company website…" and then the outcome.
  - **Manual:** in the Django admin (recorded as `manual`) or in bulk: `python manage.py import_websites sites.csv` with columns `vat_number,website`.
- **Reading:** `python manage.py fetch_websites [--force] [--limit N]`, or the admin action "Fetch website contacts". Code in `apps/companies/enrichment/websites.py`.
  - Respects `robots.txt` and identifies itself; reads the homepage plus up to 4 pages whose link is a whole-word match for contact/about/legal/privacy (e.g. `contatti`, `chi-siamo`, `azienda`, `note-legali`, `privacy`). At most 2 MB per page.
  - **Verification:** the site is used only if a page shows the company's VAT number (`P.IVA 01775410747`, `IT01775410747`, `017 754 107 47`…). Otherwise the status is `vat_not_found` and nothing is extracted.
  - **Extracted** (assurance `company`, source "Company website", page URL as reference): address + postcode + city only with a Puglia postcode (70xxx–74xxx, 76xxx); the city is cut at words like C.F., Cap. Soc., Tel., P.IVA. Phone from `tel:` links or labelled numbers. **Generic** email only (info@, amministrazione@, commerciale@…; never named people). PEC (pec./legalmail/arubapec… domains).
  - Never overwrites values whose latest source is another one (official, manual…). **An address is one unit:** if any of address/postcode/town already comes from another source, the website's address is skipped entirely, and parts it set earlier are removed (prevents mixing an official street with a town from a different office).
  - Page text is kept in `WebsitePage` (replaced on each check) for classification. Outcome in `WebsiteCheck` (`verified`, `vat_not_found`, `unreachable`, `blocked`, `no_website`); re-checked after 90 days unless `--force`.
- First real test (aqp.it, pugliasviluppo.eu): both verified; address found for AQP, email and PEC for Puglia Sviluppo.

## ISTAT: list of Italian municipalities (town names)

- File: `Elenco-comuni-italiani.csv` from istat.it (latin-1, `;`, quoted headers containing line breaks), stored as `data/raw/istat/istat_comuni_YYYYMMDD.csv`. 7,896 municipalities (257 in Puglia). Licence: ISTAT open data, CC BY (attribution "Fonte: ISTAT"; exact version not verified).
- Import: `python manage.py import_istat_municipalities [--download] [--file PATH]` into `Municipality` (code, name, province, region).
- **Town names:** companies with an ISTAT municipality code (from OpenCoesione) and no town get the official name, as `derived` with the code as raw value. This also runs at the end of `import_opencoesione`. Unknown codes (e.g. merged municipalities) are left empty.
- **Postcode check:** postcode prefixes give the province (70 BA, 71 FG, 72 BR, 73 LE, 74 TA, 76 BT). If a company's postcode contradicts the municipality's province, nothing is filled (and an earlier fill is removed).
- Postcodes alone are not used to find towns: there is no open official postcode list (it belongs to Poste Italiane), and one postcode can cover several places.

## Other free sources (to evaluate)

| Source | Use | Access |
|---|---|---|
| EPO Open Patent Services | Patents | REST API, free registration |
| ISTAT | Market totals (coverage context) | SDMX REST API |
| Eurostat | EU comparisons | REST API |
| dati.puglia.it | Regional datasets | CKAN API |

## Not usable

- **startup.registroimprese.it:** no bulk download (list pages return 404). The legal notes forbid automated mass extraction and building our own database from it. Do not scrape it. Possible route: a formal request to InfoCamere or MIMIT.
- **ANAC open data:** rejects automated requests. Don't try to get around the block; ask ANAC directly if needed.
- **Paid providers** (openapi.com, Atoka, Cerved, AIDA): out of scope while we use free sources only. Without them, official multi-year financials are not available.
