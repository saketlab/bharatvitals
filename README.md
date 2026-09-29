# BharatPluse — MCP wrapper for India's public health, mortality, and survey REST APIs

A thin proxy that exposes the existing censusindia, hmisindia, mccdindia,
srsindia, consumptionsurveyindia, and healthsurveyindia REST APIs to an LLM
via MCP tools. It does not modify the R packages, access databases directly,
or reimplement data logic.

## Architecture

```
Any MCP client / LLM (Gemini CLI, Claude Desktop, VS Code, Cursor, ...)
    ↓
MCP Server (server.py)
    ├─ HTTP GET → censusindia API (:8895)
    ├─ HTTP GET → hmisindia API (:8765)
    ├─ HTTP GET → mccdindia API (:8585)
    ├─ HTTP GET → srsindia API (:8686)
    ├─ HTTP GET/POST → consumptionsurveyindia (:8795)
    └─ HTTP GET/POST → healthsurveyindia (:8685)
```

The server exposes 43 tools — one thin wrapper per backend REST endpoint —
plus `tool_guide` (routing guide) and `api_health` (probe all backends at once).

## Tools

| Area | Tools | Backend |
|------|-------|---------|
| Health system indicators | `query_hmis`, `hmis_list_indicators`, `hmis_list_states`, `hmis_list_districts`, `hmis_periodicity`, `hmis_decompose`, `hmis_health` | hmisindia (`/query`, `/indicators`, `/states`, `/districts`, `/periodicity`, `/decompose`, `/health`) |
| Medically certified cause of death | `query_mccd`, `mccd_causes`, `mccd_chapters`, `mccd_categorize`, `mccd_list_states`, `mccd_health` | mccdindia (`/query`, `/causes`, `/chapters`, `/categorize`, `/states`, `/health`) |
| Census of India | `census_query`, `census_population`, `census_population_projection`, `census_list_states`, `census_list_geographies`, `census_list_variables`, `census_search_variables`, `census_health` | censusindia (`/query`, `/population`, `/states`, `/geographies`, `/variables`, `/search`, `/health`) |
| SRS mortality & life tables | `srs_query_cod`, `srs_query_life_table`, `srs_query_bulletin`, `srs_query_stat_report`, `srs_summary_indicators`, `srs_life_expectancy_trend`, `srs_epi_transition`, `srs_arriaga_decompose` + discovery tools (`srs_list_states`, `srs_list_life_table_periods`, `srs_list_cod_tables`, `srs_list_cod_periods`, `srs_list_bulletin_years`, `srs_list_bulletin_indicators`, `srs_list_stat_report_years`, `srs_list_stat_report_indicators`, `srs_available_periods`) + `srs_health` | srsindia |
| Household consumption survey | `query_consumption` | consumptionsurveyindia (`/health`, `/overview`, `/items/search`, `/items/catalogue`, `/shares/food-group`, `/state/consumption`, `/item/trends`, `/sql`) |
| NSS health survey | `query_healthsurvey` | healthsurveyindia (`/health`, `/overview`, `/diseases`, `/diseases/lookup`, `/query/disease`, `/query/state`, `/query/disease/trend`, `/state/summary`, `/variables/search`, `/sql`) |
| Meta | `tool_guide`, `api_health` | — |

Every backend REST endpoint is wrapped by exactly one MCP tool.

## Files

- `server.py` — the FastMCP server and all 43 data tools, plus a `TOOL_REGISTRY` that drives `tool_guide`
- `requirements.txt` — Python dependencies
- `.env.example` — template for configuring API URLs
- `.env` — copy of `.env.example` (optional; set by `load_dotenv()`)
- `tests/test_server.py` — mocked unit tests (no live backends required)

## Install

```sh
cd mcp_forall
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
```

Run the tests from the **parent directory** (the one containing `mcp_forall`,
e.g. `.../DH307`), because the tests import the package as `mcp_forall`:

```sh
.venv\Scripts\python.exe -m unittest discover -s mcp_forall/tests -p "test_server.py" -v
```

## Configure API URLs

The wrapper calls the URLs configured by `CENSUS_API_URL`, `HMIS_API_URL`,
`MCCD_API_URL`, `CONSUMPTION_API_URL`, `HEALTHSURVEY_API_URL`, and
`SRS_API_URL`. Defaults are `8895`, `8765`, `8585`, `8795`, `8685`, and
`8686`, respectively.

Override with environment variables:

```sh
export CENSUS_API_URL=http://127.0.0.1:8895
export HMIS_API_URL=http://127.0.0.1:8765
export MCCD_API_URL=http://127.0.0.1:8585
export CONSUMPTION_API_URL=http://127.0.0.1:8795
export HEALTHSURVEY_API_URL=http://127.0.0.1:8685
export SRS_API_URL=http://127.0.0.1:8686
```

or copy `.env.example` to `.env` and edit it (loaded automatically by
`server.py` via `python-dotenv`).

## Connect to any LLM (MCP client)

This server exposes its 43 tools over the Model Context Protocol (MCP) on
stdio. Any MCP-capable client can launch and query it — Gemini CLI, Claude
Desktop, VS Code, Cursor, or a custom client — with no server-side changes.
The client is only a process manager: it spawns `server.py` and exchanges
JSON over stdin/stdout.

A client needs two absolute paths — the Python interpreter in the venv and
`server.py`. Those are machine-specific (no client expands
`${workspaceFolder}`-style variables uniformly), so fill them in per device.
Everything else in the block below is generic.

1. Create the venv and install dependencies (skip if already done):

   ```sh
   python -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt   # Windows
   .venv/bin/python -m pip install -r requirements.txt            # macOS / Linux
   ```

2. Register the server in your client, replacing `REPO_ROOT` with the
   absolute path to your clone of this repo:

   ```json
   {
     "mcpServers": {
       "india-health-mcp": {
         "command": "REPO_ROOT/mcp_forall/.venv/Scripts/python.exe",
         "args": [
           "REPO_ROOT/mcp_forall/server.py"
         ],
         "env": {
           "CENSUS_API_URL": "http://127.0.0.1:8895",
           "HMIS_API_URL": "http://127.0.0.1:8765",
           "MCCD_API_URL": "http://127.0.0.1:8585",
           "SRS_API_URL": "http://127.0.0.1:8686",
           "CONSUMPTION_API_URL": "http://127.0.0.1:8795",
           "HEALTHSURVEY_API_URL": "http://127.0.0.1:8685"
         }
       }
     }
   }
   ```

   On macOS/Linux the interpreter is `.venv/bin/python` instead of
   `.venv/Scripts/python.exe`. Only `command` and `args` change per machine;
   the `env` URLs are the server's defaults and can stay as-is unless a
   backend runs on a different host/port.

3. Drop that block into your client's MCP config. The schema is the same
   everywhere; only the config file and top-level key differ:

   | Client        | Config file                                        | Key          |
   | ------------- | -------------------------------------------------- | ------------ |
   | Gemini CLI    | `~/.gemini/settings.json` or project `.gemini/settings.json` | `mcpServers` |
   | VS Code       | `.vscode/mcp.json`                                 | `servers` (adds `type: "stdio"` and `cwd`) |
   | Claude Desktop| `claude_desktop_config.json`                       | `mcpServers` |
   | Cursor        | `.cursor/mcp.json`                                 | `mcpServers` |

   Repo examples: `.gemini/settings.json` is this block filled in for the
   machine it was written on (a copy-and-tweak baseline), and
   `.vscode/mcp.json` is portable via `${workspaceFolder}`.

4. Restart the client. It spawns the server over stdio the first time a
   query needs one of the six backends.

For a programmatic client, connect an MCP stdio `ClientSession` with the
Python SDK, pointing `command`/`args` at the venv interpreter and
`server.py` as above.

## Invoke query_hmis

Once registered, ask your LLM (through its MCP client) to call `query_hmis`
with your filters. For example:

> "Query HMIS for Neonatal Deaths due to Asphyxia in Maharashtra from
> Apr 2023 to Mar 2024"

Or call it directly from Python:

```python
from server import query_hmis

result = query_hmis(
    indicator="Neonatal Deaths due to Asphyxia",
    geography="state",
    state="Maharashtra",
    from_date="Apr 2023",
    to_date="Mar 2024",
)
```

The tool returns `{"count": ..., "rows": [...]}`. Multiple state/district/
sector values must be comma-separated, matching the REST API (e.g.
`state="Maharashtra, Gujarat"`). Not sure of the exact indicator name? Call
`hmis_list_indicators(pattern="neonatal")` first.

## Invoke query_mccd

Ask your LLM to query cause-of-death data. For example:

> "How many cardiovascular deaths were there in Kerala from 2018 to 2022?"

Or call directly from Python:

```python
from server import query_mccd

result = query_mccd(
    table="cause",
    cause="IX.",
    state="Kerala",
    year="2018:2022",
    sex="T",
)
```

The `table` param selects the data granularity. Common choices:
- `deaths` — state-wise absolute death counts
- `cause` — state-level deaths by major cause group
- `age` — India-level age-disaggregated deaths
- `trend` — multi-year death count trends

The `year` param accepts a single year (`"2020"`), comma-separated
years (`"2015,2016,2017"`), or a range (`"2015:2020"`). Use `mccd_causes`
to find valid cause strings or ICD-10 codes.

## SRS tools

The wrapper exposes population-level mortality, life-table, and vital
statistics from `srsindia`. Example:

```python
from server import srs_query_life_table, srs_query_bulletin

result = srs_query_life_table(
    state="Kerala",
    period="2020-2024",
    category="Total",
)

imr = srs_query_bulletin(
    indicator="imr",
    state="India",
    year=2024,
)
```

Discovery tools (`srs_list_states`, `srs_list_cod_periods`,
`srs_list_life_table_periods`, `srs_list_bulletin_indicators`,
`srs_list_stat_report_indicators`, ...) let the model find valid periods,
tables, years, and indicators before querying.

## Census tools

```python
from server import census_query, census_population_projection

result = census_query(year=2011, geography="state", variables="population,literacy_rate")
projection = census_population_projection(year=2031, geography="district", state="Maharashtra")
```

Supported census years are 1901, 1911, 1921, 1931, 1941, 1951, 1961, 1971,
1981, 1991, 2001, 2011. Population projections go through 2031 at district
level.

## Survey tools

Both survey tools use an operation name and a `params` object matching the
underlying API:

```python
from server import query_consumption, query_healthsurvey

query_consumption("food_group_shares", {"by": "round"})
query_consumption("item_trends", {"item": "rice", "by": "round"})
query_healthsurvey("disease_query", {
  "disease": "diabetes", "table": "hospitalization", "by": "state"
})
query_healthsurvey("disease_lookup", {"query": "malaria"})
```

Consumption operations are `health`, `overview`, `items_search`,
`items_catalogue`, `food_group_shares`, `state_consumption`, `item_trends`,
and `sql`. Health survey operations are `health`, `overview`, `diseases`,
`disease_lookup`, `disease_query`, `state_query`, `disease_trend`,
`state_summary`, `variables_search`, and `sql`.

> **Consumption item catalogue — installed.** The HCES item catalogue
> (`hces_item_catalogue.csv`) ships with the package at
> `consumptionsurveyindia/inst/extdata/concordance/hces_item_catalogue.csv`
> and is loaded by the REST API (see `inst/server/api.R`), so `/health`
> reports `catalogue_loaded: true`. Item names and food groups resolve for
> the HCES rounds (2022-23/2023-24) as well as the 57th–62nd rounds.

## Health checks

`api_health()` probes the `/health` endpoint of all six backends and
returns one entry per backend, isolating failures. Call it first if a data
tool reports an API is unavailable.

## Prerequisites

All six R packages must be serving their Plumber APIs before the MCP server
can respond to queries:

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

All `serve()` functions resolve their Plumber files via `system.file(...)`,
so each package must be **installed** (not just loaded with
`devtools::load_all()`). The consumption and health survey APIs read their
parquet datasets from `ICS_DATA_DIR` / `IHS_DATA_DIR` (set these on a new
machine — otherwise they fall back to paths near this repo, then to a
hardcoded local default). Pass `data_dir` to `serve()` to override
explicitly.

## Portability across machines

Things that are device-specific, and what to do on a fresh clone:

- **`.venv` is git-ignored** — recreate it (`python -m venv .venv`, then
  `pip install -r requirements.txt`). It is *not* a package prerequisite.
- **`.gemini/settings.json` / `.vscode/mcp.json`** — client configs contain
  absolute paths for *this* machine — update `command`/`args` to your clone
  path (`.vscode/mcp.json` uses `${workspaceFolder}` and needs no editing).
- **`.env`** is optional. Copy `.env.example` for localhost defaults; it is
  loaded from the `mcp_forall/` directory (script-relative), so the server
  behaves identically no matter which CWD spawns it.
- **R backends** must each be installed; start them with `serve()` (see
  above) and set `ICS_DATA_DIR` / `IHS_DATA_DIR` to point at your
  `consumptionsurveyindiadataset/` and `healthserveyindiadataset/`
  directories. The dataset directories are not R packages and cannot be
  resolved via `system.file()`.
- **Tests** derive expected URLs from the module's URL constants, so they
  pass regardless of `.env`/environment overrides; no test edits are needed
  per machine.