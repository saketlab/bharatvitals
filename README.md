<p align="center">
  <img src="site/logo/logo.png" height="160" alt="BharatVitals logo">
</p>

<h1 align="center">BharatVitals</h1>
<p align="center" class="tagline">India's health and demographic data for AI assistants, over MCP</p>

BharatVitals is an [MCP](https://modelcontextprotocol.io) server that gives
Claude and other AI assistants access to India's official health and
demographic statistics: health-service indicators, causes of death, life
tables, registered births and deaths, and Census data.

## Quick setup

Add this URL to your AI assistant:

```text
https://bharatvitals.in/mcp
```

The server needs no API key. Ask your assistant to add it, or use the
configuration for your client below. The `.mcp.json` file in this repository
adds the server to Claude Code sessions in the repository.

## Claude

In Claude.ai or Claude Desktop:

1. Open *Settings* from the profile menu.
2. Select *Connectors* in the settings sidebar.
3. Choose *Add custom connector*.
4. Name the connector `BharatVitals` and paste the MCP server URL.
5. Approve the tools you want Claude to use.

Then ask a question, for example "What was Kerala's infant mortality rate in 2020?"

## Other assistants

### Claude Code

Run:

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

Restart Claude Code. For other settings, see the [Claude Code MCP documentation](https://docs.claude.com/en/docs/claude-code/mcp).

### Codex

Run:

```bash
codex mcp add bharatvitals --url https://bharatvitals.in/mcp
```

Or add it to `~/.codex/config.toml` by hand:

```toml
[mcp_servers.bharatvitals]
url = "https://bharatvitals.in/mcp"
```

Restart Codex. For other settings, see the [Codex MCP documentation](https://developers.openai.com/codex/mcp).

### Hermes

Run:

```bash
hermes mcp add bharatvitals --url "https://bharatvitals.in/mcp"
```

Or add it to `~/.hermes/config.yaml` by hand:

```yaml
mcp_servers:
  bharatvitals:
    url: "https://bharatvitals.in/mcp"
```

Restart Hermes. For other settings, see the [Hermes MCP documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp).

### Goose

Run:

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

Restart Goose. For other settings, see the [Goose MCP documentation](https://goose-docs.ai/docs/getting-started/using-extensions).

### OpenClaw

Run:

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

Restart OpenClaw. For other settings, see the [OpenClaw MCP documentation](https://docs.openclaw.ai/cli/mcp).

### Cursor

Add it to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "bharatvitals": { "url": "https://bharatvitals.in/mcp" }
  }
}
```

Restart Cursor. For other settings, see the [Cursor MCP documentation](https://docs.cursor.com/context/model-context-protocol).

### VS Code

Add it to `.vscode/mcp.json`:

```json
{
  "servers": {
    "bharatvitals": { "type": "http", "url": "https://bharatvitals.in/mcp" }
  }
}
```

Restart VS Code. For other settings, see the [VS Code MCP documentation](https://code.visualstudio.com/docs/copilot/chat/mcp-servers).

### Gemini CLI

Run:

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

Restart Gemini CLI. For other settings, see the [Gemini CLI MCP documentation](https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md).

### Other LLMs

[llms.txt](https://bharatvitals.in/llms.txt) gives the server URL, the usage
notes and the parameters of each tool as plain text.

## Data

| Source | What it covers | Coverage |
|--------|----------------|----------|
| HMIS, Health Management Information System | 840+ state-level and 845 district-level health-service indicators: immunisation, maternal care, disease cases | 36 states, 700+ districts, monthly from April 2008 |
| MCCD, Medical Certification of Cause of Death | ICD-10 coded causes of medically certified deaths by age and sex | 36 states, 2008-2024 |
| SRS, Sample Registration System | Life tables, causes of death, birth, death, infant and maternal mortality rates, fertility, rates by NSSO region | 36 states. Bulletins 1997-2024, life tables and causes of death 2007-2024 |
| CRS, Civil Registration System | Registered births, deaths, infant deaths and still births, registration completeness | States and 700+ districts, 2009-2023 |
| Census of India | Population, literacy, workers, households by state, district and subdistrict, population projections | 1901-2011. Projections to 2036 (states) and 2031 (districts) |

The data comes from published government tables. These open R packages
clean the tables: [hmisindia](https://hmisindia.saketlab.org),
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

<!-- tools -->

[llms.txt](https://bharatvitals.in/llms.txt) lists every tool with its parameters.


## Issues

To report an incorrect value or to ask for a new dataset, open an issue on
[GitHub](https://github.com/saketlab/bharatvitals/issues).
