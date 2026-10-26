from typing import TYPE_CHECKING, Any, Literal, Callable, Optional

from fastmcp import FastMCP

from bharatvitals.tools._common import READ_ONLY, to_json

if TYPE_CHECKING:
    from bharatvitals.client import BharatVitalsClient

SOURCE = "crs"
PACKAGE = "crsindia"
LABEL = "CRS"
GUIDE = (
    "Use for registered births, deaths, infant deaths and still births by state "
    "or district (2009-2023), registration completeness and MOHFW population "
    "projections. Registration is incomplete in some states, so check "
    "crs_registration or use crs_adjusted_events. No India row. Start with "
    "crs_list_tables or crs_vital_rates. Its rates come from registered events; "
    "never average or swap them with SRS rates."
)


def register(mcp: FastMCP, client: "BharatVitalsClient") -> None:
    def get(endpoint: str, params: dict[str, Any]) -> str:
        return to_json(client.get(SOURCE, endpoint, params))

    @mcp.resource("crs://states")
    def crs_states_resource() -> str:
        """CRS states/UTs with two-letter codes (state_name, state_abbr)."""
        return get("/states", {})

    @mcp.resource("crs://tables")
    def crs_tables_resource() -> str:
        """CRS table numbers with descriptions."""
        return get("/tables", {})

    @mcp.tool(annotations=READ_ONLY)
    def crs_list_states() -> str:
        """CRS states/UTs with two-letter codes (state_name, state_abbr). No India row."""
        return get("/states", {})

    @mcp.tool(annotations=READ_ONLY)
    def crs_list_tables() -> str:
        """List the 10 CRS tables: births, deaths, infant deaths, still births,
        registration completeness, deaths by age, and district-level equivalents.
        """
        return get("/tables", {})

    @mcp.tool(annotations=READ_ONLY)
    def crs_available_years(
        table: Optional[str] = None,
        state: Optional[str] = None,
    ) -> str:
        """Available years per CRS table.

        Args:
            table: Table number (1-10), or None for all tables.
            state: Comma-separated state names or two-letter codes to check coverage for.
        """
        return get("/available_years", {"table": table, "state": state})

    @mcp.tool(annotations=READ_ONLY)
    def crs_population_district(
        year: Optional[str] = None,
        state: Optional[str] = None,
        boundary: Literal["lgd", "census2011"] = "lgd",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """District-level population projections.

        LGD boundary: 778 current districts, every year 2012-2031.
        Census 2011 boundary: 634 districts, only 2011, 2016, 2021, 2026, 2031.

        Args:
            year: Comma-separated years or a range, e.g. "2020" or "2015:2023".
            state: Comma-separated state names or two-letter codes, e.g. "Kerala,TN".
                   No India row; None = every state.
            boundary: "lgd" (default) or "census2011".
            limit: Rows per page, 1-10000 (default 1000).
            offset: Rows to skip; pass next_offset from the previous result.
        """
        return get(
            "/population_district",
            {
                "year": year,
                "state": state,
                "boundary": boundary,
                "limit": limit,
                "offset": offset,
            },
        )

    for name, endpoint, summary in _YEAR_STATE_TOOLS:
        tool = _year_state_tool(client, endpoint, summary)
        mcp.tool(tool, name=name, annotations=READ_ONLY)


def _year_state_tool(
    client: "BharatVitalsClient", endpoint: str, summary: str
) -> Callable[..., str]:
    def tool(
        year: Optional[str] = None,
        state: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        return to_json(
            client.get(
                SOURCE,
                endpoint,
                {"year": year, "state": state, "limit": limit, "offset": offset},
            )
        )

    # FastMCP reads Args from the docstring into the parameter schema
    notes = _DISTRICT_NOTE if endpoint.startswith("/district_") else ""
    if endpoint in _COUNT_ROUTES:
        notes += _COLUMNS_NOTE
    state = _INDIA_STATE if endpoint == "/population_state" else _NO_INDIA_STATE
    tool.__doc__ = summary + notes + _YEAR_STATE_ARGS.replace("{state}", state)
    return tool


# routes returning Rural_/Urban_/Total_ x Male/Female/Person count columns
_COUNT_ROUTES = {
    "/births",
    "/deaths",
    "/infant_deaths",
    "/still_births",
    "/deaths_by_age",
    "/district_births",
    "/district_deaths",
    "/district_infant_deaths",
    "/district_still_births",
}
_COLUMNS_NOTE = (
    "\n\nColumns overlap: Total_Person is the all-person count, Total_Male plus "
    "Total_Female make it, and Rural_ plus Urban_ make Total_. Never add columns."
)
_NO_INDIA_STATE = "No India row; None = every state."
_INDIA_STATE = (
    '"India" = national row. Dadra & Nagar Haveli and Daman & Diu appear '
    "both separately and merged, so state rows do not sum to India."
)


_DISTRICT_NOTE = "\n\ndistrict is the harmonised name; district_as_reported is the spelling CRS published."

_YEAR_STATE_ARGS = """

Args:
    year: Comma-separated years or a range, e.g. "2020" or "2015:2023".
    state: Comma-separated state names or two-letter codes, e.g. "Kerala,TN".
           {state}
    limit: Rows per page, 1-10000 (default 1000).
    offset: Rows to skip; pass next_offset from the previous result.
"""

# (tool name, route, description); every route takes year, state, limit, offset
_YEAR_STATE_TOOLS = (
    (
        "crs_vital_rates",
        "/vital_rates",
        (
            "Vital rates from CRS counts and MOHFW population projections.\n"
            "\n"
            "Rates per 1,000:\n"
            "- CBR = registered births / population\n"
            "- CDR = registered deaths / population\n"
            "- IMR = infant deaths / live births\n"
            "- SBR = still births / (births + still births)\n"
            "- SRB = female births per 1,000 male births\n"
            "\n"
            "From registered counts only; use crs_adjusted_events() for\n"
            "completeness-corrected estimates."
        ),
    ),
    (
        "crs_adjusted_events",
        "/adjusted_events",
        (
            "Births/deaths adjusted for registration completeness.\n"
            "\n"
            "Divides registered counts by Table 5 completeness percentages.\n"
            "80,000 births at 80% completeness => 100,000 estimated true births.\n"
            "No rows for 2020-2022, the years Table 5 is missing."
        ),
    ),
    (
        "crs_births",
        "/births",
        "State-level registered births by sex and residence (Table 1, 2009-2023).",
    ),
    (
        "crs_deaths",
        "/deaths",
        "State-level registered deaths by sex and residence (Table 2, 2009-2023).",
    ),
    (
        "crs_infant_deaths",
        "/infant_deaths",
        "State-level registered infant deaths by sex and residence (Table 3, 2009-2023).",
    ),
    (
        "crs_still_births",
        "/still_births",
        "State-level registered still births by sex and residence (Table 4, 2009-2023).",
    ),
    (
        "crs_registration",
        "/registration",
        (
            "Birth and death registration completeness percentages (Table 5).\n"
            "\n"
            "Fraction of estimated births/deaths registered per state and year.\n"
            "No data for 2020-2022."
        ),
    ),
    ("crs_deaths_by_age", "/deaths_by_age", "Deaths by age group and sex (Table 6)."),
    (
        "crs_district_births",
        "/district_births",
        "District-level registered births (Table 7, 700+ districts, 2009-2023).",
    ),
    (
        "crs_district_deaths",
        "/district_deaths",
        "District-level registered deaths (Table 8, 700+ districts, 2009-2023).",
    ),
    (
        "crs_district_infant_deaths",
        "/district_infant_deaths",
        "District-level registered infant deaths (Table 9, 700+ districts, 2009-2023).",
    ),
    (
        "crs_district_still_births",
        "/district_still_births",
        "District-level registered still births (Table 10, 700+ districts, 2010-2023).",
    ),
    (
        "crs_population_state",
        "/population_state",
        (
            "State-level MOHFW population projections (2011-2036).\n"
            "\n"
            "Use with CRS counts to compute crude birth/death rates."
        ),
    ),
)
