import json
from typing import TYPE_CHECKING, Optional

from fastmcp import FastMCP

if TYPE_CHECKING:
    from bharatvitals.client import BharatVitalsClient

SOURCE = "hmis"
PACKAGE = "hmisindia"
LABEL = "HMIS"
GUIDE = (
    "840+ health indicators, 36 states, 700+ districts, monthly "
    "2008-2025. Start with hmis_list_indicators, then hmis_query."
)


def _to_json(data: object) -> str:
    return json.dumps(data, indent=2)


def register(mcp: FastMCP, client: "BharatVitalsClient") -> None:

    @mcp.tool()
    def hmis_list_states() -> str:
        """List all 36 state/UT names in HMIS data."""
        return _to_json(client.get(SOURCE, "/states", {}))

    @mcp.tool()
    def hmis_list_districts(state: Optional[str] = None) -> str:
        """State-district pairs in district-level HMIS data.

        Args:
            state: State name to filter, or None for all.
        """
        return _to_json(client.get(SOURCE, "/districts", {"state": state}))

    @mcp.tool()
    def hmis_list_indicators(
        pattern: Optional[str] = None,
        geography: str = "state",
        match: str = "fixed",
        min_months: Optional[int] = None,
    ) -> str:
        """Search HMIS indicators.

        Args:
            pattern: Search string (case-insensitive). Empty = all indicators.
            geography: "state" (default) or "district".
            match: "fixed" (substring), "regex", or "fuzzy".
            min_months: Minimum months of data coverage.
        """
        return _to_json(
            client.get(
                SOURCE,
                "/indicators",
                {
                    "pattern": pattern,
                    "geography": geography,
                    "match": match,
                    "min_months": min_months,
                },
            )
        )

    @mcp.tool()
    def hmis_query(
        indicator: str,
        geography: str = "state",
        state: Optional[str] = None,
        district: Optional[str] = None,
        sector: Optional[str] = None,
        category: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        match: str = "fixed",
        backend: str = "auto",
        limit: int = 10000,
    ) -> str:
        """Query HMIS health data as monthly time-series.

        Args:
            indicator: Name or search pattern, e.g. "malaria", "Live Birth - Female".
            geography: "state" (default) or "district".
            state: Comma-separated state names, e.g. "Bihar,Odisha".
            district: Comma-separated district names (geography="district" only).
            sector: "Total", "Public", "Private", "Rural", or "Urban".
            category: Sub-category, e.g. "Total", "Number Positive".
            from_date: Start month, e.g. "Apr 2015".
            to_date: End month, e.g. "Mar 2020".
            match: "fixed" (substring), "regex", or "fuzzy".
            backend: "auto" (default), "arrow", or "duckdb".
            limit: Max rows (default 10000, 0 = unlimited).
        """
        return _to_json(
            client.get(
                SOURCE,
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
                    "backend": backend,
                    "limit": limit,
                },
            )
        )

    @mcp.tool()
    def hmis_detect_periodicity(
        indicator: str,
        state: Optional[str] = None,
        category: Optional[str] = None,
        sector: Optional[str] = None,
        method: str = "pgram",
        detrend: bool = True,
    ) -> str:
        """Detect seasonal or periodic patterns in an HMIS indicator.

        Args:
            indicator: Indicator name (exact or substring).
            state: Single state recommended for clean series.
            category: e.g. "Total".
            sector: e.g. "Total" or "Public".
            method: "pgram" (periodogram + ACF) or "lomb_scargle" (robust to gaps).
            detrend: Remove linear trend first (default True).
        """
        return _to_json(
            client.get(
                SOURCE,
                "/periodicity",
                {
                    "indicator": indicator,
                    "state": state,
                    "category": category,
                    "sector": sector,
                    "method": method,
                    "detrend": str(detrend).upper(),
                },
            )
        )

    @mcp.tool()
    def hmis_decompose_series(
        indicator: str,
        state: Optional[str] = None,
        category: Optional[str] = None,
        sector: Optional[str] = None,
        frequency: int = 12,
        s_window: str = "periodic",
    ) -> str:
        """STL decomposition into trend, seasonal, and residual.

        Args:
            indicator: Indicator name (exact or substring).
            state: Single state recommended.
            category: Sub-category filter.
            sector: Sector filter.
            frequency: Seasonal period in months (default 12).
            s_window: "periodic" (constant) or odd integer string, e.g. "13"
                      (evolving seasonality for long series).
        """
        return _to_json(
            client.get(
                SOURCE,
                "/decompose",
                {
                    "indicator": indicator,
                    "state": state,
                    "category": category,
                    "sector": sector,
                    "frequency": frequency,
                    "s_window": s_window,
                },
            )
        )
