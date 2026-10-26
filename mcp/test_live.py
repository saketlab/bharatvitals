"""Run: uv run python test_live.py

Calls every tool against real R APIs; needs R and each source's R package.
Starts each API from the plumber.R checkout next to this repo when present;
BHARATVITALS_<SOURCE>_URL points a source at a running API instead.
"""

import asyncio
import json
import os
import sys
from typing import Any

from fastmcp import Client

from bharatvitals import server
from test_client import plumber_path

# read at first call, so setting them after import works
for module in server.MODULES:
    if plumber_path(module.PACKAGE).is_file():
        os.environ.setdefault(
            f"BHARATVITALS_{module.SOURCE.upper()}_PLUMBER_R",
            str(plumber_path(module.PACKAGE)),
        )

IND = "Institutional Deliveries conducted (Including C-Sections)"
# every tool, with arguments that return rows
OK = {
    "bharatvitals_health": {},
    "hmis_list_states": {},
    "hmis_list_districts": {"state": "KL"},
    "hmis_list_indicators": {"pattern": "measles", "limit": 3},
    "hmis_query": {
        "indicator": IND,
        "state": "Kerala,TN",
        "sector": "total",
        "category": "Total",
        "from_date": "2023-01",
        "to_date": "Mar 2023",
    },
    "hmis_detect_periodicity": {"indicator": IND, "state": "KL"},
    "hmis_decompose_series": {"indicator": IND, "state": "India", "limit": 3},
    "mccd_list_states": {},
    "mccd_list_tables": {},
    "mccd_list_causes": {"pattern": "malaria"},
    "mccd_list_chapters": {"category": "ncd"},
    "mccd_query": {
        "table": "cause",
        "cause": "I2",
        "state": "India,KL",
        "year": "2019:2020",
        "sex": "T",
        "limit": 5,
    },
    "mccd_categorize": {"cause": "B5", "state": "MH", "year": "2020"},
    "crs_list_states": {},
    "crs_list_tables": {},
    "crs_available_years": {"table": "5"},
    "crs_vital_rates": {"year": "2020", "state": "KL,BR"},
    "crs_adjusted_events": {"year": "2019", "state": "UP"},
    "crs_births": {"year": "2018:2020", "state": "Goa"},
    "crs_deaths": {"year": "2020", "state": "goa"},
    "crs_infant_deaths": {"year": "2020", "state": "GA"},
    "crs_still_births": {"year": "2020", "state": "GA"},
    "crs_registration": {"year": "2019", "state": "Bihar"},
    "crs_deaths_by_age": {"year": "2020", "state": "KL"},
    "crs_district_births": {"year": "2020", "state": "GA"},
    "crs_district_deaths": {"year": "2020", "state": "GA"},
    "crs_district_infant_deaths": {"year": "2020", "state": "GA"},
    "crs_district_still_births": {"year": "2020", "state": "GA"},
    "crs_population_state": {"year": "2025", "state": "KL"},
    "crs_population_district": {
        "year": "2026",
        "state": "GA",
        "boundary": "census2011",
    },
    "census_list_states": {},
    "census_list_geographies": {},
    "census_list_variables": {"year": 2011, "geography": "state"},
    "census_search_variables": {"pattern": "literacy"},
    "census_query": {
        "year": 2011,
        "geography": "district",
        "state": "KL",
        "variables": "population",
    },
    "census_population": {"year": "2021:2026", "state": "India,KL"},
    "census_languages": {"limit": 2},
    "census_sc_st": {"category": "SC", "state": "GA"},
    "census_list_datasets": {},
    "census_dataset": {"name": "census_2011_tribes", "state": "GA", "limit": 2},
    "srs_list_states": {},
    "srs_list_life_table_periods": {},
    "srs_list_cod_tables": {},
    "srs_list_cod_periods": {},
    "srs_list_bulletin_years": {},
    "srs_available_periods": {},
    "srs_list_bulletin_indicators": {},
    "srs_list_stat_report_years": {},
    "srs_list_stat_report_indicators": {},
    "srs_life_expectancy_trend": {},
    "srs_summary_indicators": {"state": "KL", "sector": "total"},
    "srs_epi_transition": {},
    "srs_arriaga_decompose": {
        "state": "KL",
        "period1": "2007-2011",
        "period2": "2019-2023",
    },
    "srs_query_life_table": {
        "state": "India",
        "period": "2019-2023",
        "sector": "urban",
        "limit": 3,
    },
    "srs_query_cod": {"table": "sample_units", "state": "KL"},
    "srs_query_bulletin": {
        "indicator": "imr",
        "state": "India,KL",
        "year": "2019:2020",
        "sector": "total",
    },
    "srs_query_stat_report": {
        "indicator": "tfr,u5mr",
        "state": "Bihar",
        "year": "2020",
    },
    "srs_list_mmr_periods": {},
    "srs_query_mmr": {"state": "India,AS", "limit": 4},
    "srs_list_nsso_years": {},
    "srs_list_nsso_divisions": {"state": "BR"},
    "srs_query_nsso_regions": {"state": "BR", "year": "2020"},
    "srs_list_nsso_districts": {"state": "BR", "division": "Northern", "limit": 3},
}
# calls that must fail, and text the error must contain
BAD = {
    "hmis_query": ({"indicator": IND, "state": "Atlantis"}, "Unknown state"),
    "hmis_detect_periodicity": (
        {"indicator": IND, "state": "KL", "sector": "public", "category": "nope"},
        "No rows",
    ),
    "mccd_query": ({"table": "age", "state": "KL"}, "not applicable"),
    "crs_births": ({"state": "India"}, "srs_query_bulletin"),
    "srs_query_bulletin": ({"sector": "suburban"}, "sector"),
    "census_query": ({"year": 2021}, "2011"),
}


async def main() -> int:
    fails = 0

    def check(good: bool, label: str) -> None:
        nonlocal fails
        fails += not good
        if not good or not label.startswith("code "):
            print("ok  " if good else "FAIL", label)

    async with Client(server.mcp) as c:

        async def call(name: str, args: dict) -> tuple[bool, Any]:
            """(is_error, parsed result or error text)"""
            r = await c.call_tool(name, args, raise_on_error=False)
            text = r.content[0].text if r.content else ""
            return r.is_error, text if r.is_error else json.loads(text)

        # start backends in parallel; each has its own lock
        await asyncio.gather(
            *(call(f"{m.SOURCE}_list_states", {}) for m in server.MODULES)
        )
        missing = {t.name for t in await c.list_tools()} - set(OK)
        check(not missing, f"every tool exercised {sorted(missing) or ''}")
        for name, args in OK.items():
            err, data = await call(name, args)
            empty = isinstance(data, dict) and data.get("returned") == 0
            check(
                not err and not empty, name if not err else f"{name}: {str(data)[:120]}"
            )
        for name, (args, want) in BAD.items():
            err, data = await call(name, args)
            check(err and want in data, f"{name} rejects {args}")
        # paging: two pages of 2 rows are the first 4 rows
        _, page1 = await call("crs_births", {"year": "2020", "limit": 2})
        _, page2 = await call(
            "crs_births", {"year": "2020", "limit": 2, "offset": page1["next_offset"]}
        )
        _, first4 = await call("crs_births", {"year": "2020", "limit": 4})
        check(
            page1["rows"] + page2["rows"] == first4["rows"],
            "next_offset pages through crs_births",
        )
        for res in await c.list_resources():
            check(bool(await c.read_resource(res.uri)), f"resource {res.uri}")
        # every two-letter code resolves to its own state
        _, states = await call("crs_list_states", {})
        for row in states["rows"]:
            err, data = await call(
                "crs_births", {"year": "2020", "state": row["state_abbr"]}
            )
            got = None if err else {x["state"] for x in data["rows"]}
            check(
                got is not None and got <= {row["state_name"]},
                f"code {row['state_abbr']} {got}",
            )
        print(len(states["rows"]), "state codes checked")
    print("failures:", fails)
    return fails


if __name__ == "__main__":
    sys.exit(1 if asyncio.run(main()) else 0)
