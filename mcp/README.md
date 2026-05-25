# bharatpulse-mcp

MCP server that makes various public health datasets queryable from AI assistants. 

## Install

```bash
uvx --from bharatpulse-mcp bharatpulse-mcp

# or add to a project
uv add bharatpulse-mcp
```

### Claude Code

Add to `.mcp.json`:

```json
{
  "mcpServers": {
    "bharatpulse": {
      "command": "uvx",
      "args": ["--from", "bharatpulse-mcp", "bharatpulse-mcp"]
    }
  }
}
```

### HTTP mode

```bash
MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT=9000 bharatpulse-mcp
```

## Prerequisites

Each data source needs its R package installed. On first tool call the server auto-starts a Plumber API for that source. To skip auto-start, point at an already-running instance:

```bash
export BHARATPULSE_HMIS_URL=http://127.0.0.1:8001
export BHARATPULSE_SRS_URL=http://127.0.0.1:8002
export BHARATPULSE_MCCD_URL=http://127.0.0.1:8003
export BHARATPULSE_CRS_URL=http://127.0.0.1:8004
```

## Services

Four data sources are wired up as of now.

### HMIS — Health Management Information System

900+ health indicators, 36 states, 700+ districts, monthly from April 2008 to present.

| Tool | What it does |
|------|-------------|
| `hmis_list_states` | 36 state/UT names |
| `hmis_list_districts` | State-district pairs; filter by state |
| `hmis_list_indicators` | Search indicators (substring, regex, or fuzzy) |
| `hmis_query` | Pull indicator values with state/district/sector/date filters |
| `hmis_detect_periodicity` | Find seasonal cycles (periodogram or Lomb-Scargle) |
| `hmis_decompose_series` | STL decomposition: trend + season + residual |

### SRS — Sample Registration System

Life tables, cause-of-death, and vital rates across 36 states, 1970 onward.

| Tool | What it does |
|------|-------------|
| `srs_list_states` | 36 state/UT names |
| `srs_list_life_table_periods` | 5-year rolling window periods |
| `srs_list_cod_tables` | Cause-of-death table slugs and metadata |
| `srs_list_cod_periods` | CoD reporting windows (2-3 year spans) |
| `srs_list_bulletin_years` | Years with Bulletin data (1997-2024) |
| `srs_available_periods` | Coverage summary across life tables, CoD, and bulletins |
| `srs_life_expectancy_trend` | National e0 from 1970-75 to present |
| `srs_summary_indicators` | e0, under-5 mortality (5q0), adult mortality (45q15) |
| `srs_epi_transition` | NCD vs communicable share over time |
| `srs_arriaga_decompose` | Arriaga decomposition of e0 change by age group |
| `srs_query_life_table` | Full abridged life tables (nqx, lx, nlx, ex) |
| `srs_query_cod` | Cause-of-death data by table slug |
| `srs_query_bulletin` | CBR, CDR, NGR, IMR from SRS Bulletins |

### MCCD — Medical Certification of Cause of Death

ICD-10 coded cause-of-death records, 36 states, 2008-2023.

| Tool | What it does |
|------|-------------|
| `mccd_list_states` | 37 state/UT names (includes "All States" aggregate) |
| `mccd_list_causes` | Search causes by name or ICD-10 code |
| `mccd_list_chapters` | ICD-10 chapters, filterable by category |
| `mccd_query` | Deaths by table: counts, percentages, age breakdown, sub-cause |
| `mccd_categorize` | Same as query but adds Communicable / NCD / External tags |

### CRS — Civil Registration System

Registered births, deaths, infant deaths, still births. State and district level, 2009-2023.

| Tool | What it does |
|------|-------------|
| `crs_list_states` | 36 state/UT names |
| `crs_list_tables` | The 10 CRS table definitions |
| `crs_available_years` | Year coverage per table and state |
| `crs_vital_rates` | CBR, CDR, IMR, SBR, SRB from raw counts |
| `crs_adjusted_events` | Births/deaths corrected for registration completeness |
| `crs_births` | State births by sex and residence (Table 1) |
| `crs_deaths` | State deaths by sex and residence (Table 2) |
| `crs_infant_deaths` | State infant deaths (Table 3) |
| `crs_still_births` | State still births (Table 4) |
| `crs_registration` | Registration completeness percentages (Table 5) |
| `crs_deaths_by_age` | Deaths by age group and sex (Table 6) |
| `crs_district_births` | District births, 700+ districts (Table 7) |
| `crs_district_deaths` | District deaths (Table 8) |
| `crs_district_infant_deaths` | District infant deaths (Table 9) |
| `crs_district_still_births` | District still births (Table 10) |
| `crs_population_state` | MOHFW state population projections, 2011-2036 |
| `crs_population_district` | District population projections (LGD or Census 2011 boundaries) |

## MCP Resources

SRS and CRS also register read-only MCP resources:

- `srs://states`, `srs://life_table_periods`, `srs://cod_tables`, `srs://bulletin_indicators`
- `crs://states`, `crs://tables`

## How it works

```
MCP client (Claude, etc.)
        |
        v
bharatpulse-mcp  (Python, FastMCP)
        |  httpx
        v
R Plumber APIs   (one per data source, auto-started)
        |
        v
Parquet / Arrow / DuckDB / CSV
```

The Python server is a thin proxy. Each R package runs its own Plumber process, started on demand and killed on exit.
