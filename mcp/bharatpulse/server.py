from fastmcp import FastMCP

from bharatpulse.client import BharatPulseClient
from bharatpulse.tools import crs, hmis, mccd, srs

mcp = FastMCP(
    "bharatpulse",
    instructions=(
        "India public health data. Tools prefixed by source: hmis_*, mccd_*, srs_*, crs_*. "
        "HMIS: 840+ health indicators, 36 states, 700+ districts, monthly 2008-2025. "
        "Start with hmis_list_indicators, then hmis_query. "
        "MCCD: Cause-of-death, 36 states, 2008-2023, ICD-10 coded. "
        "Start with mccd_list_chapters or mccd_list_causes, then mccd_query. "
        "SRS: Life tables, cause-of-death, vital rates, 36 states, 1970-present. "
        "Start with srs_available_periods or srs_summary_indicators. "
        "CRS: Registered births, deaths, infant deaths, still births, 36 states, "
        "700+ districts, 2009-2023. Start with crs_list_tables or crs_vital_rates."
    ),
)

_client = BharatPulseClient()

hmis.register(mcp, _client)
mccd.register(mcp, _client)
srs.register(mcp, _client)
crs.register(mcp, _client)
# nfhs5.register(mcp, _client)
# nfhs4.register(mcp, _client)
# census.register(mcp, _client)


def main() -> None:
    import os

    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "http":
        host = os.environ.get("MCP_HOST", "127.0.0.1")
        port = int(os.environ.get("MCP_PORT", "9000"))
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
