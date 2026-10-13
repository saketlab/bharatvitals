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


