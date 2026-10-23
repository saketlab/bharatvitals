"""Vendored mcp_forall tools (this module registers them on import)."""

from __future__ import annotations

from bharatvitals.runtime import (
    CRS_API_URL,
    CENSUS_API_URL,
    HMIS_API_URL,
    MCCD_API_URL,
    SRS_API_URL,
    _request_json,
    _string_params,
    mcp,
)


MCCD_VALID_TABLES = {
    "deaths", "deaths_pct", "cause", "age", "subcause",
    "state_subcause", "state_age_pct", "trend", "trend_pct",
    "age_pct", "age_over_pct",
}


@mcp.tool()
def query_mccd(
    table: str = "deaths",
    cause: str | None = None,
    state: str | None = None,
    year: str | None = None,
    sex: str | None = None,
) -> dict:
    """Use for cause-of-death analysis: what people died from, ICD-10 codes,
    and epidemiological category breakdowns (Communicable, NCD, External,
    Ill-defined). Data covers medically certified deaths across Indian
    states and years.

    NOT for health system indicators, facility data, or testing coverage —
    use query_hmis.

    Filter by:

    - table: which data table to query. One of: deaths (state-wise death
      counts), deaths_pct (state-wise death percentages), cause (deaths by
      major cause), age (age-disaggregated deaths), subcause (detailed
      sub-cause deaths), state_subcause (state+age disaggregated),
      state_age_pct, trend (multi-year trends), trend_pct, age_pct,
      age_over_pct. Default: "deaths".
    - cause: regex filter on Cause_Of_Death or ICD-10 code, e.g. "I20"
      or "coronary". Applied server-side.
    - state: comma-separated state names, e.g. "Kerala, Tamil Nadu".
    - year: year filter. Accepts "2020", "2015,2016,2017", or "2015:2020".
    - sex: one of "T" (total), "M" (male), "F" (female).

    Returns {"count": ..., "rows": [...]}.

    For health system indicators (facility counts, testing, vaccinations,
    staffing, service coverage), use query_hmis instead.
    """
    if table not in MCCD_VALID_TABLES:
        raise ValueError(
            f"table must be one of: {', '.join(sorted(MCCD_VALID_TABLES))}"
        )
    if sex is not None:
        sex = sex.strip().upper()
        if sex not in ("T", "M", "F"):
            raise ValueError('sex must be one of "T", "M", or "F"')

    params: dict[str, str] = {"table": table}
    if cause:
        params["cause"] = cause
    if state:
        params["state"] = state
    if year:
        params["year"] = year
    if sex:
        params["sex"] = sex

    return _request_json("mccdindia", MCCD_API_URL, "GET", "query", params=params)


MCCD_CAUSE_TABLES = {"cause", "subcause", "state_subcause"}
MCCD_CATEGORIES = {"Communicable", "NCD", "External", "Ill-defined", "Other"}


@mcp.tool()
def mccd_health() -> dict:
    """Health check for the mccdindia REST API."""
    return _request_json("mccdindia", MCCD_API_URL, "GET", "health")


@mcp.tool()
def mccd_list_states() -> dict:
    """List the states available in the MCCD datasets."""
    return _request_json("mccdindia", MCCD_API_URL, "GET", "states")


@mcp.tool()
def mccd_causes(pattern: str = "") -> dict:
    """Search MCCD causes of death by regex against Cause_Of_Death or ICD-10 code.

    Use before query_mccd to find valid cause names or codes (e.g. "I20",
    "coronary", "Septicaemia").
    """
    params: dict[str, str] = {"pattern": pattern}
    return _request_json("mccdindia", MCCD_API_URL, "GET", "causes", params=params)


@mcp.tool()
def mccd_chapters(category: str = "") -> dict:
    """List ICD-10 chapters, optionally filtered by epidemiological category.

    category: Communicable, NCD, External, Ill-defined, or Other.
    """
    if category and category not in MCCD_CATEGORIES:
        raise ValueError(
            "category must be one of: " + ", ".join(sorted(MCCD_CATEGORIES))
        )
    params: dict[str, str] = {"category": category}
    return _request_json("mccdindia", MCCD_API_URL, "GET", "chapters", params=params)


@mcp.tool()
def mccd_categorize(
    table: str = "cause",
    cause: str | None = None,
    state: str | None = None,
    year: str | None = None,
    sex: str | None = None,
) -> dict:
    """Return MCCD deaths classified into epidemiological categories.

    Same filters as query_mccd but result rows are categorized into
    Communicable, NCD, External, Ill-defined. table must be one of
    cause, subcause, state_subcause.
    """
    if table not in MCCD_CAUSE_TABLES:
        raise ValueError(
            f"table for categorize must be one of: {', '.join(sorted(MCCD_CAUSE_TABLES))}"
        )
    if sex is not None:
        sex = sex.strip().upper()
        if sex not in ("T", "M", "F"):
            raise ValueError('sex must be one of "T", "M", or "F"')
    params: dict[str, str] = {"table": table}
    if cause:
        params["cause"] = cause
    if state:
        params["state"] = state
    if year:
        params["year"] = year
    if sex:
        params["sex"] = sex
    return _request_json("mccdindia", MCCD_API_URL, "GET", "categorize", params=params)

