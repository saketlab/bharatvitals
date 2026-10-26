from typing import TYPE_CHECKING, Any, Literal, Callable, Optional

from fastmcp import FastMCP

from bharatvitals.tools._common import READ_ONLY, Sector, to_json

if TYPE_CHECKING:
    from bharatvitals.client import BharatVitalsClient

SOURCE = "srs"
PACKAGE = "srsindia"
LABEL = "SRS"
GUIDE = (
    "Use for official rates: IMR, CBR, CDR, TFR, NMR, U5MR, MMR and life "
    "expectancy for states and India by sector, plus life tables and "
    "verbal-autopsy cause of death representative of all deaths. Bulletin "
    "1997-2024, statistical reports 2011-2024, life expectancy since 1970. "
    "Start with srs_available_periods or srs_summary_indicators."
)


def register(mcp: FastMCP, client: "BharatVitalsClient") -> None:
    def get(endpoint: str, params: dict[str, Any]) -> str:
        return to_json(client.get(SOURCE, endpoint, params))

    @mcp.resource("srs://states")
    def srs_states_resource() -> str:
        """SRS states/UTs with two-letter codes (excludes India)."""
        return get("/states", {})

    @mcp.resource("srs://life_table_periods")
    def srs_life_table_periods_resource() -> str:
        """Life table periods (5-year rolling windows)."""
        return get("/life_table_periods", {})

    @mcp.resource("srs://cod_tables")
    def srs_cod_tables_resource() -> str:
        """Cause-of-death table metadata (slugs, descriptions, periods)."""
        return get("/cod_tables", {})

    @mcp.resource("srs://bulletin_indicators")
    def srs_bulletin_indicators_resource() -> str:
        """Bulletin indicator codes: cbr, cdr, ngr, imr."""
        return get("/bulletin_indicators", {})

    for name, endpoint, doc in _LIST_TOOLS:
        mcp.tool(_list_tool(client, endpoint, doc), name=name, annotations=READ_ONLY)

    @mcp.tool(annotations=READ_ONLY)
    def srs_summary_indicators(
        state: Optional[str] = None,
        period: Optional[str] = None,
        sector: Sector = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """Mortality indicators from life tables.

        e0 (life expectancy at birth), e0_sex_gap (female - male),
        u5mr (5q0, per 1000), adult_mortality (45q15, per 1000).

        Args:
            state: Comma-separated state names or two-letter codes, e.g. "Bihar,KL".
                   "India" = national row. None = all.
            period: e.g. "2019-2023". None = all periods.
            sector: "total", "rural", or "urban". None = all three.
            limit: Rows per page, 1-10000 (default 1000).
            offset: Rows to skip; pass next_offset from the previous result.
        """
        return get(
            "/summary_indicators",
            {
                "state": state,
                "period": period,
                "sector": sector,
                "limit": limit,
                "offset": offset,
            },
        )

    @mcp.tool(annotations=READ_ONLY)
    def srs_epi_transition(
        period: Optional[str] = None,
    ) -> str:
        """Share of all deaths by broad cause group per period (person_pct, male_pct, female_pct).

        ncd_fraction, on the NCD row only, is NCD / (NCD + communicable,
        maternal, perinatal and nutritional); use person_pct for the NCD
        share of all deaths.

        Args:
            period: CoD period label, e.g. "2020-2022". None = all periods.
        """
        return get("/epi_transition", {"period": period})

    @mcp.tool(annotations=READ_ONLY)
    def srs_arriaga_decompose(
        state: str = "India",
        period1: str = "2007-2011",
        period2: str = "2019-2023",
        sector: Literal["total", "rural", "urban"] = "total",
        sex: Literal["total", "male", "female"] = "total",
    ) -> str:
        """Arriaga (1984) decomposition of e0 change by age group.

        Splits total life expectancy change between two periods into
        additive age-specific contributions.

        Args:
            state: One state name or two-letter code, or "India".
            period1: Baseline period, e.g. "2007-2011".
            period2: Comparison period, e.g. "2019-2023".
            sector: "total", "rural", or "urban".
            sex: "total", "male", or "female".
        """
        return get(
            "/arriaga",
            {
                "state": state,
                "period1": period1,
                "period2": period2,
                "sector": sector,
                "sex": sex,
            },
        )

    @mcp.tool(annotations=READ_ONLY)
    def srs_query_life_table(
        state: Optional[str] = None,
        period: Optional[str] = None,
        sector: Sector = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """SRS abridged life tables (nqx, lx, nlx, ex by age, sex).

        Args:
            state: Comma-separated state names or two-letter codes, e.g. "Bihar,KL".
                   "India" = national row. None = all.
            period: e.g. "2017-2021". See srs_list_life_table_periods().
            sector: "total", "rural", or "urban".
            limit: Rows per page, 1-10000 (default 1000).
            offset: Rows to skip; pass next_offset from the previous result.
        """
        return get(
            "/life_table",
            {
                "state": state,
                "period": period,
                "sector": sector,
                "limit": limit,
                "offset": offset,
            },
        )

    @mcp.tool(annotations=READ_ONLY)
    def srs_query_cod(
        table: str = "cause_groups_national",
        period: Optional[str] = None,
        state: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """SRS cause-of-death tables by slug. See srs_list_cod_tables() for slugs.

        Args:
            table: "cause_groups_national" (Table 2.1A, major cause groups),
                   "cause_groups_state_type" (Table 2.1B, EAG vs other),
                   "cause_top10_zones" (Tables 5.1A-F, top-10 by zone),
                   "sample_units" (Table 1.1).
            period: e.g. "2020-2022". None = all periods.
            state: Comma-separated state names or two-letter codes; only for
                   tables with a state column (sample_units).
            limit: Rows per page, 1-10000 (default 1000).
            offset: Rows to skip; pass next_offset from the previous result.
        """
        return get(
            "/cod",
            {
                "table": table,
                "period": period,
                "state": state,
                "limit": limit,
                "offset": offset,
            },
        )

    @mcp.tool(annotations=READ_ONLY)
    def srs_query_bulletin(
        indicator: Optional[str] = None,
        state: Optional[str] = None,
        year: Optional[str] = None,
        sector: Sector = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """SRS Bulletin vital statistics: CBR, CDR, NGR, IMR (1997-2024).

        36 states/UTs and India, total/rural/urban. The long series for these
        four; srs_query_stat_report has TFR, NMR, U5MR and the rest. Each row
        carries its unit.

        Args:
            indicator: "cbr", "cdr", "ngr", or "imr". None = all.
            state: Comma-separated state names or two-letter codes, e.g. "Bihar,KL".
                   "India" = national row. None = all.
            year: Comma-separated years or a range, e.g. "2020" or "2015:2020".
            sector: "total", "rural", or "urban". None = all three.
            limit: Rows per page, 1-10000 (default 1000).
            offset: Rows to skip; pass next_offset from the previous result.
        """
        return get(
            "/bulletin",
            {
                "indicator": indicator,
                "state": state,
                "year": year,
                "sector": sector,
                "limit": limit,
                "offset": offset,
            },
        )

    @mcp.tool(annotations=READ_ONLY)
    def srs_query_stat_report(
        indicator: Optional[str] = None,
        state: Optional[str] = None,
        year: Optional[str] = None,
        sector: Sector = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """SRS Statistical Report indicators (2011-2024).

        Includes TFR, NMR, U5MR and other indicators not in the Bulletin.
        23 larger states and India, total/rural/urban. Use srs_query_bulletin
        for CBR, CDR, NGR and IMR back to 1997. Each row carries its unit.

        Args:
            indicator: Comma-separated codes, e.g. "tfr", "nmr,u5mr,imr".
                       Codes: cbr, cdr, cmr, enmr, gfr, gmfr, grr, imr, lnmr, nmr,
                       perimr, pnmr, sbr, tfr, tmfr, u5mr. None = all.
            state: Comma-separated state names or two-letter codes, e.g. "Bihar,KL".
                   "India" = national row. None = all.
            year: Comma-separated years or a range, e.g. "2020" or "2015:2020".
            sector: "total", "rural", or "urban". None = all three.
            limit: Rows per page, 1-10000 (default 1000).
            offset: Rows to skip; pass next_offset from the previous result.
        """
        return get(
            "/stat_report",
            {
                "indicator": indicator,
                "state": state,
                "year": year,
                "sector": sector,
                "limit": limit,
                "offset": offset,
            },
        )

    @mcp.tool(annotations=READ_ONLY)
    def srs_query_mmr(
        state: Optional[str] = None,
        period: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """Maternal mortality ratio: maternal deaths per 100,000 live births, with CIs.

        Args:
            state: Comma-separated state names or two-letter codes, e.g. "Bihar,KL".
                   "India" = national row. None = all.
            period: Three-year period from srs_list_mmr_periods, e.g. "2018-2020".
            limit: Rows per page, 1-10000 (default 1000).
            offset: Rows to skip; pass next_offset from the previous result.
        """
        return get(
            "/mmr",
            {"state": state, "period": period, "limit": limit, "offset": offset},
        )

    @mcp.tool(annotations=READ_ONLY)
    def srs_list_nsso_divisions(state: Optional[str] = None) -> str:
        """NSSO natural division names, the sub-state regions SRS reports.

        Args:
            state: Comma-separated state names or two-letter codes. None = all.
        """
        return get("/nsso_divisions", {"state": state})

    @mcp.tool(annotations=READ_ONLY)
    def srs_query_nsso_regions(
        state: Optional[str] = None,
        year: Optional[str] = None,
        division: Optional[str] = None,
        include_totals: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """CBR, CDR, IMR and U5MR by NSSO natural division (below state level).

        Args:
            state: Comma-separated state names or two-letter codes. No India row.
            year: Comma-separated years or a range, e.g. "2020" or "2018:2020".
            division: Exact division name from srs_list_nsso_divisions,
                      e.g. "Northern" (with state="BR").
            include_totals: Also return the state-level Total rows.
            limit: Rows per page, 1-10000 (default 1000).
            offset: Rows to skip; pass next_offset from the previous result.
        """
        return get(
            "/nsso_regions",
            {
                "state": state,
                "year": year,
                "division": division,
                "include_totals": include_totals,
                "limit": limit,
                "offset": offset,
            },
        )

    @mcp.tool(annotations=READ_ONLY)
    def srs_list_nsso_districts(
        state: Optional[str] = None,
        division: Optional[str] = None,
        include_approximate: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """Districts in each NSSO natural division, to link districts to srs_query_nsso_regions.

        Args:
            state: Comma-separated state names or two-letter codes. No India row.
            division: Exact division name from srs_list_nsso_divisions, e.g. "Northern".
            include_approximate: Also return approximate historical mappings.
            limit: Rows per page, 1-10000 (default 1000).
            offset: Rows to skip; pass next_offset from the previous result.
        """
        return get(
            "/nsso_districts",
            {
                "state": state,
                "natural_division": division,
                "include_approximate": include_approximate,
                "limit": limit,
                "offset": offset,
            },
        )


def _list_tool(
    client: "BharatVitalsClient", endpoint: str, doc: str
) -> Callable[[], str]:
    def tool() -> str:
        return to_json(client.get(SOURCE, endpoint, {}))

    tool.__doc__ = doc
    return tool


# (tool name, route, description) for the routes that take no arguments
_LIST_TOOLS = (
    (
        "srs_list_states",
        "/states",
        (
            "SRS states/UTs with two-letter codes (state_name, state_abbr).\n"
            "\n"
            'Pass state="India" in other tools for the national row.'
        ),
    ),
    (
        "srs_list_life_table_periods",
        "/life_table_periods",
        (
            "Life table periods (5-year rolling windows).\n"
            "\n"
            'E.g. "2007-2011", "2008-2012", ..., "2020-2024".'
        ),
    ),
    (
        "srs_list_cod_tables",
        "/cod_tables",
        (
            "Cause-of-death table slugs with metadata.\n"
            "\n"
            "Use table_slug values in srs_query_cod()."
        ),
    ),
    (
        "srs_list_cod_periods",
        "/cod_periods",
        (
            "Cause-of-death periods (2-3 year windows).\n"
            "\n"
            'E.g. "2007-2009", "2010-2013", ..., "2022-2024".'
        ),
    ),
    (
        "srs_list_bulletin_years",
        "/bulletin_years",
        "Years with SRS Bulletin vital statistics (1997-2024, 2002 missing).",
    ),
    (
        "srs_available_periods",
        "/available_periods",
        "Temporal coverage for all SRS data types (life tables, CoD, bulletin).",
    ),
    (
        "srs_list_bulletin_indicators",
        "/bulletin_indicators",
        "Bulletin indicator codes for srs_query_bulletin: cbr, cdr, ngr, imr.",
    ),
    (
        "srs_list_stat_report_years",
        "/stat_report_years",
        "Years with SRS Statistical Report data (2011 onward).",
    ),
    (
        "srs_list_stat_report_indicators",
        "/stat_report_indicators",
        "Indicator codes for srs_query_stat_report, e.g. tfr, nmr, u5mr, sbr.",
    ),
    (
        "srs_life_expectancy_trend",
        "/life_expectancy_trend",
        (
            "National life expectancy at birth, 1970-75 to present (SRS Statement 1).\n"
            "\n"
            "Columns: period, mid_year, lifespan_at_birth by total/rural/urban\n"
            "and person/male/female."
        ),
    ),
    (
        "srs_list_mmr_periods",
        "/mmr_periods",
        'Three-year periods with maternal mortality ratio data, e.g. "2018-2020".',
    ),
    (
        "srs_list_nsso_years",
        "/nsso_years",
        "Years with SRS vital rates by NSSO natural division (sub-state regions).",
    ),
)
