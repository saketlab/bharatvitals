# BharatPluse — How It Works and Where It Can Go

## What Is BharatPluse?

BharatPluse is a thin MCP (Model Context Protocol) server that exposes six of
India's public health and survey data backends — HMIS (Health Management
Information System), MCCD (Medical Certification of Cause of Death), SRS
(Sample Registration System), the Census of India, the NSS household
consumption expenditure survey, and the NSS health survey — to an LLM
through natural language. It does not reimplement any data logic, does not
access any database directly, and does not modify any R package. It is a
pure proxy: the LLM asks a question, the MCP server forwards it to the right
R API over HTTP, and returns the result.

The goal is to let a researcher ask questions like "How many
cardiovascular deaths were there in Kerala from 2018 to 2022?", "What is
the life expectancy in Kerala over 2020-2024?", "What was the population of
Maharashtra in 2011?", "What share of food budgets went to cereals in
2005?", or "How much did households spend on hospitalization for
cardiovascular disease?" and get an answer without writing code, navigating
databases, or knowing the underlying data model.

The server is named **India Health MCP** and is registered in Gemini under
the key `india-health-mcp` (and the same server in VS Code via
`.vscode/mcp.json`).

## How It Works

### Architecture

```
User asks Gemini a question
    ↓
Gemini reads tool descriptions, picks the right tool
    ↓
MCP server (server.py) receives the call
    ├─ HTTP → hmisindia API (:8765)
    ├─ HTTP → mccdindia API (:8585)
    ├─ HTTP → srsindia API (:8686)
    ├─ HTTP → censusindia API (:8895)
    ├─ HTTP → consumptionsurveyindia (:8795)
    └─ HTTP → healthsurveyindia (:8685)
    ↓
Gemini synthesizes answer back to user
```

The MCP server runs over stdio. Gemini CLI spawns it automatically when a
query needs data. The server never starts on its own — it only runs while
Gemini is actively processing a request.

### Data Flow

1. The user asks a natural language question in Gemini CLI.
2. Gemini reads the tool descriptions (docstrings) and decides which tool
   to call. If unsure, it can call `tool_guide` first.
3. Gemini invokes the chosen MCP tool with the right parameters.
4. The MCP server forwards the request to the corresponding R API.
5. The R API queries its data backend (Arrow/DuckDB over Parquet files)
   and returns JSON.
6. The MCP server forwards the JSON back to Gemini.
7. Gemini interprets the data and presents a natural language answer to
   the user.

The six base URLs are configurable via the environment variables
`HMIS_API_URL`, `MCCD_API_URL`, `CENSUS_API_URL`, `SRS_API_URL`,
`CONSUMPTION_API_URL`, and `HEALTHSURVEY_API_URL` (defaults 8765, 8585,
8895, 8686, 8795, 8685). Configured in `.gemini/settings.json` and
`.vscode/mcp.json`, and overridable via a local `.env`.

### Prerequisites

All six R packages must be running their Plumber APIs before the MCP
server can respond:

```r
# HMIS API on port 8765
library(hmisindia)
serve()

# MCCD API on port 8585
library(mccdindia)
serve()

# SRS API on port 8686
library(srsindia)
serve()

# Census API on port 8895
library(censusindia)
serve()

# Consumption survey API on port 8795
plumber::plumb("consumptionsurveyindia/inst/server/api.R")$run(port = 8795)

# Health survey API on port 8685
plumber::plumb("healthsurveyindia/inst/server/api.R")$run(port = 8685)
```

Each `serve()` resolves its Plumber file via `system.file(...)`, so the
packages must be **installed**, and the API packages must have their
parquet datasets where `ICS_DATA_DIR` / `IHS_DATA_DIR` point (defaulting to
the sibling `consumptionsurveyindiadataset/` and
`healthserveyindiadataset/` directories). `api_health()` will report which
backends are reachable.

## Current Tools

The server exposes 43 tools. Every backend REST route has exactly one
wrapper. The registry in `server.py` (`TOOL_REGISTRY`) drives `tool_guide`,
so tool documentation stays in sync with the code.

### HMIS tools — health system indicators

**Use for:** facility counts, bed availability, staffing, testing coverage,
vaccinations, service delivery metrics, monthly time series, and their
seasonality.

- `query_hmis` — indicator query (state/district, sector, date range,
  fixed/regex/fuzzy matching)
- `hmis_list_indicators` — search valid indicator names before querying
- `hmis_list_states` / `hmis_list_districts` — geography discovery
- `hmis_periodicity` — is there a seasonal pattern in this indicator?
- `hmis_decompose` — trend/seasonal/remainder decomposition
- `hmis_health` — API reachability

**Not for:** cause-of-death analysis or ICD-10 codes (use `query_mccd`).

### MCCD tools — medically certified cause of death

**Use for:** what people died from, ICD-10 codes, disease categories
(Communicable, NCD, External, Ill-defined), yearly mortality trends.

- `query_mccd` — table query (deaths, deaths_pct, cause, age, subcause,
  state_subcause, state_age_pct, trend, trend_pct, age_pct, age_over_pct)
- `mccd_causes` — search valid cause strings / ICD-10 codes
- `mccd_chapters` — browse ICD-10 chapters by epidemiological category
- `mccd_categorize` — deaths reclassified into epidemiological categories
- `mccd_list_states` / `mccd_health` — discovery and reachability

**Not for:** health system indicators, facility data, or testing coverage.

### SRS tools — population-level mortality and life tables

**Use for:** life expectancy, age-specific mortality, SRS cause-of-death
patterns, bulletins such as CBR/CDR/IMR, statistical report indicators
(TFR/NMR/U5MR), and summaries of mortality indicators.

Query tools: `srs_query_life_table`, `srs_query_cod`, `srs_query_bulletin`,
`srs_query_stat_report`, `srs_summary_indicators`,
`srs_life_expectancy_trend`, `srs_epi_transition`, `srs_arriaga_decompose`.

Discovery tools: `srs_list_states`, `srs_list_life_table_periods`,
`srs_list_cod_tables`, `srs_list_cod_periods`, `srs_list_bulletin_years`,
`srs_list_bulletin_indicators`, `srs_list_stat_report_years`,
`srs_list_stat_report_indicators`, `srs_available_periods`, `srs_health`.

**Not for:** medically certified deaths in MCCD or health-system service
data.

### Census tools — Census of India

**Use for:** population totals, demographic variables (literacy, sex
ratio, workers, religion), state/district/subdistrict geographies,
population projections, 1901–2011.

- `census_query` — variable query by year, geography, state, sector,
  optional geometry
- `census_population` — population totals with optional projections
- `census_population_projection` — district/state projections through 2031
- `census_list_states`, `census_list_geographies`, `census_list_variables`,
  `census_search_variables` — discovery
- `census_health` — API reachability

### query_consumption — household consumption

Analytics over the NSS household consumption expenditure survey (43rd 1988
through HCES 2023-24).

**Use for:** food/non-food spending, item search, food-group shares (by
round/state/sector), state consumption comparisons, item trends.

**Parameters:** `operation` — health, overview, items_search,
items_catalogue, food_group_shares, state_consumption, item_trends, or
`sql` (read-only SELECT/WITH over the `consumption` table); `params` —
operation filters (keyword, item, by, round, era, food_group, limit);
`max_rows` — result cap for the `sql` operation.

### query_healthsurvey — NSS health survey

Analytics over the NSS health survey hospitalization and outpatient data.

**Use for:** disease categories and lookup, hospitalization/outpatient
expenditure, state and sector comparisons, trends and summaries,
variable-label search.

**Parameters:** `operation` — health, overview, diseases, disease_lookup,
disease_query, state_query, disease_trend, state_summary,
variables_search, or `sql` (tables `hospitalization`, `outpatient`);
`params` — operation filters (table, round, disease, query, keyword, by,
min_obs).

### Meta tools

- `tool_guide` — returns a routing guide for every registered tool plus a
  `decision_rule` string. Generated from `TOOL_REGISTRY`, so it never
  drifts from the code.
- `api_health` — probes `/health` on all six backends at once and isolates
  per-backend failures. Call this first when a data tool reports an
  unavailable API.

## Tool Routing

The LLM decides which tool to call based on the tool descriptions
(docstrings). There is no explicit routing logic — Gemini reads the
descriptions, compares them against the user's question, and picks the
best match.

The `tool_guide` provides a fallback for ambiguous questions, returning a
structured decision rule:

- health system does → `query_hmis` (+ `hmis_list_indicators` to find names)
- medically certified deaths / cause of death → `query_mccd` (+ `mccd_causes`)
- population mortality / life expectancy / SRS indicators → `srs_query_*`
- Census of India population / variables / projections → `census_query`,
  `census_population`, `census_population_projection`
- household spending / food items → `query_consumption`
- illness / hospitalization / outpatient / health expenditure →
  `query_healthsurvey`
- backend unreachable → `api_health`

In practice, users naturally phrase questions differently depending on
which dataset they need:
- "What are the neonatal death indicators for Maharashtra?" → HMIS
- "How many deaths from coronary heart disease in Kerala in 2020?" → MCCD
- "What is the life expectancy trend in Kerala?" → SRS
- "What was the 2011 population of Maharashtra?" → Census
- "What share of food budgets went to cereals in 2005?" → Consumption
- "Average hospitalization spend for diabetes by state?" → Health survey