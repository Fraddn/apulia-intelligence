# Data sources

Rules: use free sources only (for now), respect each licence, never invent values, and record the provenance of every value.

## Glossary

- **VAT number (Partita IVA):** 11-digit business tax ID. The primary key for matching companies across sources. Digits 8–10 are the code of the provincial tax office that issued it.
- **Codice fiscale:** tax code. For companies it's usually the same as the VAT number.
- **ATECO:** Italian classification of economic activities (the national version of NACE), e.g. `J-62.01` for software production.

## OpenCoesione: Soggetti (primary seed)

- URL: https://opencoesione.gov.it/it/opendata/ (file `soggetti.zip`, about 119 MB zipped, 2.2 GB CSV)
- Licence: CC BY 4.0 (as stated on the site; confirm before release). Attribution: "Fonte: OpenCoesione".
- Updated every two months. Analysed snapshot: `soggetti_20260630.csv`, 7.4M rows.
- Format: semicolon-separated CSV, UTF-8, one row per entity per project (`COD_LOCALE_PROGETTO`).
- Useful fields: `OC_CODICE_FISCALE_SOGG`, `OC_DENOMINAZIONE_SOGG`, `COD_FORMA_GIURIDICA_SOGG` (1.x = business), `COD_COMUNE_SEDE_SOGG` (region+province+comune, Puglia = `016`), `INDIRIZZO_SOGG`, `CAP_SOGG`, `COD_ATECO_SOGG`, `COD_ADDETTI_SOGG`, `COD_DIMENSIONE_SOGG`.

Findings:
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
