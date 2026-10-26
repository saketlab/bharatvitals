from typing import TYPE_CHECKING, Any, Literal, Optional
from urllib.parse import quote

from fastmcp import FastMCP

from bharatvitals.tools._common import READ_ONLY, to_json

if TYPE_CHECKING:
    from bharatvitals.client import BharatVitalsClient

SOURCE = "census"
PACKAGE = "censusindia"
LABEL = "Census of India"
GUIDE = (
    "Use for population and denominators: census counts 1901-2011 by state, "
    "district and subdistrict (literacy, workers, housing, languages, SC/ST) "
    "through census_query (no India row), and projections 2011-2036 through "
    "census_population (India row included). "
    "Start with census_search_variables."
)

# ponytail: no geometry=true; GeoJSON polygons swamp an LLM context


def register(mcp: FastMCP, client: "BharatVitalsClient") -> None:
    def get(endpoint: str, params: dict[str, Any]) -> str:
        return to_json(client.get(SOURCE, endpoint, params))

    @mcp.tool(annotations=READ_ONLY)
    def census_list_states() -> str:
        """States/UTs with census code, two-letter abbreviation, region and harmonised name."""
        return get("/states", {})

    @mcp.tool(annotations=READ_ONLY)
    def census_list_geographies() -> str:
        """Census year x geography combinations available, with the dataset behind each."""
        return get("/geographies", {})

    @mcp.tool(annotations=READ_ONLY)
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
        return get(
            "/variables",
            {"year": year, "geography": geography, "category": category},
        )

    @mcp.tool(annotations=READ_ONLY)
    def census_search_variables(pattern: str) -> str:
        """Find census variables whose name or label matches a keyword or regex.

        Args:
            pattern: e.g. "literacy", "worker", "sex ratio".
        """
        return get("/search", {"pattern": pattern})

    @mcp.tool(annotations=READ_ONLY)
    def census_query(
        year: int = 2011,
        geography: Literal["state", "district", "subdistrict"] = "state",
        state: Optional[str] = None,
        variables: Optional[str] = None,
        sector: Literal["total", "rural", "urban"] = "total",
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
                   No India row; use census_population for national population.
            variables: Comma-separated variable names, e.g. "population,literacy_rate".
                       None = all variables.
            sector: "total", "rural", or "urban". Rural and urban exist only for
                    1971 and 1981; other years reject them.
            limit: Rows per page, 1-10000 (default 1000).
            offset: Rows to skip; pass next_offset from the previous result.
        """
        return get(
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

    @mcp.tool(annotations=READ_ONLY)
    def census_population(
        year: Optional[str] = None,
        geography: Literal["state", "district"] = "state",
        state: Optional[str] = None,
        boundary: Literal["census2011", "lgd"] = "census2011",
        by_age: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """Population projections: males, females and total population.

        State projections cover 2011-2036; district projections 2011-2031
        (Census 2011 boundaries every 5 years, LGD boundaries annually).
        Years between published tables are interpolated and years up to five
        past the last table extrapolated; the estimate column says which.

        Args:
            year: Comma-separated years or a range, e.g. "2026" or "2021:2026".
                  None = all published years.
            geography: "state" or "district".
            state: Comma-separated state names or two-letter codes; "India" = national row.
            boundary: District boundaries: "census2011" or "lgd" (current LGD districts).
            by_age: Age-group rows, absolute counts of persons. District level:
                    single years 0-14, then 5-year bands to 80+. State level:
                    5-year bands for 23 major states, India and a North-East
                    aggregate only; other states are an error.
            limit: Rows per page, 1-10000 (default 1000).
            offset: Rows to skip; pass next_offset from the previous result.
        """
        return get(
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

    @mcp.tool(annotations=READ_ONLY)
    def census_languages(
        level: Literal["district", "subdistrict"] = "district",
        language_group: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """Census 2011 speakers per language, one row per language per area.

        Args:
            level: "district" (default) or "subdistrict".
            language_group: Comma-separated codes from the language_group column.
            limit: Rows per page, 1-10000 (default 1000).
            offset: Rows to skip; pass next_offset from the previous result.
        """
        return get(
            "/languages",
            {
                "level": level,
                "language_group": language_group,
                "limit": limit,
                "offset": offset,
            },
        )

    @mcp.tool(annotations=READ_ONLY)
    def census_sc_st(
        category: Optional[str] = None,
        state: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """Census 2011 Scheduled Caste and Scheduled Tribe populations by district.

        Args:
            category: "SC", "ST", or a full category name. None = both.
            state: Comma-separated state names or two-letter codes. None = every state.
            limit: Rows per page, 1-10000 (default 1000).
            offset: Rows to skip; pass next_offset from the previous result.
        """
        return get(
            "/sc-st",
            {"category": category, "state": state, "limit": limit, "offset": offset},
        )

    @mcp.tool(annotations=READ_ONLY)
    def census_list_datasets() -> str:
        """Whole census tables (e.g. 1931 castes, 2011 tribes) for census_dataset."""
        return get("/datasets", {})

    @mcp.tool(annotations=READ_ONLY)
    def census_dataset(
        name: str,
        state: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """One whole census table by name from census_list_datasets. Counts are persons.

        Args:
            name: Dataset name (the Item column), e.g. "census_1931_castes".
            state: Comma-separated state names or two-letter codes, for tables
                   with a state column.
            limit: Rows per page, 1-10000 (default 1000).
            offset: Rows to skip; pass next_offset from the previous result.
        """
        return get(
            f"/dataset/{quote(name, safe='')}",
            {"state": state, "limit": limit, "offset": offset},
        )
