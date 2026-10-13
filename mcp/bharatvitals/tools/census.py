"""Vendored mcp_forall tools (this module registers them on import)."""

from __future__ import annotations

from bharatvitals.runtime import (
    CONSUMPTION_API_URL,
    CRS_API_URL,
    CENSUS_API_URL,
    HEALTHSURVEY_API_URL,
    HMIS_API_URL,
    MCCD_API_URL,
    SRS_API_URL,
    _request_json,
    _string_params,
    mcp,
)


CENSUS_VALID_YEARS = {
    1901, 1911, 1921, 1931, 1941, 1951,
    1961, 1971, 1981, 1991, 2001, 2011,
}
CENSUS_VALID_GEOGRAPHIES = {"state", "district", "subdistrict"}
CENSUS_VALID_SECTORS = {"total", "rural", "urban"}


def _as_csv(value):
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        items = [str(item).strip() for item in value if str(item).strip()]
        return ",".join(items) if items else None
    text = str(value).strip()
    return text if text else None


@mcp.tool()
def census_list_states() -> dict:
    """List the states available through the Census India API."""
    return _request_json("censusindia", CENSUS_API_URL, "GET", "states")


@mcp.tool()
def census_list_geographies() -> dict:
    """List the Census of India geography levels available through the API."""
    return _request_json("censusindia", CENSUS_API_URL, "GET", "geographies")


@mcp.tool()
def census_list_variables(
    year: int | None = None,
    geography: str | None = None,
    category: str | None = None,
) -> dict:
    """List available Census variables, optionally filtered by year, geography, or category."""
    params: dict[str, str] = {}
    if year is not None:
        params["year"] = str(year)
    if geography:
        params["geography"] = str(geography).strip().lower()
    if category:
        params["category"] = str(category).strip()
    return _request_json("censusindia", CENSUS_API_URL, "GET", "variables", params=params or None)


@mcp.tool()
def census_search_variables(query: str = "") -> dict:
    """Search Census variables by keyword or regex-like pattern."""
    pattern = (query or "").strip()
    params: dict[str, str] = {"pattern": pattern}
    return _request_json("censusindia", CENSUS_API_URL, "GET", "search", params=params)


@mcp.tool()
def census_query(
    year: int = 2011,
    geography: str = "state",
    state: str | None = None,
    variables: list[str] | str | None = None,
    sector: str = "total",
    geometry: bool = False,
) -> dict:
    """Query Census India tables for a specific year, geography, state, and variable set."""
    if year not in CENSUS_VALID_YEARS:
        raise ValueError(f"Unsupported Census year: {year}. Supported values are {sorted(CENSUS_VALID_YEARS)}.")
    geography_key = (geography or "").strip().lower()
    if geography_key not in CENSUS_VALID_GEOGRAPHIES:
        raise ValueError(f"Supported geography values are: {', '.join(sorted(CENSUS_VALID_GEOGRAPHIES))}.")
    sector_key = (sector or "total").strip().lower()
    if sector_key not in CENSUS_VALID_SECTORS:
        raise ValueError(f"Supported sector values are: {', '.join(sorted(CENSUS_VALID_SECTORS))}.")

    params: dict[str, str] = {
        "year": str(year),
        "geography": geography_key,
        "sector": sector_key,
        "geometry": str(bool(geometry)).lower(),
    }
    if state:
        params["state"] = _as_csv(state)
    if variables is not None:
        params["variables"] = _as_csv(variables)
    return _request_json("censusindia", CENSUS_API_URL, "GET", "query", params=params)


@mcp.tool()
def census_population(
    year: int = 2011,
    geography: str = "state",
    state: str | None = None,
    boundary: str = "census2011",
    by_age: bool = False,
    geometry: bool = False,
) -> dict:
    """Query Census India population totals and projections for the selected geography."""
    if year not in CENSUS_VALID_YEARS:
        raise ValueError(f"Unsupported Census year: {year}. Supported values are {sorted(CENSUS_VALID_YEARS)}.")
    geography_key = (geography or "").strip().lower()
    if geography_key not in {"state", "district"}:
        raise ValueError(f"Supported geography values are: state, district.")
    params: dict[str, str] = {
        "year": str(year),
        "geography": geography_key,
        "boundary": str(boundary).strip().lower(),
        "by_age": str(bool(by_age)).lower(),
        "geometry": str(bool(geometry)).lower(),
    }
    if state:
        params["state"] = _as_csv(state)
    return _request_json("censusindia", CENSUS_API_URL, "GET", "population", params=params)


@mcp.tool()
def census_population_projection(
    year: int = 2031,
    geography: str = "state",
    state: str | None = None,
    boundary: str = "census2011",
    by_age: bool = False,
    geometry: bool = False,
) -> dict:
    """Query district or state population projections for Census India data."""
    geography_key = (geography or "").strip().lower()
    if geography_key not in {"state", "district"}:
        raise ValueError("Supported geography values are: state, district.")
    if geography_key == "district" and year > 2031:
        raise ValueError("District-level population projections are available only through 2031.")
    params: dict[str, str] = {
        "year": str(year),
        "geography": geography_key,
        "boundary": str(boundary).strip().lower(),
        "by_age": str(bool(by_age)).lower(),
        "geometry": str(bool(geometry)).lower(),
    }
    if state:
        params["state"] = _as_csv(state)
    return _request_json("censusindia", CENSUS_API_URL, "GET", "population", params=params)


@mcp.tool()
def census_health() -> dict:
    """Health check for the censusindia REST API."""
    return _request_json("censusindia", CENSUS_API_URL, "GET", "health")


