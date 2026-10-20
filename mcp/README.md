# bharatvitals-mcp

MCP server that makes India's public health and demographic datasets queryable
from AI assistants. The hosted server is at `https://bharatvitals.saketlab.org/mcp`;
see the [top-level README](../README.md) for client setup and the data overview.

## Run from a checkout

The package is not on PyPI. Requires Python 3.10+ and
[uv](https://docs.astral.sh/uv/). From this directory:

```bash
uv run bharatvitals-mcp                                                  # stdio
MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT=9000 uv run bharatvitals-mcp   # streamable HTTP at /mcp
```

`MCP_TRANSPORT` accepts `stdio` (default), `http` and `streamable-http`.
`MCP_HOST`, `MCP_PORT`, `MCP_PATH`, `MCP_STATELESS_HTTP` and
`MCP_ALLOWED_HOSTS` configure the HTTP transport, and
`REQUEST_TIMEOUT_SECONDS` (default 30) the backend call timeout. With fastmcp
3.x the transport rejects `MCP_ALLOWED_HOSTS`, so `main()` falls back to
plain host/port binding and the endpoint is served at FastMCP's default path
`/mcp`; `MCP_HOST` and `MCP_PORT` always take effect.

## Prerequisites

Each data source needs its R package installed. On first tool call the server
auto-starts a Plumber API for that source on a free local port and stops it at
exit. To skip auto-start, point at an already-running instance (local or
remote) with the source's base URL:

```bash
export BHARATVITALS_HMIS_URL=http://127.0.0.1:8765
export BHARATVITALS_MCCD_URL=http://127.0.0.1:8585
export BHARATVITALS_SRS_URL=http://127.0.0.1:8686
export BHARATVITALS_CRS_URL=http://127.0.0.1:8484
export BHARATVITALS_CENSUS_URL=http://127.0.0.1:8895
export BHARATVITALS_CONSUMPTION_URL=http://127.0.0.1:8795
export BHARATVITALS_HEALTHSURVEY_URL=http://127.0.0.1:8685
```

The first five URLs mirror the ports pinned in
`.github/services/bharatvitals-mcp.service`; the two survey defaults are the
client's own. Override any of them to use your own instance. A remote base
URL must be the API root (for example, the Census API base URL ends in
`/api`). A source that fails to auto-start is not retried for 60 seconds.

On Windows, the client looks for `Rscript.exe` on `PATH`, under `R_HOME`, and
in the standard `C:\Program Files\R\R-*\bin` installation folders. For a
custom R installation, set `BHARATVITALS_RSCRIPT` to the full executable path
in the environment used to start the MCP server, for example:

```powershell
$env:BHARATVITALS_RSCRIPT = 'C:\Program Files\R\R-4.6.1\bin\Rscript.exe'
```

`BHARATVITALS_<SOURCE>_PLUMBER_R` (for example
`BHARATVITALS_CRS_PLUMBER_R`) overrides the discovered Plumber entry file for
one source.

The NSS survey packages ship their Plumber entry point at `inst/server/api.R`
rather than `inst/plumber/plumber.R`; the client handles both.

`api_health` probes `/health` on every source and reports each one separately;
call it when a tool says an API is unreachable.

## Tools

61 tools and 6 MCP resources. The HMIS, MCCD, SRS, Census and survey tools
are vendored from the `mcp_forall` project; the CRS tools and the SRS/CRS
resources come from the `bharatvitals/tools/` modules. Every tool routes
through `bharatvitals.runtime.client` (a `BharatVitalsClient`), so tests mock
that boundary. The site lists every tool, and
[llms.txt](https://bharatvitals.saketlab.org/llms.txt) carries each one's
parameters.

## MCP Resources

SRS and CRS also register read-only MCP resources:

- `srs://states`, `srs://life_table_periods`, `srs://cod_tables`, `srs://bulletin_indicators`
- `crs://states`, `crs://tables`

## Tests

From this directory (no R or running backend required):

```bash
uv run python -m unittest discover -s tests   # tool layer, backends mocked
uv run pytest test_client.py                  # R discovery / auto-start client
```

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

The Python server is a thin proxy. Each R package runs its own Plumber
process, started on demand and killed on exit.
