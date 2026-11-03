# Apilia — Product Requirements

Company and market intelligence platform.

## 1. Product overview

Apilia is a business intelligence platform focused initially on companies operating in Puglia, Italy. It collects, organises, analyses and presents information about businesses. Users can understand the regional business ecosystem and explore individual companies and entire markets.

It is not a simple company directory. Its value is turning fragmented company information into structured, comparable business intelligence. The model is platforms like Beauhurst, adapted to the Italian and regional business environment.

## 2. Problem

Business information is fragmented across official registers, financial records, company websites, public statistical databases, startup registers and other public sources. Finding and comparing it by hand is difficult.

A user should be able to understand:
- what a company actually does, and which markets it serves
- its products, services and technologies
- its size, financial performance, and whether it is growing or declining
- how it compares with other companies, and where it stands in its industry

## 3. Geographic market

The initial focus is Puglia, covering all six provinces: Bari, Barletta-Andria-Trani, Brindisi, Foggia, Lecce and Taranto.

The design should allow expansion to other Italian regions and later to European markets. The first goal is a meaningful, reliable database, not cataloguing every registered company.

## 4. Company information

### 4.1 Basic information
Official name, VAT number, fiscal code, registered office, city, province, region, website, legal form, business status, registration date or year founded, ATECO classification, and the official activity description.

### 4.2 Business description
General description, main activities, products, services, industries served, target markets, specialisations, areas of operation, and publicly described projects. Descriptions should be readable, not copied administrative classifications.

### 4.3 Technology and specialisation
For example: AI, machine learning, software development, cloud, cybersecurity, data analytics, e-commerce, web, mobile, industrial automation, robotics, renewable energy. A company can have several. Technologies the company explicitly mentions are kept separate from technologies inferred by analysis.

### 4.4 Financial information
Revenue, net profit or loss, employees, total assets, shareholders' equity, financial year, and other relevant indicators. History across several years matters most. Never invent values or present estimates as official figures, and show clearly when information is unavailable.

### 4.5 Development and innovation
Startup status, innovative startup registration, patents, R&D, investments, funding rounds, acquisitions, partnerships, international expansion, and new products.

### 4.6 Sources and reliability
For every important value: where it came from, when it was collected, and whether it is officially verified, supplied by the company, or inferred by automated analysis. Also how reliable and complete it is. Official facts must be kept distinct from AI-generated interpretations.

## 5. Data sources

Candidate sources: Registro Imprese / InfoCamere, the innovative startup register, Regione Puglia open data, ISTAT, Eurostat, company websites, and others that allow appropriate access and reuse. See [data-sources.md](data-sources.md) for what is actually usable.

Requirements:
- respect licensing
- don't assume bulk availability
- never fabricate records
- preserve where each value came from
- avoid duplicates
- keep data up to date

## 6. AI-powered intelligence

Apilia uses **Jev**, a type-safe AI classification model, to turn unstructured information into structured intelligence. For each company it determines:
- industry classification
- specialisations
- technologies, with a 0–100 score each
- products and services
- relevance to an industry, technology or search
- confidence in the classification

AI analysis must never be presented as verified fact. If a website mentions machine learning, that is a publicly mentioned capability, not proof of a large AI department.

## 7. Search and discovery

Users can search by name, industry, keywords, products and services, technologies, specialisations, province, city, ATECO code, revenue range, employees, company age and status. Results are filterable and sortable. Each result shows a short description, location, industry, key specialisations and a link to the profile.

## 8. Rankings

- **Financial:** highest revenue, profit, employees.
- **Growth:** fastest-growing, largest revenue increase, growing headcount. These require enough history.
- **Technology:** leading AI, software, cloud, cybersecurity and automation companies.
- **Innovation:** innovative startups, patents, documented R&D, investment activity.
- **Geographic:** leaders by province or city, industry distribution.

Every ranking has clearly defined criteria and explains why each company appears in it.

## 9. Custom rankings

Users choose criteria and weights (e.g. AI 40%, cloud 25%, software 20%, cybersecurity 15%). Each result shows its final score, position, the score for each criterion, the weights, an explanation, data completeness and confidence. A score measures fit with the chosen criteria, not overall company quality.

## 10. Market analytics

- **Geographic:** companies by province and municipality, where each technology is concentrated.
- **Industry:** counts, concentration, size distribution, financial comparisons.
- **Financial:** total revenue available, distribution, averages and medians where meaningful, employment, historical performance.
- **Innovation:** startups, specialisations, patents, investment.
- **Market evolution:** company registrations and closures, growth, changes in employment and in industry composition.

Every statistic states its coverage, reporting period and limitations. Totals over an incomplete database are not the whole market.

## 11. Company comparison

Side-by-side comparison covering activities, services, industry, technologies, revenue, employees, financial history, innovation, AI classification and data completeness. Missing values are shown as missing, never as zero.

## 12. Product experience

The main areas are the dashboard, company explorer, company profiles, rankings, market analytics and comparison. The product should feel professional, clear and reliable, letting users move naturally from a market overview to a single company.

## 13. Data quality and trust

The platform must:
- preserve sources
- flag outdated information
- detect duplicates
- handle missing values
- separate verified data from inferred data
- show the reporting year of financial figures
- show AI confidence
- explain how rankings are calculated
- avoid unsupported conclusions

Incomplete data must not automatically push a company down a ranking.

## 14. Initial scope

Puglia only, with **300–500 well-documented profiles**. Priorities:
1. Company dataset
2. Detailed profiles
3. Industry and technology classification
4. Search
5. Rankings
6. Geographic and industry analytics
7. Source traceability
8. Financials where available
9. Comparison

## 15. Success criteria

- **Discoverability:** users find companies by natural business concepts, industries, technologies and location.
- **Understanding:** users quickly see what a company does and which markets it serves.
- **Comparison:** users compare companies on meaningful, transparent criteria.
- **Market awareness:** users understand the composition of an industry or area.
- **Ranking:** users find companies that stand out on measurable or clearly explained criteria.
- **Reliability:** information is traceable, limitations are visible, and AI assessments are distinct from verified facts.
- **Scalability:** the platform can expand beyond Puglia without changing its purpose.

## 16. Vision

**Discover companies → understand their activities → analyse their characteristics → compare businesses → rank the market → understand the business ecosystem.**

Accurate information, explainable analysis and useful insight come before the number of records.
