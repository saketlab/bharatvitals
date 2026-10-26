import re
from typing import TYPE_CHECKING, Any, Literal, Optional

from fastmcp import FastMCP

from bharatvitals.tools._common import READ_ONLY, to_json

if TYPE_CHECKING:
    from bharatvitals.client import BharatVitalsClient

SOURCE = "mccd"
PACKAGE = "mccdindia"
LABEL = "MCCD"
GUIDE = (
    "Use for ICD-10 detail on medically certified deaths, 36 states, 2008-2024 "
    "(most tables end in 2023). "
    "Certified deaths are a minority, mostly in hospitals, so MCCD shares are "
    "not population cause-of-death shares; SRS has those. Start with "
    "mccd_list_tables, then mccd_list_causes or mccd_list_chapters, then mccd_query."
)


def register(mcp: FastMCP, client: "BharatVitalsClient") -> None:
    def get(endpoint: str, params: dict[str, Any]) -> str:
        return to_json(client.get(SOURCE, endpoint, params))

    def query(endpoint: str, params: dict[str, Any]) -> str:
        found = client.get(SOURCE, endpoint, params)
        cause = params.get("cause")
        # a cause that matches no table returns the closest causes
        if (
            cause
            and not found["rows"]
            and not client.get(SOURCE, "/causes", {"pattern": cause})["rows"]
        ):
            words = "|".join(re.findall(r"[a-z]{4,}", cause.lower()))
            hits = (
                client.get(SOURCE, "/causes", {"pattern": words, "limit": 8})["rows"]
                if words
                else []
            )
            names = "; ".join(
                f"{r['Cause_Of_Death']} ({r['ICD10_Code']})" for r in hits
            )
            found["note"] = f"No cause matches {cause!r}." + (
                f" Causes sharing its words: {names}."
                if names
                else " Search mccd_list_causes with one medical word."
            )
        return to_json(found)

    @mcp.tool(annotations=READ_ONLY)
    def mccd_list_states() -> str:
        """MCCD states/UTs with two-letter codes (state_name, state_abbr).

        Pass state="India" in other tools for the national row.
        """
        return get("/states", {})

    @mcp.tool(annotations=READ_ONLY)
    def mccd_list_tables() -> str:
        """MCCD tables: what each holds, has_state, has_age_group, first_year and last_year.

        Check this before mccd_query; tables end in different years.
        """
        return get("/tables", {})

    @mcp.tool(annotations=READ_ONLY)
    def mccd_list_causes(
        pattern: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """Search MCCD causes of death; returns Cause_Of_Death and ICD10_Code.

        Args:
            pattern: Case-insensitive regex on Cause_Of_Death or ICD10_Code,
                     e.g. "heart", "I20", "malaria". None = all causes.
            limit: Rows per page, 1-10000 (default 1000).
            offset: Rows to skip; pass next_offset from the previous result.
        """
        return get("/causes", {"pattern": pattern, "limit": limit, "offset": offset})

    @mcp.tool(annotations=READ_ONLY)
    def mccd_list_chapters(category: Optional[str] = None) -> str:
        """ICD-10 chapters with ICD range, category and subcategory.

        Args:
            category: "Communicable", "NCD", "External", "Ill-defined",
                      or "Other". None = all chapters.
        """
        return get("/chapters", {"category": category})

    @mcp.tool(annotations=READ_ONLY)
    def mccd_query(
        table: Literal[
            "deaths",
            "deaths_pct",
            "cause",
            "age",
            "subcause",
            "state_subcause",
            "state_age_pct",
            "trend",
            "trend_pct",
            "age_pct",
            "age_over_pct",
        ] = "deaths",
        cause: Optional[str] = None,
        state: Optional[str] = None,
        year: Optional[str] = None,
        sex: Literal["T", "M", "F"] = "T",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """Medically certified deaths by table, ICD-10 coded; years per table in mccd_list_tables.

        Rows mix levels: level is "total" (ALL CAUSES), "chapter" or "cause",
        and cause rows include group subtotals, so never sum rows. Percent
        tables are shares, not counts.

        Args:
            table: "deaths" (default; state x sex, all causes, Table 2),
                   "deaths_pct" (state x sex, percent),
                   "cause" (state x cause x sex, Table 4),
                   "age" (India x cause x sex x age, Table 5),
                   "subcause" (India x detailed sub-cause x age, Table 6),
                   "state_subcause" (state x sub-cause x age, Table 7),
                   "state_age_pct", "trend", "trend_pct", "age_pct", "age_over_pct".
                   Tables without a state column reject state; tables without
                   a cause breakdown reject cause.
            cause: Regex on Cause_Of_Death or ICD10_Code in medical wording, e.g.
                   "myocardial infarction" or "I21"; mccd_list_causes finds it.
            state: Comma-separated state names or two-letter codes, e.g. "Kerala,TN".
                   "India" = national row.
            year: Comma-separated years or a range, e.g. "2015,2016" or "2015:2020".
            sex: "T" (total, default), "M" or "F". M and F add up to T; never sum sexes.
            limit: Rows per page, 1-10000 (default 1000).
            offset: Rows to skip; pass next_offset from the previous result.
        """
        return query(
            "/query",
            {
                "table": table,
                "cause": cause,
                "state": state,
                "year": year,
                "sex": sex,
                "limit": limit,
                "offset": offset,
            },
        )

    @mcp.tool(annotations=READ_ONLY)
    def mccd_categorize(
        table: Literal["cause", "subcause", "state_subcause"] = "cause",
        cause: Optional[str] = None,
        state: Optional[str] = None,
        year: Optional[str] = None,
        sex: Literal["T", "M", "F"] = "T",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """Like mccd_query, plus category (Communicable/NCD/External/Ill-defined/Other) and subcategory.

        Args:
            table: "cause" (default; has state), "subcause" (India only), or
                   "state_subcause".
            cause: Regex on Cause_Of_Death or ICD10_Code.
            state: Comma-separated state names or two-letter codes; "India" = national row.
            year: Comma-separated years or a range, e.g. "2015:2020".
            sex: "T" (default), "M" or "F". M and F add up to T; never sum sexes.
            limit: Rows per page, 1-10000 (default 1000).
            offset: Rows to skip; pass next_offset from the previous result.
        """
        return query(
            "/categorize",
            {
                "table": table,
                "cause": cause,
                "state": state,
                "year": year,
                "sex": sex,
                "limit": limit,
                "offset": offset,
            },
        )
