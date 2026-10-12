import json
from typing import TYPE_CHECKING, Optional

from fastmcp import FastMCP

if TYPE_CHECKING:
    from bharatvitals.client import BharatVitalsClient

SOURCE = "crs"
PACKAGE = "crsindia"
LABEL = "CRS"
GUIDE = (
    "Registered births, deaths, infant deaths, still births, 36 states, "
    "700+ districts, 2009-2023. Start with crs_list_tables or "
    "crs_vital_rates."
)


def _to_json(data: object) -> str:
    return json.dumps(data)


def register(mcp: FastMCP, client: "BharatVitalsClient") -> None:

    @mcp.resource("crs://states")
    def crs_states_resource() -> str:
        """All 36 canonical state/UT names in CRS data."""
        return _to_json(client.get(SOURCE, "/states", {}))

    @mcp.resource("crs://tables")
    def crs_tables_resource() -> str:
        """CRS table numbers with descriptions."""
        return _to_json(client.get(SOURCE, "/tables", {}))

    @mcp.tool()
    def crs_list_states() -> str:
        """List all 36 canonical state/UT names in CRS data."""
        return _to_json(client.get(SOURCE, "/states", {}))

    @mcp.tool()
    def crs_list_tables() -> str:
        """List the 10 CRS tables: births, deaths, infant deaths, still births,
        registration completeness, deaths by age, and district-level equivalents.
        """
        return _to_json(client.get(SOURCE, "/tables", {}))

    @mcp.tool()
    def crs_available_years(
        table: Optional[str] = None,
        state: Optional[str] = None,
    ) -> str:
        """Available years per CRS table.

        Args:
            table: Table number (1-10), or None for all tables.
            state: State name to check coverage for.
        """
        return _to_json(
            client.get(SOURCE, "/available_years", {"table": table, "state": state})
        )

    @mcp.tool()
    def crs_vital_rates(
        year: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 10000,
    ) -> str:
        """Vital rates from CRS counts and MOHFW population projections.

        Rates per 1,000:
        - CBR = registered births / population
        - CDR = registered deaths / population
        - IMR = infant deaths / live births
        - SBR = still births / (births + still births)
        - SRB = female births / male births

        From registered counts only; use crs_adjusted_events() for
        completeness-corrected estimates.

        Args:
            year: Comma-separated years or range, e.g. "2020" or "2015:2023".
            state: Comma-separated state names.
            limit: Max rows (default 10000, 0 = unlimited).
        """
        return _to_json(
            client.get(
                SOURCE,
                "/vital_rates",
                {"year": year, "state": state, "limit": limit},
            )
        )

    @mcp.tool()
    def crs_adjusted_events(
        year: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 10000,
    ) -> str:
        """Births/deaths adjusted for registration completeness.

        Divides registered counts by Table 5 completeness percentages.
        80,000 births at 80% completeness => 100,000 estimated true births.

        Args:
            year: Comma-separated years or range.
            state: Comma-separated state names.
            limit: Max rows (default 10000, 0 = unlimited).
        """
        return _to_json(
            client.get(
                SOURCE,
                "/adjusted_events",
                {"year": year, "state": state, "limit": limit},
            )
        )

    @mcp.tool()
    def crs_births(
        year: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 10000,
    ) -> str:
        """State-level registered births by sex and residence (Table 1, 2009-2023).

        Args:
            year: Comma-separated years or range, e.g. "2020" or "2018:2023".
            state: Comma-separated state names, e.g. "Kerala,Tamil Nadu".
            limit: Max rows (default 10000, 0 = unlimited).
        """
        return _to_json(
            client.get(
                SOURCE, "/births", {"year": year, "state": state, "limit": limit}
            )
        )

    @mcp.tool()
    def crs_deaths(
        year: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 10000,
    ) -> str:
        """State-level registered deaths by sex and residence (Table 2, 2009-2023).

        Args:
            year: Comma-separated years or range.
            state: Comma-separated state names.
            limit: Max rows (default 10000, 0 = unlimited).
        """
        return _to_json(
            client.get(
                SOURCE, "/deaths", {"year": year, "state": state, "limit": limit}
            )
        )

    @mcp.tool()
    def crs_infant_deaths(
        year: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 10000,
    ) -> str:
        """State-level registered infant deaths by sex and residence (Table 3, 2009-2023).

        Args:
            year: Comma-separated years or range.
            state: Comma-separated state names.
            limit: Max rows (default 10000, 0 = unlimited).
        """
        return _to_json(
            client.get(
                SOURCE,
                "/infant_deaths",
                {"year": year, "state": state, "limit": limit},
            )
        )

    @mcp.tool()
    def crs_still_births(
        year: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 10000,
    ) -> str:
        """State-level registered still births by sex and residence (Table 4, 2009-2023).

        Args:
            year: Comma-separated years or range.
            state: Comma-separated state names.
            limit: Max rows (default 10000, 0 = unlimited).
        """
        return _to_json(
            client.get(
                SOURCE,
                "/still_births",
                {"year": year, "state": state, "limit": limit},
            )
        )

    @mcp.tool()
    def crs_registration(
        year: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 10000,
    ) -> str:
        """Birth and death registration completeness percentages (Table 5).

        Fraction of estimated births/deaths registered per state and year.

        Args:
            year: Comma-separated years or range.
            state: Comma-separated state names.
            limit: Max rows (default 10000, 0 = unlimited).
        """
        return _to_json(
            client.get(
                SOURCE,
                "/registration",
                {"year": year, "state": state, "limit": limit},
            )
        )

    @mcp.tool()
    def crs_deaths_by_age(
        year: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 10000,
    ) -> str:
        """Deaths by age group and sex (Table 6).

        Args:
            year: Comma-separated years or range.
            state: Comma-separated state names.
            limit: Max rows (default 10000, 0 = unlimited).
        """
        return _to_json(
            client.get(
                SOURCE,
                "/deaths_by_age",
                {"year": year, "state": state, "limit": limit},
            )
        )

    @mcp.tool()
    def crs_district_births(
        year: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 10000,
    ) -> str:
        """District-level registered births (Table 7, 700+ districts, 2009-2023).

        Args:
            year: Comma-separated years or range.
            state: Comma-separated state names to filter districts.
            limit: Max rows (default 10000, 0 = unlimited).
        """
        return _to_json(
            client.get(
                SOURCE,
                "/district_births",
                {"year": year, "state": state, "limit": limit},
            )
        )

    @mcp.tool()
    def crs_district_deaths(
        year: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 10000,
    ) -> str:
        """District-level registered deaths (Table 8, 700+ districts, 2009-2023).

        Args:
            year: Comma-separated years or range.
            state: Comma-separated state names.
            limit: Max rows (default 10000, 0 = unlimited).
        """
        return _to_json(
            client.get(
                SOURCE,
                "/district_deaths",
                {"year": year, "state": state, "limit": limit},
            )
        )

    @mcp.tool()
    def crs_district_infant_deaths(
        year: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 10000,
    ) -> str:
        """District-level registered infant deaths (Table 9, 700+ districts, 2009-2023).

        Args:
            year: Comma-separated years or range.
            state: Comma-separated state names.
            limit: Max rows (default 10000, 0 = unlimited).
        """
        return _to_json(
            client.get(
                SOURCE,
                "/district_infant_deaths",
                {"year": year, "state": state, "limit": limit},
            )
        )

    @mcp.tool()
    def crs_district_still_births(
        year: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 10000,
    ) -> str:
        """District-level registered still births (Table 10, 700+ districts, 2010-2023).

        Args:
            year: Comma-separated years or range.
            state: Comma-separated state names.
            limit: Max rows (default 10000, 0 = unlimited).
        """
        return _to_json(
            client.get(
                SOURCE,
                "/district_still_births",
                {"year": year, "state": state, "limit": limit},
            )
        )

    @mcp.tool()
    def crs_population_state(
        year: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 10000,
    ) -> str:
        """State-level MOHFW population projections (2011-2036).

        Use with CRS counts to compute crude birth/death rates.

        Args:
            year: Comma-separated years or range.
            state: Comma-separated state names.
            limit: Max rows (default 10000, 0 = unlimited).
        """
        return _to_json(
            client.get(
                SOURCE,
                "/population_state",
                {"year": year, "state": state, "limit": limit},
            )
        )

    @mcp.tool()
    def crs_population_district(
        year: Optional[str] = None,
        state: Optional[str] = None,
        boundary: str = "lgd",
        limit: int = 10000,
    ) -> str:
        """District-level population projections.

        LGD boundary: 785 districts, 2012-2031.
        Census 2011 boundary: 640 districts, 5-year intervals.

        Args:
            year: Comma-separated years or range.
            state: Comma-separated state names.
            boundary: "lgd" (default, 785 districts) or "census2011" (640 districts).
            limit: Max rows (default 10000, 0 = unlimited).
        """
        return _to_json(
            client.get(
                SOURCE,
                "/population_district",
                {"year": year, "state": state, "boundary": boundary, "limit": limit},
            )
        )
