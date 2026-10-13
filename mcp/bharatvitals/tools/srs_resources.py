import json
from typing import TYPE_CHECKING

from fastmcp import FastMCP

if TYPE_CHECKING:
    from bharatvitals.client import BharatVitalsClient

SOURCE = "srs"
PACKAGE = "srsindia"
LABEL = "SRS"
GUIDE = (
    "Static SRS lookups (states, life table periods, cause-of-death tables, "
    "bulletin indicators). SRS tools themselves are provided by the vendored "
    "mcp_forall layer."
)


def _to_json(data: object) -> str:
    return json.dumps(data)


def register(mcp: FastMCP, client: "BharatVitalsClient") -> None:

    @mcp.resource("srs://states")
    def srs_states_resource() -> str:
        """All 36 canonical state/UT names in SRS data (excludes 'India')."""
        return _to_json(client.get(SOURCE, "/states", {}))

    @mcp.resource("srs://life_table_periods")
    def srs_life_table_periods_resource() -> str:
        """Life table periods (5-year rolling windows)."""
        return _to_json(client.get(SOURCE, "/life_table_periods", {}))

    @mcp.resource("srs://cod_tables")
    def srs_cod_tables_resource() -> str:
        """Cause-of-death table metadata (slugs, descriptions, periods)."""
        return _to_json(client.get(SOURCE, "/cod_tables", {}))

    @mcp.resource("srs://bulletin_indicators")
    def srs_bulletin_indicators_resource() -> str:
        """Bulletin indicator codes: cbr, cdr, ngr, imr."""
        return _to_json(client.get(SOURCE, "/bulletin_indicators", {}))
