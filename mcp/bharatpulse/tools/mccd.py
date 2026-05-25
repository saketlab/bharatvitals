import json
from typing import TYPE_CHECKING, Optional

from fastmcp import FastMCP

if TYPE_CHECKING:
    from bharatpulse.client import BharatPulseClient

_SOURCE = "mccd"


def _to_json(data: object) -> str:
    return json.dumps(data, indent=2)


def register(mcp: FastMCP, client: "BharatPulseClient") -> None:

    @mcp.tool()
    def mccd_list_states() -> str:
        """List all 37 canonical state/UT names in MCCD data.

        Includes "All States (Total)" national aggregate.
        """
        return _to_json(client.get(_SOURCE, "/states", {}))

    @mcp.tool()
    def mccd_list_causes(pattern: Optional[str] = None) -> str:
        """Search MCCD cause-of-death entries.

        Args:
            pattern: Case-insensitive regex on Cause_Of_Death or ICD10_Code.
                     E.g. "heart", "I20", "malaria". Empty = all causes.
        """
        return _to_json(client.get(_SOURCE, "/causes", {"pattern": pattern}))

    @mcp.tool()
    def mccd_list_chapters(category: Optional[str] = None) -> str:
        """ICD-10 chapters with epidemiological categories.

        Args:
            category: "Communicable", "NCD", "External", "Ill-defined",
                      or "Other". Empty = all chapters.
        """
        return _to_json(client.get(_SOURCE, "/chapters", {"category": category}))

    @mcp.tool()
    def mccd_query(
        table: str = "deaths",
        cause: Optional[str] = None,
        state: Optional[str] = None,
        year: Optional[str] = None,
        sex: Optional[str] = None,
    ) -> str:
        """Query MCCD cause-of-death data (36 states, 2008-2023, ICD-10 coded).

        Args:
            table: "deaths" (state-wise counts, Table 2),
                   "deaths_pct" (state-wise percentages, Table 3),
                   "cause" (by major cause/ICD chapter, Table 4),
                   "age" (India-level age-disaggregated, Table 5),
                   "subcause" (India-level detailed sub-cause, Table 6),
                   "state_subcause" (state + age disaggregated, Table 7).
            cause: Regex on Cause_Of_Death or ICD10_Code, e.g. "I20", "coronary".
                   Only for cause/subcause/state_subcause tables.
            state: Comma-separated state names, e.g. "Kerala,Tamil Nadu".
                   "All States (Total)" or "India" for national aggregate.
            year: Comma-separated years or range, e.g. "2015,2016" or "2015:2020".
            sex: "T" (total), "M" (male), or "F" (female).
        """
        return _to_json(
            client.get(
                _SOURCE,
                "/query",
                {
                    "table": table,
                    "cause": cause,
                    "state": state,
                    "year": year,
                    "sex": sex,
                },
            )
        )

    @mcp.tool()
    def mccd_categorize(
        table: str = "cause",
        cause: Optional[str] = None,
        state: Optional[str] = None,
        year: Optional[str] = None,
        sex: Optional[str] = None,
    ) -> str:
        """Like mccd_query but adds epidemiological category columns.

        Joins with ICD-10 chapter metadata to add "category"
        (Communicable/NCD/External/Ill-defined/Other) and "subcategory".

        Args:
            table: "cause", "subcause", or "state_subcause".
            cause: Regex on Cause_Of_Death or ICD10_Code.
            state: Comma-separated state names.
            year: Comma-separated years or range.
            sex: "T", "M", or "F".
        """
        return _to_json(
            client.get(
                _SOURCE,
                "/categorize",
                {
                    "table": table,
                    "cause": cause,
                    "state": state,
                    "year": year,
                    "sex": sex,
                },
            )
        )
