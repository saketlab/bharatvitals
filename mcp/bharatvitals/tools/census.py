import json
from typing import TYPE_CHECKING, Optional

from fastmcp import FastMCP

if TYPE_CHECKING:
    from bharatvitals.client import BharatVitalsClient

SOURCE = "census"
PACKAGE = "censusindia"
LABEL = "Census of India"
GUIDE = (
    "1901-2011 by state/district/subdistrict, plus "
    "population projections to 2036. Start with census_search_variables, then "
    "census_query; use census_population for projections."
)

# ponytail: no geometry=true; GeoJSON polygons swamp an LLM context


def _to_json(data: object) -> str:
    return json.dumps(data)


def register(mcp: FastMCP, client: "BharatVitalsClient") -> None:

    @mcp.tool()
    def census_list_states() -> str:
        """States/UTs with census code, abbreviation, region and harmonised name."""
        return _to_json(client.get(SOURCE, "/states", {}))

    @mcp.tool()
    def census_list_geographies() -> str:
        """Census year x geography combinations available, with the dataset behind each."""
        return _to_json(client.get(SOURCE, "/geographies", {}))

    @mcp.tool()
    def census_list_variables(
        year: Optional[int] = None,
        geography: Optional[str] = None,
        category: Optional[str] = None,
    ) -> str:
        """Census variables with label, years, geographies and category.

        Args:
            year: Census year, e.g. 2011. None = all years.
            geography: "state", "district", or "subdistrict". None = all.
            category: e.g. "literacy", "housing". None = all.
        """
        return _to_json(
            client.get(
                SOURCE,
                "/variables",
                {"year": year, "geography": geography, "category": category},
            )
        )

    @mcp.tool()
    def census_search_variables(pattern: str) -> str:
        """Find census variables whose name or label matches a keyword or regex.

        Args:
            pattern: e.g. "literacy", "worker", "sex ratio".
        """
        return _to_json(client.get(SOURCE, "/search", {"pattern": pattern}))

    @mcp.tool()
    def census_query(
        year: int = 2011,
        geography: str = "state",
        state: Optional[str] = None,
        variables: Optional[str] = None,
        sector: str = "total",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """Census of India counts by year and geography (1901-2011).

        Find variable names with census_search_variables first.

        Args:
            year: 1901, 1911, ..., 2001, or 2011 (decadal census years only).
            geography: "state", "district", or "subdistrict".
                       See census_list_geographies for what each year has.
            state: Comma-separated state names or two-letter codes, e.g. "Kerala,TN".
            variables: Comma-separated variable names, e.g. "population,literacy_rate".
                       None = all variables.
            sector: "total", "rural", or "urban". Only 1971 and 1981 split by
                    sector; other years ignore it and return totals.
            limit: Rows per page, 1-10000 (default 10000).
            offset: Rows to skip, for paging past 10000.
        """
        return _to_json(
            client.get(
                SOURCE,
                "/query",
                {
                    "year": year,
                    "geography": geography,
                    "state": state,
                    "variables": variables,
                    "sector": sector,
                    "limit": limit,
                    "offset": offset,
                },
            )
        )

    @mcp.tool()
    def census_population(
        year: Optional[str] = None,
        geography: str = "state",
        state: Optional[str] = None,
        boundary: str = "census2011",
        by_age: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """Population projections: males, females and total population.

        State projections cover 2011-2036; district projections 2011-2031
        (Census 2011 boundaries every 5 years, LGD boundaries annually).
        Other years are estimated by geometric growth, and years outside those
        ranges are extrapolated; the response does not flag either.

        Args:
            year: Year or comma-separated years, e.g. "2026" or "2021,2026".
                  None = all published years.
            geography: "state" or "district".
            state: Comma-separated state names or two-letter codes.
            boundary: District boundaries: "census2011" or "lgd" (current LGD districts).
            by_age: Age-group rows. District level: single years 0-14, then
                    5-year bands to 80+, absolute counts. State level: 5-year
                    bands, values IN THOUSANDS, only 23 major states, India and
                    a North-East aggregate (other states return no rows).
            limit: Rows per page, 1-10000 (default 10000).
            offset: Rows to skip, for paging past 10000.
        """
        return _to_json(
            client.get(
                SOURCE,
                "/population",
                {
                    "year": year,
                    "geography": geography,
                    "state": state,
                    "boundary": boundary,
                    "by_age": by_age,
                    "limit": limit,
                    "offset": offset,
                },
            )
        )
