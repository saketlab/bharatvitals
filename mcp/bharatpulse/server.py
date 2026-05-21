from fastmcp import FastMCP

from bharatpulse.client import BharatPulseClient
from bharatpulse.tools import hmis

mcp = FastMCP(
    "bharatpulse",
    instructions=(
        "BharatPulse provides AI-accessible access to India's public health data. "
        "Tools are prefixed by source: hmis_* for HMIS data. "
        "Start with hmis_list_indicators to discover available indicators, "
        "then call hmis_query to retrieve time-series data. "
        "HMIS covers 840+ health indicators across 36 states and 700+ districts, "
        "monthly from April 2008 to March 2025."
    ),
)

_client = BharatPulseClient()

hmis.register(mcp, _client)
# nfhs5.register(mcp, _client)
# nfhs4.register(mcp, _client)
# srs.register(mcp, _client)
# mccd.register(mcp, _client)
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
