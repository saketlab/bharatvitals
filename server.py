"""Thin MCP wrapper around India's health, mortality, and survey REST APIs.

Exposes 43 MCP tools, one thin proxy per backend endpoint:
- HMIS (health system indicators, facilities, testing, vaccinations):
  query_hmis plus discovery (hmis_list_indicators, hmis_list_states,
  hmis_list_districts) and time-series analysis (hmis_periodicity,
  hmis_decompose).
- MCCD (medically certified cause-of-death, ICD-10): query_mccd plus
  mccd_causes, mccd_chapters, mccd_categorize, mccd_list_states.
- Census of India: census_query, census_population,
  census_population_projection and discovery tools.
- SRS (population-level mortality, life tables, vital statistics):
  srs_query_* plus discovery and analysis tools.
- Surveys: query_consumption, query_healthsurvey (analytics + read-only SQL).
- Meta: api_health (probe all backends), tool_guide (routing guide).

Forwards requests to already-running Plumber APIs over HTTP. Does not
reimplement any data logic and never touches any database directly.
"""

from __future__ import annotations

import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load .env from the directory containing this script, not the process CWD,
# so the server behaves the same regardless of how the MCP client starts it.
load_dotenv(Path(__file__).resolve().with_name(".env"))

# Base URL of the running hmisindia REST API.
# Override by setting the HMIS_API_URL environment variable.
HMIS_API_URL = os.environ.get("HMIS_API_URL", "http://127.0.0.1:8765")

# Base URL of the running mccdindia REST API.
# Override by setting the MCCD_API_URL environment variable.
MCCD_API_URL = os.environ.get("MCCD_API_URL", "http://127.0.0.1:8585")

# Base URLs of the survey APIs.
CONSUMPTION_API_URL = os.environ.get(
    "CONSUMPTION_API_URL", "http://127.0.0.1:8795"
)
HEALTHSURVEY_API_URL = os.environ.get(
    "HEALTHSURVEY_API_URL", "http://127.0.0.1:8685"
)

# Base URL of the running srsindia REST API.
# Override by setting the SRS_API_URL environment variable.
SRS_API_URL = os.environ.get("SRS_API_URL", "http://127.0.0.1:8686")

# Base URL of the running censusindia REST API.
# Override by setting the CENSUS_API_URL environment variable.
CENSUS_API_URL = os.environ.get("CENSUS_API_URL", "http://127.0.0.1:8895")

REQUEST_TIMEOUT_SECONDS = 30

mcp = FastMCP("India Health MCP")


def _request_json(api_name: str, base_url: str, method: str, path: str,
                  *, params: dict | None = None, json: dict | None = None) -> dict:
    """Call a Plumber route and return its JSON response unchanged."""
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    request = requests.get if method == "GET" else requests.post
    try:
        response = request(
            url,
            params=params,
            json=json,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.exceptions.RequestException as exc:
        raise ValueError(
            f"{api_name} API unavailable: could not reach {url} ({exc}). "
            f"Make sure the {api_name} REST API is running and its URL is correct."
        ) from exc

    if response.status_code != 200:
        raise ValueError(
            f"{api_name} API returned HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError(
            f"{api_name} API returned invalid JSON: {response.text[:500]}"
        ) from exc
    return payload if isinstance(payload, dict) else {"count": len(payload), "rows": payload}


def _string_params(params: dict | None) -> dict[str, str] | None:
    return {key: str(value) for key, value in (params or {}).items() if value is not None}


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


CONSUMPTION_OPERATIONS = {
    "health": ("GET", "health"),
    "overview": ("GET", "overview"),
    "items_search": ("GET", "items/search"),
    "items_catalogue": ("GET", "items/catalogue"),
    "food_group_shares": ("GET", "shares/food-group"),
    "state_consumption": ("GET", "state/consumption"),
    "item_trends": ("GET", "item/trends"),
    "sql": ("POST", "sql"),
}


@mcp.tool()
def query_consumption(
    operation: str = "overview",
    params: dict | None = None,
    sql: str | None = None,
    max_rows: int = 10000,
) -> dict:
    """Query household consumption expenditure survey data.

    IMPORTANT: Do NOT read or search the R package source files to answer a
    question. Just call this tool. For any question that is not a plain fit
    for overview, state_consumption, or food_group_shares, use
    operation="sql" with a direct SELECT. The table is `consumption`
    (columns: nss_round, round_year, era, state, district, sector, hhid,
    item_code, quantity, value, weight, food_group). Example:
    query_consumption(operation="sql", sql="SELECT SUM(value*weight) AS total
    FROM consumption WHERE nss_round = 'HCES-2022-23' AND value > 0").

    Available operations: health, overview, items_search, items_catalogue,
    food_group_shares, state_consumption, item_trends, and sql. Use params
    for an operation's filters (keyword, item, by, round, era, food_group,
    limit). The sql operation takes a read-only SELECT/WITH statement in
    `sql` plus `max_rows`. Returns the native API response envelope.

    Note: the HCES item catalogue ships with the consumptionsurveyindia
    package and is loaded by the API, so official item names and food
    groups resolve for the HCES rounds (2022-23/2023-24) as well as the
    57th-62nd rounds.
    """
    if operation not in CONSUMPTION_OPERATIONS:
        raise ValueError(
            f"operation must be one of: {', '.join(CONSUMPTION_OPERATIONS)}"
        )
    params = params or {}
    if operation == "items_search" and not str(params.get("keyword", "")).strip():
        raise ValueError("params.keyword must be non-empty for items_search")
    if operation == "item_trends" and not str(params.get("item", "")).strip():
        raise ValueError("params.item must be non-empty for item_trends")
    if operation in ("food_group_shares", "state_consumption", "item_trends"):
        by = params.get("by")
        if operation != "state_consumption" and by not in (None, "round", "state", "sector"):
            raise ValueError('params.by must be one of "round", "state", or "sector"')
    if operation == "sql":
        if not sql or not sql.strip():
            raise ValueError("sql must be a non-empty SELECT or WITH statement")
        if max_rows < 0:
            raise ValueError("max_rows must be >= 0")
        return _request_json(
            "consumption survey", CONSUMPTION_API_URL, "POST", "sql",
            json={"query": sql, "max_rows": max_rows},
        )
    method, path = CONSUMPTION_OPERATIONS[operation]
    return _request_json(
        "consumption survey", CONSUMPTION_API_URL, method, path,
        params=_string_params(params),
    )


HEALTHSURVEY_OPERATIONS = {
    "health": ("GET", "health"),
    "overview": ("GET", "overview"),
    "diseases": ("GET", "diseases"),
    "disease_lookup": ("GET", "diseases/lookup"),
    "disease_query": ("GET", "query/disease"),
    "state_query": ("GET", "query/state"),
    "disease_trend": ("GET", "query/disease/trend"),
    "state_summary": ("GET", "state/summary"),
    "variables_search": ("GET", "variables/search"),
    "sql": ("POST", "sql"),
}


@mcp.tool()
def query_healthsurvey(
    operation: str = "overview",
    params: dict | None = None,
    sql: str | None = None,
    max_rows: int = 10000,
) -> dict:
    """Query NSS health survey hospitalization and outpatient data.

    IMPORTANT: Do NOT read or search the R package source files to answer a
    question. Just call this tool. For any question not a plain fit for
    overview, diseases, disease_query, or state_query, use operation="sql"
    with a direct SELECT. Tables are `hospitalization` and `outpatient`.

    Available operations: health, overview, diseases, disease_lookup,
    disease_query, state_query, disease_trend, state_summary,
    variables_search, and sql. Use params for table, round, disease, query,
    keyword, by, and min_obs filters. The sql operation takes a read-only
    SELECT/WITH statement in `sql` plus `max_rows`. Returns the native API
    response envelope.
    """
    if operation not in HEALTHSURVEY_OPERATIONS:
        raise ValueError(
            f"operation must be one of: {', '.join(HEALTHSURVEY_OPERATIONS)}"
        )
    params = params or {}
    if operation in ("diseases", "disease_query", "state_query", "disease_trend"):
        table = params.get("table")
        if table is not None and table not in ("hospitalization", "outpatient"):
            raise ValueError('params.table must be "hospitalization" or "outpatient"')
    if operation == "disease_lookup" and not str(params.get("query", "")).strip():
        raise ValueError("params.query must be non-empty for disease_lookup")
    if operation == "disease_query" and not str(params.get("disease", "")).strip():
        raise ValueError("params.disease must be non-empty for disease_query")
    if operation == "variables_search" and not str(params.get("keyword", "")).strip():
        raise ValueError("params.keyword must be non-empty for variables_search")
    if operation == "disease_query" and params.get("by") not in (None, "round", "state", "sector"):
        raise ValueError('params.by must be one of "round", "state", or "sector"')
    if operation == "sql":
        if not sql or not sql.strip():
            raise ValueError("sql must be a non-empty SELECT or WITH statement")
        if max_rows < 0:
            raise ValueError("max_rows must be >= 0")
        return _request_json(
            "health survey", HEALTHSURVEY_API_URL, "POST", "sql",
            json={"query": sql, "max_rows": max_rows},
        )
    method, path = HEALTHSURVEY_OPERATIONS[operation]
    return _request_json(
        "health survey", HEALTHSURVEY_API_URL, method, path,
        params=_string_params(params),
    )


BACKENDS = [
    ("hmisindia", HMIS_API_URL),
    ("mccdindia", MCCD_API_URL),
    ("censusindia", CENSUS_API_URL),
    ("srsindia", SRS_API_URL),
    ("consumptionsurveyindia", CONSUMPTION_API_URL),
    ("healthsurveyindia", HEALTHSURVEY_API_URL),
]


@mcp.tool()
def api_health() -> dict:
    """Probe the /health endpoint of every backend REST API.

    Returns one entry per backend with status, package, and version when the
    API is reachable, or an error message when it is not. Call this first if
    a data tool reports that an API is unavailable.
    """
    results: dict[str, dict] = {}
    for name, url in BACKENDS:
        try:
            results[name] = _request_json(name, url, "GET", "health")
        except ValueError as exc:
            results[name] = {"error": str(exc)}
    return results


TOOL_REGISTRY: dict[str, dict] = {
    "query_hmis": {
        "purpose": "Health system indicators",
        "use_for": [
            "Facility counts, beds, staffing",
            "Testing and vaccination coverage",
            "Service delivery metrics",
            "Monthly time series of indicators",
            "State and district level health data",
        ],
        "not_for": "Cause-of-death analysis, ICD-10 codes",
        "api": "hmisindia /query",
        "params": "indicator, geography, state, district, sector, from_date, to_date",
    },
    "hmis_list_indicators": {
        "purpose": "Search valid HMIS indicator names",
        "use_for": [
            "Finding the exact indicator string before calling query_hmis",
            "Browsing the ~840 HMIS indicators by keyword, geography, or coverage",
        ],
        "api": "hmisindia /indicators",
        "params": "pattern, geography, match, min_months",
    },
    "hmis_list_states": {
        "purpose": "List HMIS states and union territories",
        "api": "hmisindia /states",
        "params": "none",
    },
    "hmis_list_districts": {
        "purpose": "List HMIS districts, optionally by state",
        "api": "hmisindia /districts",
        "params": "state",
    },
    "hmis_periodicity": {
        "purpose": "Detect seasonality in an HMIS indicator series",
        "use_for": ["Is there a seasonal pattern in this indicator, e.g. malaria cases?"],
        "api": "hmisindia /periodicity",
        "params": "indicator, state, category, sector, method, detrend",
    },
    "hmis_decompose": {
        "purpose": "Decompose an HMIS monthly series into trend/seasonal/remainder",
        "api": "hmisindia /decompose",
        "params": "indicator, state, category, sector, frequency, s_window",
    },
    "hmis_health": {"purpose": "Health check for the hmisindia API", "api": "hmisindia /health", "params": "none"},
    "query_mccd": {
        "purpose": "Medically certified cause-of-death data",
        "use_for": [
            "What people died from (cause of death)",
            "ICD-10 codes and disease categories",
            "Communicable vs NCD vs External cause breakdown",
            "Yearly mortality trends by cause",
            "State-level death counts by cause",
        ],
        "not_for": "Health system indicators, facility data, testing",
        "api": "mccdindia /query",
        "params": "table, cause, state, year, sex",
    },
    "mccd_causes": {
        "purpose": "Search MCCD causes by name or ICD-10 code",
        "use_for": ["Finding valid cause strings/codes to pass to query_mccd"],
        "api": "mccdindia /causes",
        "params": "pattern",
    },
    "mccd_chapters": {
        "purpose": "List ICD-10 chapters, optionally by category",
        "api": "mccdindia /chapters",
        "params": "category",
    },
    "mccd_categorize": {
        "purpose": "MCCD deaths classified into Communicable/NCD/External/Ill-defined",
        "api": "mccdindia /categorize",
        "params": "table, cause, state, year, sex",
    },
    "mccd_list_states": {
        "purpose": "List the states available in the MCCD datasets",
        "api": "mccdindia /states",
        "params": "none",
    },
    "mccd_health": {"purpose": "Health check for the mccdindia API", "api": "mccdindia /health", "params": "none"},
    "census_query": {
        "purpose": "Census of India population and demographic variables",
        "use_for": [
            "Population totals and rates by state, district, subdistrict",
            "Variables like literacy, sex ratio, workers, religion",
            "Census 1901-2011 (sector filter for 1971/1981)",
        ],
        "not_for": "Census population projections or shapefiles",
        "api": "censusindia /query",
        "params": "year, geography, state, variables, sector, geometry",
    },
    "census_population": {
        "purpose": "Census population totals with optional projections and geometry",
        "api": "censusindia /population",
        "params": "year, geography, state, boundary, by_age, geometry",
    },
    "census_population_projection": {
        "purpose": "District/state population projections (through 2031)",
        "api": "censusindia /population",
        "params": "year, geography, state, boundary, by_age, geometry",
    },
    "census_list_states": {
        "purpose": "List states available through the censusindia API",
        "api": "censusindia /states",
        "params": "none",
    },
    "census_list_geographies": {
        "purpose": "List census geography levels (state, district, subdistrict)",
        "api": "censusindia /geographies",
        "params": "none",
    },
    "census_list_variables": {
        "purpose": "List census variables, optionally filtered by year/geography/category",
        "api": "censusindia /variables",
        "params": "year, geography, category",
    },
    "census_search_variables": {
        "purpose": "Search census variables by keyword or regex pattern",
        "api": "censusindia /search",
        "params": "query",
    },
    "census_health": {"purpose": "Health check for the censusindia API", "api": "censusindia /health", "params": "none"},
    "srs_query_life_table": {
        "purpose": "SRS abridged life-table statistics",
        "use_for": [
            "Life expectancy and survival probabilities",
            "Age-specific mortality and longevity patterns",
            "State and period comparisons for life tables",
        ],
        "not_for": "Cause-specific mortality or clinical deaths",
        "api": "srsindia /life_table",
        "params": "state, period, category, limit",
    },
    "srs_query_cod": {
        "purpose": "Population-level SRS cause-of-death data",
        "use_for": [
            "SRS mortality by cause",
            "Population-level cause patterns over time",
            "State, zone, or national SRS mortality comparisons",
        ],
        "not_for": "Medically certified deaths or facility counts",
        "api": "srsindia /cod",
        "params": "table, period",
    },
    "srs_query_bulletin": {
        "purpose": "SRS vital statistics (CBR, CDR, NGR, IMR) from the bulletin",
        "api": "srsindia /bulletin",
        "params": "indicator, state, year, category, limit",
    },
    "srs_query_stat_report": {
        "purpose": "SRS Statistical Report indicators (TFR, NMR, U5MR, IMR, CDR)",
        "api": "srsindia /stat_report",
        "params": "indicator, state, year, category, limit",
    },
    "srs_summary_indicators": {
        "purpose": "Concise SRS mortality and demographic indicators",
        "api": "srsindia /summary_indicators",
        "params": "state, period, category, limit",
    },
    "srs_list_states": {
        "purpose": "List SRS states and union territories",
        "api": "srsindia /states",
        "params": "none",
    },
    "srs_list_life_table_periods": {
        "purpose": "List available SRS life-table periods",
        "api": "srsindia /life_table_periods",
        "params": "none",
    },
    "srs_list_cod_tables": {
        "purpose": "List SRS cause-of-death table slugs with metadata",
        "api": "srsindia /cod_tables",
        "params": "none",
    },
    "srs_list_cod_periods": {
        "purpose": "List available SRS cause-of-death periods",
        "api": "srsindia /cod_periods",
        "params": "none",
    },
    "srs_list_bulletin_years": {
        "purpose": "List years covered by the SRS bulletin",
        "api": "srsindia /bulletin_years",
        "params": "none",
    },
    "srs_list_bulletin_indicators": {
        "purpose": "List SRS bulletin indicators",
        "api": "srsindia /bulletin_indicators",
        "params": "none",
    },
    "srs_list_stat_report_years": {
        "purpose": "List years covered by the SRS Statistical Report",
        "api": "srsindia /stat_report_years",
        "params": "none",
    },
    "srs_list_stat_report_indicators": {
        "purpose": "List SRS Statistical Report indicators",
        "api": "srsindia /stat_report_indicators",
        "params": "none",
    },
    "srs_available_periods": {
        "purpose": "List periods available across SRS datasets",
        "api": "srsindia /available_periods",
        "params": "none",
    },
    "srs_life_expectancy_trend": {
        "purpose": "National SRS life-expectancy trend over time",
        "api": "srsindia /life_expectancy_trend",
        "params": "none",
    },
    "srs_epi_transition": {
        "purpose": "Epidemiological transition profile from SRS cause-of-death data",
        "api": "srsindia /epi_transition",
        "params": "period",
    },
    "srs_arriaga_decompose": {
        "purpose": "Decompose life-expectancy difference between two SRS periods",
        "api": "srsindia /arriaga",
        "params": "state, period1, period2, category, sex",
    },
    "srs_health": {"purpose": "Health check for the srsindia API", "api": "srsindia /health", "params": "none"},
    "query_consumption": {
        "purpose": "Household consumption expenditure survey analytics",
        "use_for": [
            "Food and non-food spending",
            "Item search and catalogue coverage",
            "Food-group shares by round, state, or sector",
            "State consumption comparisons",
            "Item trends across survey rounds",
        ],
        "api": "consumptionsurveyindia REST API",
        "params": "operation, params, sql, max_rows",
    },
    "query_healthsurvey": {
        "purpose": "NSS health survey hospitalization and outpatient analytics",
        "use_for": [
            "Disease categories and disease lookup",
            "Hospitalization and outpatient expenditure",
            "State and sector comparisons",
            "Health survey trends and summaries",
            "Survey variable label search",
        ],
        "api": "healthsurveyindia REST API",
        "params": "operation, params, sql, max_rows",
    },
    "api_health": {
        "purpose": "Probe /health of all six backend REST APIs at once",
        "use_for": ["Diagnose which backend is down before querying data"],
        "api": "all backends /health",
        "params": "none",
    },
}

TOOL_DECISION_RULE = (
    "If the question is about what the health system does "
    "(facilities, testing, vaccination, staffing) -> query_hmis; browse "
    "valid indicators with hmis_list_indicators. If it is about medically "
    "certified deaths, ICD-10, or cause-of-death in the MCCD system -> "
    "query_mccd; search causes with mccd_causes or categorize with "
    "mccd_categorize. If it is about population-level SRS mortality, life "
    "expectancy, or demographic indicators -> srs_query_life_table, "
    "srs_query_cod, srs_query_bulletin, or srs_summary_indicators. If it is "
    "about Census of India population, variables, or projections -> "
    "census_query, census_population, or census_population_projection. If it "
    "is about household spending or food items -> query_consumption. If it "
    "is about illness, hospitalization, outpatient care, or health "
    "expenditure in NSS surveys -> query_healthsurvey. If a tool reports an "
    "unavailable backend, call api_health to diagnose."
)


@mcp.tool()
def tool_guide() -> dict:
    """Return a routing guide for choosing the appropriate India data tool.

    Call this when unsure which tool to use for a health data question
    about India. Returns topic mappings, backend routes, and decision rules
    for every registered tool.
    """
    guide = {name: dict(entry) for name, entry in TOOL_REGISTRY.items()}
    guide["decision_rule"] = TOOL_DECISION_RULE
    return guide


if __name__ == "__main__":
    mcp.run()
