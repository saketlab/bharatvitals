import json
from typing import TYPE_CHECKING, Optional

from fastmcp import FastMCP

if TYPE_CHECKING:
    from bharatpulse.client import BharatPulseClient

_SOURCE = "hmis"


def _to_json(data: object) -> str:
    return json.dumps(data, indent=2)


def register(mcp: FastMCP, client: "BharatPulseClient") -> None:

    @mcp.tool()
    def hmis_list_states() -> str:
        """Return all 36 canonical state and union territory names in the HMIS data."""
        return _to_json(client.get(_SOURCE, "/states", {}))

    @mcp.tool()
    def hmis_list_districts(state: Optional[str] = None) -> str:
        """Return state-district pairs in the district-level HMIS data.

        Args:
            state: Optional state name to filter results.

        Returns:
            JSON array of {state, district} objects.
        """
        return _to_json(client.get(_SOURCE, "/districts", {"state": state}))

    @mcp.tool()
    def hmis_list_indicators(
        pattern: Optional[str] = None,
        geography: str = "state",
        match: str = "fixed",
        min_months: Optional[int] = None,
    ) -> str:
        """List or search available HMIS indicators.

        Args:
            pattern: Optional search string (case-insensitive substring by default).
                     Leave empty to list all indicators.
            geography: "state" for state-level indicators (default),
                       "district" for district-level.
            match: "fixed" (substring), "regex", or "fuzzy" (approximate).
            min_months: Only include indicators with at least this many months of data.

        Returns:
            JSON array with canonical_name, n_yearmon, first_month, last_month.
        """
        return _to_json(
            client.get(
                _SOURCE,
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
        """Query India HMIS health data and return a monthly time-series.

        Args:
            indicator: Indicator name or search pattern, e.g. "malaria" or
                       "Live Birth - Female". Matched against canonical names.
            geography: "state" (default) or "district".
            state: Comma-separated state names, e.g. "Bihar,Odisha".
                   Case-insensitive; common aliases are resolved automatically.
            district: Comma-separated district names. Only valid when
                      geography="district".
            sector: Comma-separated sectors — "Total", "Public", "Private",
                    "Rural", "Urban".
            category: Sub-category filter, e.g. "Total", "Number Positive".
            from_date: Start month as "Mon YYYY", e.g. "Apr 2015".
            to_date: End month as "Mon YYYY", e.g. "Mar 2020".
            match: "fixed" (substring, default), "regex", or "fuzzy".
            backend: "auto" (default; duckdb for district, arrow for state),
                     "arrow", or "duckdb".
            limit: Maximum rows to return (default 10 000; 0 = unlimited).

        Returns:
            JSON array with canonical_name, monyear, state, sector, category,
            value (and district when geography="district").
        """
        return _to_json(
            client.get(
                _SOURCE,
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
        """Detect whether an HMIS indicator has seasonal or periodic patterns.

        Args:
            indicator: Indicator name (exact or substring match).
            state: State to filter to. Use a single state for a clean series.
            category: Sub-category filter, e.g. "Total".
            sector: Sector filter, e.g. "Total" or "Public".
            method: "pgram" — periodogram + ACF (default, evenly sampled).
                    "lomb_scargle" — Baluev FAP test, robust to missing months.
            detrend: Remove a linear trend before analysis (default True).

        Returns:
            JSON with is_periodic, dominant_period (months), and significance
            metrics (spectral_power + acf_peak for pgram; fap for lomb_scargle).
        """
        return _to_json(
            client.get(
                _SOURCE,
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
        """Decompose an HMIS time series into trend, seasonal, and residual components.

        Uses STL (Seasonal-Trend decomposition via Loess) on monthly data.

        Args:
            indicator: Indicator name (exact or substring match).
            state: State to filter to. Single state recommended.
            category: Sub-category filter.
            sector: Sector filter.
            frequency: Seasonal period in months (default 12 = annual cycle).
            s_window: "periodic" — constant seasonality (default).
                      Odd integer as string, e.g. "13" — allows seasonality to
                      evolve; useful for long HMIS series spanning 17+ years.

        Returns:
            JSON array with date, observed, trend, seasonal, remainder columns.
        """
        return _to_json(
            client.get(
                _SOURCE,
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
