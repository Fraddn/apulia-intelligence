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
- **Excluded:** records without a real name (name is the VAT number), and invalid VAT checksums.
- **ATECO formats:** `C-25.62.00` (2007), `25.62.00_2007`, `47.11.40_2022` (2022 update, same sections), `P_2007` (section only). Codes marked `_2025` are kept without a section and counted.
- **Text:** double- and triple-encoded UTF-8 and cp1252 mojibake are fixed; `§;` is an escaped `;`. The clean value goes in `Company`, the raw value in `FieldProvenance`.
- **Re-runs:** a file already imported (same checksum) is skipped unless `--force`. Values whose latest provenance comes from another source (e.g. manual edits) are never overwritten.

First import (snapshot 2026-06-30, 2026-11-04): 7.4M rows read in about 1.5 minutes; **42,485 companies** (BA 18,794, LE 9,032, FG 6,181, TA 5,065, BR 3,407, BT 6); 98.7% have ATECO; sections J+M 4,012, software (62.x) 630; database about 90 MB.

Findings from exploring the data:
- `COD_COMUNE_SEDE_SOGG` is empty in 83% of rows. Filtering on it finds only about 1,050 Puglia businesses.
- Filtering on the VAT tax-office code (`071` FG, `072` BA, `073` TA, `074` BR, `075` LE, `110` BAT) finds about **55k businesses**: Bari 23.7k, Lecce 12.2k, Foggia 8.1k, Taranto 6.6k, Brindisi 4.5k. 87% have an ATECO code.
- The VAT office is where the number was issued, not necessarily today's registered office. Store it as a likely location and confirm it from another source.
- BAT companies mostly have Bari-issued VAT numbers.
- Company size is almost never filled. ATECO comes in mixed formats (`C-25.62.00` and plain digits).
- Coverage is limited to companies involved in funded projects, which is not the whole economy.

## RNA: Registro Nazionale Aiuti (enrichment)

- URL: https://www.incentivitalia.gov.it/rna/rna-open-data/aiuti
- Monthly XML files (`OpenData_Aiuti_YYYY_MM`), updated weekly.
- Licence: none named ("senza restrizioni di copyright"). Use for enrichment with attribution.
- Fields: `DENOMINAZIONE_BENEFICIARIO`, `CODICE_FISCALE_BENEFICIARIO`, `DES_TIPO_BENEFICIARIO` (size), `REGIONE_BENEFICIARIO`, `SETTORE_ATTIVITA` (NACE), aid amounts, project title and description.

## Company websites (enrichment)

Fetch the homepage and the about and services pages, respecting `robots.txt`. Extract the text and classify it with Jev. Store website-derived facts as company-supplied, and Jev output as AI-inferred.

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
