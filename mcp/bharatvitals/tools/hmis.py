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


@mcp.tool()
def query_hmis(
    indicator: str,
    geography: str = "state",
    state: str | None = None,
    district: str | None = None,
    sector: str | None = None,
    category: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    match: str = "fixed",
    backend: str = "auto",
    limit: int = 10000,
) -> dict:
    """Use for health system indicators: facility counts, bed availability,
    staffing, testing coverage, vaccinations, service delivery metrics, and
    monthly time series of HMIS indicators at state or district level.

    NOT for cause-of-death analysis or ICD-10 codes — use query_mccd.

    Provide an indicator search string (e.g. "Neonatal Deaths due to
    Asphyxia") and optionally restrict it by geography and time:

    - geography: "state" (default) or "district".
    - state: comma-separated state names (for state geography).
    - district: comma-separated district names (for district geography).
    - sector: comma-separated values from Total, Public, Private, Rural, Urban.
    - category: sub-category filter.
    - from_date / to_date: month range in "Mon YYYY" format, e.g. "Apr 2023".
    - match: fixed, regex, or fuzzy matching of the indicator string.
    - backend: auto, arrow, or duckdb query backend.
    - limit: maximum rows to return (0 means unlimited).

    Multiple values for state/district/sector must be comma-separated, matching
    the underlying REST API. Returns the API response as {"count": ..., "rows": [...]}.

    For cause-of-death mortality data, ICD-10 codes, or epidemiological
    category breakdowns (Communicable/NCD/External), use query_mccd instead.
    """
    indicator = (indicator or "").strip()
    if not indicator:
        raise ValueError("indicator must be a non-empty string")

    if geography not in ("state", "district"):
        raise ValueError('geography must be either "state" or "district"')
    if match not in ("fixed", "regex", "fuzzy"):
        raise ValueError('match must be one of "fixed", "regex", "fuzzy"')
    if backend not in ("auto", "arrow", "duckdb"):
        raise ValueError('backend must be one of "auto", "arrow", "duckdb"')
    if limit < 0:
        raise ValueError("limit must be >= 0")

    params: dict[str, str] = {
        "indicator": indicator,
        "geography": geography,
        "match": match,
        "backend": backend,
        "limit": str(limit),
    }
    if geography == "state" and state:
        params["state"] = state
    if geography == "district" and district:
        params["district"] = district
    if sector:
        params["sector"] = sector
    if category:
        params["category"] = category
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date

    return _request_json("hmisindia", HMIS_API_URL, "GET", "query", params=params)


@mcp.tool()
def hmis_health() -> dict:
    """Health check for the hmisindia REST API."""
    return _request_json("hmisindia", HMIS_API_URL, "GET", "health")


@mcp.tool()
def hmis_list_states() -> list[str]:
    """List the states and union territories in the HMIS datasets."""
    return _request_json("hmisindia", HMIS_API_URL, "GET", "states")


@mcp.tool()
def hmis_list_districts(state: str | None = None) -> dict:
    """List HMIS districts, optionally filtered by comma-separated state names."""
    params: dict[str, str] | None = None
    if state:
        params = {"state": state}
    return _request_json("hmisindia", HMIS_API_URL, "GET", "districts", params=params)


@mcp.tool()
def hmis_list_indicators(
    pattern: str | None = None,
    geography: str = "state",
    match: str = "fixed",
    min_months: int | None = None,
) -> dict:
    """Search available HMIS indicator names.

    - pattern: search string; match: fixed, regex, or fuzzy.
    - geography: "state" or "district".
    - min_months: minimum months of data coverage.
    """
    if geography not in ("state", "district"):
        raise ValueError('geography must be either "state" or "district"')
    if match not in ("fixed", "regex", "fuzzy"):
        raise ValueError('match must be one of "fixed", "regex", "fuzzy"')
    params: dict[str, str] = {"geography": geography, "match": match}
    if pattern:
        params["pattern"] = pattern
    if min_months is not None:
        params["min_months"] = str(min_months)
    return _request_json("hmisindia", HMIS_API_URL, "GET", "indicators", params=params)


@mcp.tool()
def hmis_periodicity(
    indicator: str,
    state: str | None = None,
    category: str | None = None,
    sector: str | None = None,
    method: str = "pgram",
    detrend: bool = True,
) -> dict:
    """Detect periodicity/seasonality in an HMIS indicator time series.

    Use after query_hmis to test whether a monthly series (e.g. malaria
    cases) has a seasonal pattern. method: "pgram" or "lomb_scargle".
    Provide a single state name for best results.
    """
    if not indicator or not indicator.strip():
        raise ValueError("indicator must be a non-empty string")
    if method not in ("pgram", "lomb_scargle"):
        raise ValueError('method must be one of "pgram" or "lomb_scargle"')
    params: dict[str, str] = {
        "indicator": indicator.strip(),
        "method": method,
        "detrend": "TRUE" if detrend else "FALSE",
    }
    if state:
        params["state"] = state
    if category:
        params["category"] = category
    if sector:
        params["sector"] = sector
    return _request_json("hmisindia", HMIS_API_URL, "GET", "periodicity", params=params)


@mcp.tool()
def hmis_decompose(
    indicator: str,
    state: str | None = None,
    category: str | None = None,
    sector: str | None = None,
    frequency: int = 12,
    s_window: str = "periodic",
) -> dict:
    """Decompose an HMIS indicator monthly series into trend, seasonal, remainder.

    Provide a single state name for best results. frequency: seasonal
    months (default 12); s_window: "periodic" or an odd integer string.
    """
    if not indicator or not indicator.strip():
        raise ValueError("indicator must be a non-empty string")
    if frequency < 2:
        raise ValueError("frequency must be >= 2")
    params: dict[str, str] = {
        "indicator": indicator.strip(),
        "frequency": str(frequency),
        "s_window": str(s_window),
    }
    if state:
        params["state"] = state
    if category:
        params["category"] = category
    if sector:
        params["sector"] = sector
    return _request_json("hmisindia", HMIS_API_URL, "GET", "decompose", params=params)


