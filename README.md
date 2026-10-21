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
registered births and deaths, and the Census.

## Quick setup

Add this URL to your AI assistant:

```text
https://bharatvitals.in/mcp
```

The server needs no API key. You can ask the
assistant to add it for you, or paste one of the snippets below into its
configuration file.

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
| HMIS, Health Management Information System | 900+ health-service indicators: immunisation, maternal care, disease cases | 36 states, 700+ districts, monthly from April 2008 |
| MCCD, Medical Certification of Cause of Death | ICD-10 coded causes of death by age and sex | 36 states, 2008-2023 |
| SRS, Sample Registration System | Life tables, causes of death, birth, death and infant mortality rates, fertility | 36 states, 1970 onward |
| CRS, Civil Registration System | Registered births, deaths, infant deaths and still births; registration completeness | States and 700+ districts, 2009-2023 |
| Census of India | Population, literacy, workers, households by state, district and subdistrict; population projections | 1901-2011; projections to 2036 (states) and 2031 (districts) |

The figures come from published government tables, cleaned by the open R
packages [hmisindia](https://hmisindia.saketlab.org),
[srsindia](https://srsindia.saketlab.org),
[censusindia](https://censusindia.saketlab.org), [mccdindia](https://mccindia.saketlab.org) and 
[crsindia](https://crsindia.saketlab.org).

## Example questions

- How has institutional delivery changed in Bihar since 2015?
- What are the leading causes of death among women in Kerala?
- Decompose the change in life expectancy in India between 2007-2011 and 2019-2023 by age.
- Which districts of Uttar Pradesh registered the fewest births per 1,000 people in 2020?
- What was Maharashtra's literacy rate in 2011, and its projected population in 2031?

## Tools

Each tool name starts with its source (`hmis_`, `mccd_`, `srs_`, `crs_`,
`census_`). The `list_` tools return valid states, indicators, periods and table
names, so the assistant can check its inputs before it queries.

<!-- tools -->

[llms.txt](https://bharatvitals.in/llms.txt) lists every tool with its parameters.

## Run it locally

```bash
git clone https://github.com/saketlab/bharatvitals.git
cd bharatvitals/mcp
uv run bharatvitals-mcp
```

Each data source needs its R package installed. On the first call to a source
the server starts that package's Plumber API; set `BHARATVITALS_<SOURCE>_URL`
(for example `BHARATVITALS_HMIS_URL`) to use an API that is already running.

## Issues

If you spot a wrong number or want another dataset, open an issue on
[GitHub](https://github.com/saketlab/bharatvitals/issues).
