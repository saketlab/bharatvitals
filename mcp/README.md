# bharatvitals-mcp

MCP server that makes India's public health and demographic datasets queryable
from AI assistants. The hosted server is at `https://bharatvitals.saketlab.org/mcp`;
see the [top-level README](../README.md) for client setup.

## Run from a checkout

The package is not on PyPI. From this directory:

```bash
uv run bharatvitals-mcp                                                  # stdio
MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT=9000 uv run bharatvitals-mcp   # streamable HTTP at /mcp
```

## Prerequisites

Each data source needs its R package installed. On first tool call the server auto-starts a Plumber API for that source. To skip auto-start, point at an already-running instance:

```bash
export BHARATVITALS_HMIS_URL=http://127.0.0.1:8765
export BHARATVITALS_SRS_URL=http://127.0.0.1:8686
export BHARATVITALS_MCCD_URL=http://127.0.0.1:8585
export BHARATVITALS_CRS_URL=http://127.0.0.1:8484
export BHARATVITALS_CENSUS_URL=https://censusindia.saketlab.org/api
```

`bharatvitals_health` probes `/health` on every source and reports each one
separately; call it when a tool says an API is unreachable.

## Tools

The server builds its tool list from `bharatvitals/tools/`. The site lists every tool,
and [llms.txt](https://bharatvitals.saketlab.org/llms.txt) carries each one's parameters.

## MCP Resources

SRS and CRS also register read-only MCP resources:

- `srs://states`, `srs://life_table_periods`, `srs://cod_tables`, `srs://bulletin_indicators`
- `crs://states`, `crs://tables`

## How it works

```
MCP client (Claude, etc.)
        |
        v
bharatvitals-mcp (Python, FastMCP)
        |  httpx
        v
R Plumber APIs   (one per data source, auto-started)
        |
        v
Parquet / Arrow / DuckDB / CSV
```

The Python server is a thin proxy. Each R package runs its own Plumber process, started on demand and killed on exit.
