<p align="center">
  <img src="site/logo/logo.png" height="160" alt="BharatVitals logo">
</p>

<h1 align="center">BharatVitals</h1>
<p align="center" class="tagline">India's health and demographic data for AI assistants, over MCP</p>

BharatVitals connects Claude and other AI assistants to India's official health
and demographic statistics through the
[Model Context Protocol](https://modelcontextprotocol.io) (MCP). It allows
you to ask questions in plain language, and the assistant looks up the
published figures: health-service indicators, causes of death, life tables,
registered births and deaths, and Census population and demographic statistics.

## Quick setup

Add this URL to your AI assistant:

```text
https://bharatvitals.in/mcp
```

The server needs no API key. You can ask the
assistant to add it for you, or paste one of the snippets below into its
configuration file. (This repository's `.mcp.json` registers the same server
for Claude Code sessions started inside the repo.)

## Claude

In Claude.ai or Claude Desktop:

1. Open *Settings* from the profile menu.
2. Select *Connectors* in the settings sidebar.
3. Choose *Add custom connector*.
4. Name the connector `BharatVitals` and paste the MCP server URL.
5. Approve the tools you want Claude to use.

Then try a question such as "What was Kerala's infant mortality rate in 2020?"

## Other assistants

### Claude Code

Run this command in your terminal:

```bash
claude mcp add --transport http bharatvitals https://bharatvitals.in/mcp
```

Or add it to `~/.claude.json` by hand:

```json
"mcpServers": {
  "bharatvitals": {
    "type": "http",
    "url": "https://bharatvitals.in/mcp"
  }
}
```

Restart Claude Code to load the server. Its [Claude Code MCP documentation](https://docs.claude.com/en/docs/claude-code/mcp) lists the other settings.

### Codex

Run this command in your terminal:

```bash
codex mcp add bharatvitals --url https://bharatvitals.in/mcp
```

Or add it to `~/.codex/config.toml` by hand:

```toml
[mcp_servers.bharatvitals]
url = "https://bharatvitals.in/mcp"
```

Restart Codex to load the server. Its [Codex MCP documentation](https://developers.openai.com/codex/mcp) lists the other settings.

### Hermes

Run this command in your terminal:

```bash
hermes mcp add bharatvitals --url "https://bharatvitals.in/mcp"
```

Or add it to `~/.hermes/config.yaml` by hand:

```yaml
mcp_servers:
  bharatvitals:
    url: "https://bharatvitals.in/mcp"
```

Restart Hermes to load the server. Its [Hermes MCP documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp) lists the other settings.

### Goose

Run this command in your terminal:

```bash
goose configure   # Add Extension → Remote Extension (Streamable HTTP)
```

Or add it to `~/.config/goose/config.yaml` by hand:

```yaml
extensions:
  bharatvitals:
    enabled: true
    type: streamable_http
    name: bharatvitals
    uri: https://bharatvitals.in/mcp
    timeout: 300
```

Restart Goose to load the server. Its [Goose MCP documentation](https://goose-docs.ai/docs/getting-started/using-extensions) lists the other settings.

### OpenClaw

Run this command in your terminal:

```bash
openclaw mcp add bharatvitals --url https://bharatvitals.in/mcp --transport streamable-http
```

Or add it to `~/.openclaw/openclaw.json` by hand:

```json
{
  "mcp": {
    "servers": {
      "bharatvitals": {
        "url": "https://bharatvitals.in/mcp",
        "transport": "streamable-http"
      }
    }
  }
}
```

Restart OpenClaw to load the server. Its [OpenClaw MCP documentation](https://docs.openclaw.ai/cli/mcp) lists the other settings.

### Cursor

Add it to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "bharatvitals": { "url": "https://bharatvitals.in/mcp" }
  }
}
```

Restart Cursor to load the server. Its [Cursor MCP documentation](https://docs.cursor.com/context/model-context-protocol) lists the other settings.

### VS Code

Add it to `.vscode/mcp.json`:

```json
{
  "servers": {
    "bharatvitals": { "type": "http", "url": "https://bharatvitals.in/mcp" }
  }
}
```

Restart VS Code to load the server. Its [VS Code MCP documentation](https://code.visualstudio.com/docs/copilot/chat/mcp-servers) lists the other settings.

### Gemini CLI

Run this command in your terminal:

```bash
gemini mcp add --transport http bharatvitals https://bharatvitals.in/mcp
```

Or add it to `~/.gemini/settings.json` by hand:

```json
{
  "mcpServers": {
    "bharatvitals": { "httpUrl": "https://bharatvitals.in/mcp" }
  }
}
```

Restart Gemini CLI to load the server. Its [Gemini CLI MCP documentation](https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md) lists the other settings.

### Other LLMs

[llms.txt](https://bharatvitals.in/llms.txt) gives the server URL,
usage notes and each tool's parameters as plain text, for assistants that read
it.

## Data

| Source | What it covers | Coverage |
|--------|----------------|----------|
| HMIS, Health Management Information System | 840+ state-level and 845 district-level health-service indicators: immunisation, maternal care, disease cases | 36 states, 700+ districts, monthly from April 2008 |
| MCCD, Medical Certification of Cause of Death | ICD-10 coded causes of death by age and sex | 36 states, 2008-2023 |
| SRS, Sample Registration System | Life tables, causes of death, birth, death and infant mortality rates, fertility | 36 states; bulletin series 1997-2024, life tables and cause-of-death series 2007-2024 |
| CRS, Civil Registration System | Registered births, deaths, infant deaths and still births; registration completeness | States and 700+ districts, 2009-2023 |
| Census of India | Population, literacy, workers, households by state, district and subdistrict; population projections | 1901-2011; projections to 2036 (states) and 2031 (districts) |

The figures come from published government tables, cleaned by the open R
packages [hmisindia](https://hmisindia.saketlab.org),
[srsindia](https://srsindia.saketlab.org),
[censusindia](https://censusindia.saketlab.org),
[mccdindia](https://mccdindia.saketlab.org),
[crsindia](https://crsindia.saketlab.org).

## Example questions

- How has institutional delivery changed in Bihar since 2015?
- What are the leading causes of death among women in Kerala?
- Decompose the change in life expectancy in India between 2007-2011 and 2019-2023 by age.
- Which districts of Uttar Pradesh registered the fewest births per 1,000 people in 2020?
- What was Maharashtra's literacy rate in 2011, and its projected population in 2031?

## Tools

The server registers 59 tools, grouped by source:

| Group | Count | Highlights |
|-------|-------|------------|
| HMIS | 7 | `query_hmis`, `hmis_list_indicators`, `hmis_periodicity`, `hmis_decompose` |
| MCCD | 6 | `query_mccd`, `mccd_causes`, `mccd_categorize` |
| Census of India | 8 | `census_query`, `census_population`, `census_population_projection` |
| SRS | 18 | `srs_query_life_table`, `srs_query_cod`, `srs_arriaga_decompose` |
| CRS | 18 | `crs_births`, `crs_deaths`, `crs_vital_rates`, `crs_adjusted_events` |
| Diagnostics | 2 | `api_health`, `tool_guide` |

The `list_` tools return valid states, indicators, periods and table names,
so the assistant can check its inputs before it queries. `api_health` probes
each of the five backends and `tool_guide` explains which tool to use. SRS and
CRS also expose six read-only MCP resources: `srs://states`,
`srs://life_table_periods`, `srs://cod_tables`, `srs://bulletin_indicators`,
`crs://states` and `crs://tables`.

<!-- tools -->

[llms.txt](https://bharatvitals.in/llms.txt) lists every tool with its parameters.

## How it works

```text
MCP client (Claude, Claude Code, Cursor, ...)
        |  MCP over stdio or streamable HTTP
        v
bharatvitals-mcp (Python, FastMCP)        mcp/bharatvitals/
        |  httpx
        v
R Plumber REST API per data source        hmisindia, mccdindia, srsindia,
        |                                 crsindia and censusindia
Parquet / Arrow / DuckDB / CSV
```

The Python server is a thin proxy: each tool validates its parameters and
forwards the call over HTTP to the Plumber API of the corresponding R
package. Unless `BHARATVITALS_<SOURCE>_URL` points at an already-running
instance, the server starts that package's Plumber API on a free local port
the first time a tool needs it, waits for its `/health` endpoint, and stops
the process at exit.

## Run it locally

Prerequisites: Python 3.10+ and [uv](https://docs.astral.sh/uv/). To query a
source locally you also need R and that source's R package installed; sources
without an installed R package simply report that their backend is
unavailable.

```bash
git clone https://github.com/saketlab/bharatvitals.git
cd bharatvitals/mcp
uv run bharatvitals-mcp                                            # stdio
MCP_TRANSPORT=http MCP_PORT=9000 uv run bharatvitals-mcp           # HTTP at http://127.0.0.1:9000/mcp
```

## Configuration

All settings are environment variables, read at startup:

| Variable | Default | Purpose |
|----------|---------|---------|
| `MCP_TRANSPORT` | `stdio` | `stdio`, `http` or `streamable-http` |
| `MCP_HOST` | `127.0.0.1` | Bind address for the HTTP transport |
| `MCP_PORT` | `9000` | Port for the HTTP transport |
| `MCP_PATH` | `/mcp` | HTTP endpoint path (see note below) |
| `MCP_STATELESS_HTTP` | `true` | Stateless HTTP mode (see note below) |
| `MCP_ALLOWED_HOSTS` | `127.0.0.1:*,localhost:*,[::1]:*` | Accepted `Host` headers (see note below) |
| `REQUEST_TIMEOUT_SECONDS` | `30` | Timeout for calls to the backend APIs |
| `BHARATVITALS_HMIS_URL` | `http://127.0.0.1:8765` | Use an already-running HMIS API; skips local R startup |
| `BHARATVITALS_MCCD_URL` | `http://127.0.0.1:8585` | Same for MCCD |
| `BHARATVITALS_SRS_URL` | `http://127.0.0.1:8686` | Same for SRS |
| `BHARATVITALS_CRS_URL` | `http://127.0.0.1:8484` | Same for CRS |
| `BHARATVITALS_CENSUS_URL` | `http://127.0.0.1:8895` | Same for Census (a remote base URL ends in `/api`) |
| `BHARATVITALS_RSCRIPT` | *(unset)* | Full path to `Rscript` for a non-standard R install |
| `BHARATVITALS_<SOURCE>_PLUMBER_R` | *(unset)* | Full path to one source's Plumber entry file, skipping R package discovery |

**HTTP note.** `MCP_PATH`, `MCP_STATELESS_HTTP` and `MCP_ALLOWED_HOSTS` are
passed to FastMCP's HTTP transport. On fastmcp 3.x (the installed version)
`allowed_hosts` is not a supported keyword, so `main()` catches the
`TypeError` and falls back to plain host/port binding: the endpoint is served
at FastMCP's default path `/mcp` with sessions enabled. `MCP_HOST` and
`MCP_PORT` always take effect.

## Testing

From the `mcp/` directory:

```bash
uv run python -m unittest discover -s tests   # tool layer, backends mocked
uv run pytest test_client.py                  # R discovery / auto-start client
```

Neither suite needs R or a running backend.

## Troubleshooting

- **A tool reports that a backend is unavailable.** Call `api_health`; it
  probes `/health` on each of the five backends and reports them
  individually. A source that failed to auto-start is not retried for 60
  seconds.
- **`Rscript.exe was not found`.** Install R and add its `bin` directory to
  `PATH`, or set `BHARATVITALS_RSCRIPT` to the full path of the executable.
  On Windows the client also searches the standard
  `C:\Program Files\R\R-*\bin` folders and `R_HOME`.
- **`plumber.R not found for '<source>'`.** That source's R package is not
  installed (install it from GitHub), or set
  `BHARATVITALS_<SOURCE>_PLUMBER_R` to the entry file's full path.
- **A remote or pre-started backend URL does not work.** The value of
  `BHARATVITALS_<SOURCE>_URL` must be the API base URL (for example, a
  remote Census API base URL ends in `/api`).

## Deployment

Two GitHub Actions workflows deploy from `main`:

- `deploy-mcp.yaml` — on changes under `mcp/`, SSHes into the host, refreshes
  the checkout, installs the package into `.venv`, installs and restarts the
  systemd user unit `bharatvitals-mcp.service`, and waits for the server to
  answer at `127.0.0.1:9000/mcp`.
- `deploy-site.yaml` — on changes to the README, site assets or generator,
  runs `mcp/test_client.py`, rebuilds the landing page and `llms.txt` with
  `scripts/build_site.py`, rsyncs the output to
  `/var/www/r-pkgdown/bharatvitals/docs`, and installs the Nginx vhost.

Nginx terminates TLS for `bharatvitals.saketlab.org`, serves the generated
landing page (built from this README plus the server's live tool list;
`docs/` is gitignored build output), and proxies `/mcp` to the local server
on port 9000. The systemd unit runs the server with `MCP_TRANSPORT=http` and
pins the HMIS, MCCD, SRS, CRS and Census backends to locally running R APIs
via `BHARATVITALS_*_URL`.

## Issues

If you spot a wrong number or want another dataset, open an issue on
[GitHub](https://github.com/saketlab/bharatvitals/issues).
