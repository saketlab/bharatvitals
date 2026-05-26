import json
from typing import TYPE_CHECKING, Optional

from fastmcp import FastMCP

if TYPE_CHECKING:
    from bharatpulse.client import BharatPulseClient

_SOURCE = "srs"


def _to_json(data: object) -> str:
    return json.dumps(data)


def register(mcp: FastMCP, client: "BharatPulseClient") -> None:

    @mcp.resource("srs://states")
    def srs_states_resource() -> str:
        """All 36 canonical state/UT names in SRS data (excludes 'India')."""
        return _to_json(client.get(_SOURCE, "/states", {}))

    @mcp.resource("srs://life_table_periods")
    def srs_life_table_periods_resource() -> str:
        """Life table periods (5-year rolling windows)."""
        return _to_json(client.get(_SOURCE, "/life_table_periods", {}))

    @mcp.resource("srs://cod_tables")
    def srs_cod_tables_resource() -> str:
        """Cause-of-death table metadata (slugs, descriptions, periods)."""
        return _to_json(client.get(_SOURCE, "/cod_tables", {}))

    @mcp.resource("srs://bulletin_indicators")
    def srs_bulletin_indicators_resource() -> str:
        """Bulletin indicator codes: cbr, cdr, ngr, imr."""
        return _to_json(client.get(_SOURCE, "/bulletin_indicators", {}))

    @mcp.tool()
    def srs_list_states() -> str:
        """List all 36 canonical state/UT names in SRS data.

        Use state="India" in query tools for the national aggregate.
        """
        return _to_json(client.get(_SOURCE, "/states", {}))

    @mcp.tool()
    def srs_list_life_table_periods() -> str:
        """Life table periods (5-year rolling windows).

        E.g. "2007-2011", "2008-2012", ..., "2020-2024".
        """
        return _to_json(client.get(_SOURCE, "/life_table_periods", {}))

    @mcp.tool()
    def srs_list_cod_tables() -> str:
        """Cause-of-death table slugs with metadata.

        Use table_slug values in srs_query_cod().
        """
        return _to_json(client.get(_SOURCE, "/cod_tables", {}))

    @mcp.tool()
    def srs_list_cod_periods() -> str:
        """Cause-of-death periods (2-3 year windows).

        E.g. "2007-2009", "2010-2013", ..., "2022-2024".
        """
        return _to_json(client.get(_SOURCE, "/cod_periods", {}))

    @mcp.tool()
    def srs_list_bulletin_years() -> str:
        """Years with SRS Bulletin vital statistics (1997-2024, 2002 missing)."""
        return _to_json(client.get(_SOURCE, "/bulletin_years", {}))

    @mcp.tool()
    def srs_available_periods() -> str:
        """Temporal coverage for all SRS data types (life tables, CoD, bulletin)."""
        return _to_json(client.get(_SOURCE, "/available_periods", {}))

    @mcp.tool()
    def srs_life_expectancy_trend() -> str:
        """National life expectancy at birth, 1970-75 to present (SRS Statement 1).

        Columns: period, mid_year, lifespan_at_birth by total/rural/urban
        and person/male/female.
        """
        return _to_json(client.get(_SOURCE, "/life_expectancy_trend", {}))

    @mcp.tool()
    def srs_summary_indicators(
        state: Optional[str] = None,
        period: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10000,
    ) -> str:
        """Mortality indicators from life tables.

        e0 (life expectancy at birth), e0_sex_gap (female - male),
        u5mr (5q0, per 1000), adult_mortality (45q15, per 1000).

        Args:
            state: State name or "India". None = all states.
            period: e.g. "2019-2023". None = all periods.
            category: "Total", "Rural", or "Urban". None = all.
            limit: Max rows (default 10000, 0 = unlimited).
        """
        return _to_json(
            client.get(
                _SOURCE,
                "/summary_indicators",
                {
                    "state": state,
                    "period": period,
                    "category": category,
                    "limit": limit,
                },
            )
        )

    @mcp.tool()
    def srs_epi_transition(
        period: Optional[str] = None,
    ) -> str:
        """NCD vs communicable disease fractions from cause-of-death data.

        Cause-group percentages with NCD fraction per period.

        Args:
            period: CoD period label, e.g. "2020-2022". None = all periods.
        """
        return _to_json(client.get(_SOURCE, "/epi_transition", {"period": period}))

    @mcp.tool()
    def srs_arriaga_decompose(
        state: str = "India",
        period1: str = "2007-2011",
        period2: str = "2019-2023",
        category: str = "Total",
        sex: str = "total",
    ) -> str:
        """Arriaga (1984) decomposition of e0 change by age group.

        Splits total life expectancy change between two periods into
        additive age-specific contributions.

        Args:
            state: State name or "India".
            period1: Baseline period, e.g. "2007-2011".
            period2: Comparison period, e.g. "2019-2023".
            category: "Total", "Rural", or "Urban".
            sex: "total", "male", or "female".
        """
        return _to_json(
            client.get(
                _SOURCE,
                "/arriaga",
                {
                    "state": state,
                    "period1": period1,
                    "period2": period2,
                    "category": category,
                    "sex": sex,
                },
            )
        )

    @mcp.tool()
    def srs_query_life_table(
        state: Optional[str] = None,
        period: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10000,
    ) -> str:
        """SRS abridged life tables (nqx, lx, nlx, ex by age, sex).

        Args:
            state: State name or "India". E.g. "Bihar", "delhi".
            period: e.g. "2017-2021". See srs_list_life_table_periods().
            category: "Total", "Rural", or "Urban".
            limit: Max rows (default 10000, 0 = unlimited).
        """
        return _to_json(
            client.get(
                _SOURCE,
                "/life_table",
                {
                    "state": state,
                    "period": period,
                    "category": category,
                    "limit": limit,
                },
            )
        )

    @mcp.tool()
    def srs_query_cod(
        table: str = "cause_groups_national",
        period: Optional[str] = None,
    ) -> str:
        """SRS cause-of-death tables by slug. See srs_list_cod_tables() for slugs.

        Args:
            table: "cause_groups_national" (Table 2.1A, major cause groups),
                   "cause_groups_state_type" (Table 2.1B, EAG vs other),
                   "cause_top10_zones" (Tables 5.1A-F, top-10 by zone),
                   "sample_units" (Table 1.1).
            period: e.g. "2020-2022". None = all periods.
        """
        return _to_json(
            client.get(
                _SOURCE,
                "/cod",
                {
                    "table": table,
                    "period": period,
                },
            )
        )

    @mcp.tool()
    def srs_query_bulletin(
        indicator: Optional[str] = None,
        state: Optional[str] = None,
        year: Optional[int] = None,
        category: Optional[str] = None,
        limit: int = 10000,
    ) -> str:
        """SRS Bulletin vital statistics: CBR, CDR, NGR, IMR (1997-2024).

        36 states/UTs with Total/Rural/Urban breakdowns.

        Args:
            indicator: "cbr", "cdr", "ngr", or "imr". None = all.
            state: State name. "India" for national.
            year: e.g. 2020.
            category: "Total", "Rural", or "Urban". None = all.
            limit: Max rows (default 10000, 0 = unlimited).
        """
        return _to_json(
            client.get(
                _SOURCE,
                "/bulletin",
                {
                    "indicator": indicator,
                    "state": state,
                    "year": year,
                    "category": category,
                    "limit": limit,
                },
            )
        )

    @mcp.tool()
    def srs_query_stat_report(
        indicator: Optional[str] = None,
        state: Optional[str] = None,
        year: Optional[int] = None,
        category: Optional[str] = None,
        limit: int = 10000,
    ) -> str:
        """SRS Statistical Report indicators (2011-2024).

        Includes TFR, NMR, U5MR and other indicators not in the Bulletin.
        23 states, Total/Rural/Urban breakdowns.

        Args:
            indicator: Comma-separated codes, e.g. "tfr", "nmr,u5mr,imr".
                       Key codes: tfr, nmr, u5mr, imr, cdr, cbr, enmr, lnmr, pnmr,
                       cmr, perimr, sbr, gfr, grr. None = all.
            state: State name. "India" for national.
            year: e.g. 2020.
            category: "Total", "Rural", or "Urban". None = all.
            limit: Max rows (default 10000, 0 = unlimited).
        """
        return _to_json(
            client.get(
                _SOURCE,
                "/stat_report",
                {
                    "indicator": indicator,
                    "state": state,
                    "year": year,
                    "category": category,
                    "limit": limit,
                },
            )
        )
