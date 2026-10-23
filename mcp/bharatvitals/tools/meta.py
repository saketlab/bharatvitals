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


BACKENDS = [
    ("hmisindia", HMIS_API_URL),
    ("mccdindia", MCCD_API_URL),
    ("censusindia", CENSUS_API_URL),
    ("srsindia", SRS_API_URL),
    ("crsindia", CRS_API_URL),
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
    "api_health": {
        "purpose": "Probe /health of all five backend REST APIs at once",
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
    "census_query, census_population, or census_population_projection. If a "
    "tool reports an unavailable backend, call api_health to diagnose."
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

