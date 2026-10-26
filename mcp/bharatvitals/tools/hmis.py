import re
from typing import TYPE_CHECKING, Any, Literal, Optional

from fastmcp import FastMCP

from bharatvitals.normalize import INDICATOR_WORDS
from bharatvitals.tools._common import READ_ONLY, Match, to_json

if TYPE_CHECKING:
    from bharatvitals.client import BharatVitalsClient

SOURCE = "hmis"
PACKAGE = "hmisindia"
LABEL = "HMIS"
GUIDE = (
    "Use for health services delivered (deliveries, immunisation, ANC, tests, "
    "OPD) by month, state or district, Apr 2008-2025, 840+ indicators. These "
    "are facility counts, not population coverage. Sector adds public and "
    "private; district rows carry LGD codes. Start with "
    "hmis_list_indicators for the exact name, then hmis_query with sector and "
    "category set, since an unfiltered query returns every combination."
)


def register(mcp: FastMCP, client: "BharatVitalsClient") -> None:
    def get(endpoint: str, params: dict[str, Any]) -> str:
        return to_json(client.get(SOURCE, endpoint, params))

    def query(endpoint: str, params: dict[str, Any]) -> str:
        found = client.get(SOURCE, endpoint, params)
        name = params.get("indicator")
        # a name that matches no indicator returns the closest indicators
        if name and not found["rows"]:
            known = {"pattern": name, "match": params.get("match", "fixed"), "limit": 1}
            if not client.get(SOURCE, "/indicators", known)["rows"]:
                names = "; ".join(_closest(client, name))
                found["note"] = f"No indicator matches {name!r}." + (
                    f" Close names: {names}. Pass one as indicator."
                    if names
                    else " Search hmis_list_indicators with a single word."
                )
        return to_json(found)

    @mcp.tool(annotations=READ_ONLY)
    def hmis_list_states() -> str:
        """HMIS states/UTs with two-letter codes (state_name, state_abbr).

        Also lists "M/O Defence" and "M/O Railways", which report outside every
        state. Pass state="India" in other tools for the national row.
        """
        return get("/states", {})

    @mcp.tool(annotations=READ_ONLY)
    def hmis_list_districts(
        state: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """State-district pairs with LGD codes in district-level HMIS data.

        Args:
            state: Comma-separated state names or two-letter codes, e.g. "Kerala,TN".
                   None = all states.
            limit: Rows per page, 1-10000 (default 1000).
            offset: Rows to skip; pass next_offset from the previous result.
        """
        return get("/districts", {"state": state, "limit": limit, "offset": offset})

    @mcp.tool(annotations=READ_ONLY)
    def hmis_list_indicators(
        pattern: Optional[str] = None,
        geography: Literal["state", "district"] = "state",
        match: Match = "fixed",
        min_months: Optional[int] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """Search HMIS indicators; returns canonical_name and month coverage.

        Pass the canonical_name to hmis_query to get exactly one indicator.
        Search single words ("deliveries", not "institutional delivery") or
        use match="fuzzy".

        Args:
            pattern: Case-insensitive search, e.g. "measles", "deliveries".
                     None = all indicators.
            geography: "state" (default) or "district"; coverage differs.
            match: "fixed" (substring), "regex", or "fuzzy" (typo tolerant).
            min_months: Only indicators with at least this many months of data.
            limit: Rows per page, 1-10000 (default 1000).
            offset: Rows to skip; pass next_offset from the previous result.
        """
        found = client.get(
            SOURCE,
            "/indicators",
            {
                "pattern": pattern,
                "geography": geography,
                "match": match,
                "min_months": min_months,
                "limit": limit,
                "offset": offset,
            },
        )
        if pattern and not found["rows"]:
            names = "; ".join(_closest(client, pattern))
            if names:
                found["note"] = (
                    f"No indicator matches this search. Closest names: {names}."
                )
        return to_json(found)

    @mcp.tool(annotations=READ_ONLY)
    def hmis_query(
        indicator: str,
        geography: Literal["state", "district"] = "state",
        state: Optional[str] = None,
        district: Optional[str] = None,
        sector: Optional[str] = None,
        category: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        match: Match = "fixed",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """Monthly HMIS values, one row per indicator x state x month x sector x category.

        Without state the rows include India (national total) and the
        M/O Defence and M/O Railways rows, so never sum across all rows.
        A substring indicator can match several indicators; check
        canonical_name in the rows or pass the exact name.

        Args:
            indicator: Indicator name or search string, e.g. "Live Birth - Female".
            geography: "state" (default) or "district".
            state: Comma-separated state names or two-letter codes, e.g. "Bihar,OR".
                   "India" = national row.
            district: Comma-separated district names from hmis_list_districts, any
                      case; needs geography="district". Unknown names are an error
                      that suggests close matches.
            sector: Comma-separated: "total", "public", "private", "rural", "urban".
            category: Sub-category, e.g. "Total" or "Number Positive".
            from_date: Start month, "Apr 2015" or "2015-04".
            to_date: End month, "Mar 2020" or "2020-03".
            match: "fixed" (substring), "regex", or "fuzzy".
            limit: Rows per page, 1-10000 (default 1000).
            offset: Rows to skip; pass next_offset from the previous result.
        """
        return query(
            "/query",
            {
                "indicator": indicator,
                "geography": geography,
                "state": state,
                "district": district,
                "sector": sector,
                "category": category,
                "from": from_date,
                "to": to_date,
                "match": match,
                "limit": limit,
                "offset": offset,
            },
        )

    @mcp.tool(annotations=READ_ONLY)
    def hmis_detect_periodicity(
        indicator: str,
        state: str,
        sector: str = "Total",
        category: str = "Total",
        method: Literal["pgram", "lomb_scargle"] = "pgram",
        detrend: bool = True,
    ) -> str:
        """Test one monthly HMIS series for seasonality; one row with dominant_period.

        The filters must leave exactly one series (indicator x state x sector x
        category), otherwise the API says how many match.

        Args:
            indicator: Exact indicator name from hmis_list_indicators.
            state: One state name or two-letter code, or "India".
            sector: "Total" (default), "Public", "Private", "Rural", or "Urban"; any case.
            category: Sub-category, default "Total".
            method: "pgram" (periodogram + ACF) or "lomb_scargle" (robust to gaps).
            detrend: Remove a linear trend first (default True).
        """
        return get(
            "/periodicity",
            {
                "indicator": indicator,
                "state": state,
                "category": category,
                "sector": sector,
                "method": method,
                "detrend": detrend,
            },
        )

    @mcp.tool(annotations=READ_ONLY)
    def hmis_decompose_series(
        indicator: str,
        state: str,
        sector: str = "Total",
        category: str = "Total",
        frequency: int = 12,
        s_window: str = "periodic",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """STL decomposition of one monthly HMIS series: date, observed, trend, seasonal, remainder.

        The filters must leave exactly one series, as for hmis_detect_periodicity.

        Args:
            indicator: Exact indicator name from hmis_list_indicators.
            state: One state name or two-letter code, or "India".
            sector: "Total" (default), "Public", "Private", "Rural", or "Urban"; any case.
            category: Sub-category, default "Total".
            frequency: Seasonal period in months (default 12).
            s_window: "periodic" (fixed seasonality) or an odd integer >= 7 as a
                      string, e.g. "13" (seasonality that drifts).
            limit: Rows per page, 1-10000 (default 1000).
            offset: Rows to skip; pass next_offset from the previous result.
        """
        return get(
            "/decompose",
            {
                "indicator": indicator,
                "state": state,
                "category": category,
                "sector": sector,
                "frequency": frequency,
                "s_window": s_window,
                "limit": limit,
                "offset": offset,
            },
        )


# words in so many indicator names that they rank nothing
_GENERIC = {
    "care",
    "number",
    "total",
    "cases",
    "case",
    "count",
    "rate",
    "data",
    "the",
    "and",
    "for",
    "with",
}


def _closest(client: "BharatVitalsClient", name: str, n: int = 5) -> list[str]:
    """Indicators sharing the rarest words with name; fuzzy matching as a fallback."""
    plain = re.sub(r"[\\()|]", " ", name).lower()
    for word, swap in INDICATOR_WORDS.items():
        plain = plain.replace(word, swap.lower())
    words = set(re.findall(r"[a-z]{3,}", plain)) - _GENERIC
    pool: dict[str, tuple[int, float]] = {}
    for word in words:
        whole = re.compile(
            rf"\b{re.escape(word)}", re.I
        )  # "anc" must not match "cancer"
        rows = client.get(SOURCE, "/indicators", {"pattern": word, "limit": 500})[
            "rows"
        ]
        rows = [r for r in rows if whole.search(r["canonical_name"])]
        for row in rows:
            hits, rarity = pool.get(row["canonical_name"], (0, 0.0))
            # most query words first; rarer words break ties
            pool[row["canonical_name"]] = (hits + 1, rarity + 1 / len(rows))
    if not pool:
        fuzzy = client.get(
            SOURCE, "/indicators", {"pattern": name, "match": "fuzzy", "limit": n}
        )
        return [r["canonical_name"] for r in fuzzy["rows"]]
    return sorted(pool, key=lambda t: (-pool[t][0], -pool[t][1], len(t)))[:n]
