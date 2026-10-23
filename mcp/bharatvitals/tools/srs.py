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


SRS_BULLETIN_INDICATORS = {"cbr", "cdr", "ngr", "imr"}
SRS_STAT_REPORT_INDICATORS = {"tfr", "nmr", "u5mr", "imr", "cdr"}
SRS_CATEGORIES = {"Total", "Rural", "Urban"}


@mcp.tool()
def srs_health() -> dict:
    """Health check for the srsindia REST API."""
    return _request_json("srsindia", SRS_API_URL, "GET", "health")


@mcp.tool()
def srs_list_states() -> dict:
    """List the states and union territories available in the SRS datasets."""
    return _request_json("srsindia", SRS_API_URL, "GET", "states")


@mcp.tool()
def srs_list_life_table_periods() -> dict:
    """List the available SRS life-table periods."""
    return _request_json("srsindia", SRS_API_URL, "GET", "life_table_periods")


@mcp.tool()
def srs_list_cod_periods() -> dict:
    """List the available SRS cause-of-death periods."""
    return _request_json("srsindia", SRS_API_URL, "GET", "cod_periods")


@mcp.tool()
def srs_list_bulletin_years() -> dict:
    """List the years covered by the SRS bulletin."""
    return _request_json("srsindia", SRS_API_URL, "GET", "bulletin_years")


@mcp.tool()
def srs_list_bulletin_indicators() -> dict:
    """List the SRS bulletin indicators available (CBR, CDR, NGR, IMR)."""
    return _request_json("srsindia", SRS_API_URL, "GET", "bulletin_indicators")


@mcp.tool()
def srs_list_stat_report_years() -> dict:
    """List the years covered by the SRS Statistical Report."""
    return _request_json("srsindia", SRS_API_URL, "GET", "stat_report_years")


@mcp.tool()
def srs_list_stat_report_indicators() -> dict:
    """List the SRS Statistical Report indicators available (TFR, NMR, U5MR, etc.)."""
    return _request_json("srsindia", SRS_API_URL, "GET", "stat_report_indicators")


@mcp.tool()
def srs_list_cod_tables() -> dict:
    """List the available SRS cause-of-death tables and metadata."""
    return _request_json("srsindia", SRS_API_URL, "GET", "cod_tables")


@mcp.tool()
def srs_available_periods() -> dict:
    """List the periods available across SRS datasets."""
    return _request_json("srsindia", SRS_API_URL, "GET", "available_periods")


@mcp.tool()
def srs_query_cod(table: str, period: str | None = None) -> dict:
    """Query SRS cause-of-death tables for population-level mortality patterns."""
    if not table or not str(table).strip():
        raise ValueError("table is required for srs_query_cod")
    params: dict[str, str] = {"table": table.strip()}
    if period:
        params["period"] = str(period)
    return _request_json("srsindia", SRS_API_URL, "GET", "cod", params=params)


@mcp.tool()
def srs_query_bulletin(
    indicator: str = "",
    state: str = "",
    year: int | None = None,
    category: str = "",
    limit: int = 10000,
) -> dict:
    """Query SRS vital statistics from the bulletin (CBR, CDR, NGR, IMR)."""
    if indicator and indicator not in SRS_BULLETIN_INDICATORS:
        raise ValueError(
            "indicator must be one of: " + ", ".join(sorted(SRS_BULLETIN_INDICATORS))
        )
    if category and category not in SRS_CATEGORIES:
        raise ValueError("category must be one of: " + ", ".join(sorted(SRS_CATEGORIES)))
    if limit < 0:
        raise ValueError("limit must be >= 0")
    params: dict[str, str] = {"indicator": indicator, "state": state, "category": category, "limit": str(limit)}
    if year is not None:
        params["year"] = str(year)
    return _request_json("srsindia", SRS_API_URL, "GET", "bulletin", params=params)


@mcp.tool()
def srs_query_life_table(
    state: str = "",
    period: str = "",
    category: str = "",
    limit: int = 10000,
) -> dict:
    """Query SRS abridged life-table statistics."""
    if category and category not in SRS_CATEGORIES:
        raise ValueError("category must be one of: " + ", ".join(sorted(SRS_CATEGORIES)))
    if limit < 0:
        raise ValueError("limit must be >= 0")
    params: dict[str, str] = {
        "state": state,
        "period": period,
        "category": category,
        "limit": str(limit),
    }
    return _request_json("srsindia", SRS_API_URL, "GET", "life_table", params=params)


@mcp.tool()
def srs_query_stat_report(
    indicator: str = "",
    state: str = "",
    year: int | None = None,
    category: str = "",
    limit: int = 10000,
) -> dict:
    """Query additional SRS summary indicators such as TFR, NMR, U5MR, IMR, and CDR."""
    if indicator:
        for item in indicator.split(","):
            if item.strip() not in SRS_STAT_REPORT_INDICATORS:
                raise ValueError(
                    "indicator entries must be a comma-separated subset of: "
                    + ", ".join(sorted(SRS_STAT_REPORT_INDICATORS))
                )
    if category and category not in SRS_CATEGORIES:
        raise ValueError("category must be one of: " + ", ".join(sorted(SRS_CATEGORIES)))
    if limit < 0:
        raise ValueError("limit must be >= 0")
    params: dict[str, str] = {
        "indicator": indicator,
        "state": state,
        "category": category,
        "limit": str(limit),
    }
    if year is not None:
        params["year"] = str(year)
    return _request_json("srsindia", SRS_API_URL, "GET", "stat_report", params=params)


@mcp.tool()
def srs_summary_indicators(
    state: str = "",
    period: str = "",
    category: str = "",
    limit: int = 10000,
) -> dict:
    """Return a concise summary of SRS mortality and demographic indicators."""
    if category and category not in SRS_CATEGORIES:
        raise ValueError("category must be one of: " + ", ".join(sorted(SRS_CATEGORIES)))
    if limit < 0:
        raise ValueError("limit must be >= 0")
    params: dict[str, str] = {
        "state": state,
        "period": period,
        "category": category,
        "limit": str(limit),
    }
    return _request_json("srsindia", SRS_API_URL, "GET", "summary_indicators", params=params)


@mcp.tool()
def srs_life_expectancy_trend() -> dict:
    """Return the national SRS life-expectancy trend over time."""
    return _request_json("srsindia", SRS_API_URL, "GET", "life_expectancy_trend")


@mcp.tool()
def srs_epi_transition(period: str = "") -> dict:
    """Return the epidemiological transition profile from SRS cause-of-death data."""
    params: dict[str, str] = {"period": period}
    return _request_json("srsindia", SRS_API_URL, "GET", "epi_transition", params=params)


@mcp.tool()
def srs_arriaga_decompose(
    state: str,
    period1: str,
    period2: str,
    category: str = "Total",
    sex: str = "total",
) -> dict:
    """Decompose the difference in life expectancy between two SRS periods."""
    if not state or not str(state).strip():
        raise ValueError("state is required for srs_arriaga_decompose")
    if not period1 or not str(period1).strip():
        raise ValueError("period1 is required for srs_arriaga_decompose")
    if not period2 or not str(period2).strip():
        raise ValueError("period2 is required for srs_arriaga_decompose")
    if category not in SRS_CATEGORIES:
        raise ValueError("category must be one of: " + ", ".join(sorted(SRS_CATEGORIES)))
    if sex not in {"total", "male", "female"}:
        raise ValueError('sex must be one of "total", "male", or "female"')
    params: dict[str, str] = {
        "state": state,
        "period1": period1,
        "period2": period2,
        "category": category,
        "sex": sex,
    }
    return _request_json("srsindia", SRS_API_URL, "GET", "arriaga", params=params)

