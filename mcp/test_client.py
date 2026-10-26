"""Run: uv run python test_client.py"""

import asyncio
import functools
import json
import os
import re
import stat
import tempfile
from pathlib import Path
from typing import Any

import httpx

from bharatvitals.client import _PORT_RANGE, _envelope, _SourceServer
from bharatvitals.normalize import _types

# sibling checkouts of the R packages, e.g. ~/github/hmisindia
R_SRC = Path(os.environ.get("BHARATVITALS_R_SRC", Path(__file__).resolve().parents[2]))


def plumber_path(pkg: str) -> Path:
    return R_SRC / pkg / "inst" / "plumber" / "plumber.R"


def _raises(fn: Any, message: str) -> None:
    try:
        fn()
    except RuntimeError as e:
        assert str(e) == message, e
    else:
        raise AssertionError("expected RuntimeError")


def test_failed_start_is_cached_and_health_never_starts_r() -> None:
    srv = _SourceServer(source_id="nosuch", pkg_name="nosuch")
    assert srv.health() == {"status": "not started; the first tool call starts it"}

    def boom() -> str:
        raise RuntimeError("boom")

    srv._start = boom  # type: ignore[method-assign]
    _raises(lambda: srv.get("/health", {}), "boom")
    srv._start = lambda: 1 / 0  # type: ignore[method-assign]  # the cooldown must skip it
    _raises(lambda: srv.get("/health", {}), "boom")
    srv._failed = (0.0, "boom")  # cooldown over: health still reports, never starts R
    assert srv.health() == {"error": "boom"}


def test_configured_url_skips_the_cooldown() -> None:
    srv = _SourceServer(source_id="nosuch", pkg_name="nosuch")
    srv._failed = (1e18, "old failure")  # far in the future: cooldown active
    os.environ["BHARATVITALS_NOSUCH_URL"] = "http://127.0.0.1:1/"
    try:
        assert srv._resolve_url() == "http://127.0.0.1:1"
        assert srv._failed is None
    finally:
        del os.environ["BHARATVITALS_NOSUCH_URL"]


def test_failed_start_reports_what_r_said() -> None:
    if os.name == "nt":
        return
    with tempfile.TemporaryDirectory() as d:
        fake = Path(d, "Rscript")
        fake.write_text(
            "#!/bin/sh\necho 'there is no package called plumber' >&2\nexit 1\n"
        )
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        plumber_r = Path(d, "plumber.R")
        plumber_r.touch()
        env = {
            "BHARATVITALS_RSCRIPT": str(fake),
            "BHARATVITALS_FAKE_PLUMBER_R": str(plumber_r),
        }
        os.environ.update(env)
        try:
            _SourceServer(source_id="fake", pkg_name="fake")._start()
            raise AssertionError("start should fail")
        except RuntimeError as e:
            assert "exit code 1" in str(e) and "no package called plumber" in str(e), e
        finally:
            for k in env:
                del os.environ[k]


def test_free_port_is_one_plumber_accepts() -> None:
    lo, hi = _PORT_RANGE
    assert all(lo <= _SourceServer._free_port() <= hi for _ in range(20))


def test_envelope_says_how_to_page_and_why_empty() -> None:
    page = _envelope([1, 2], httpx.Headers({"X-Total-Count": "5", "X-Offset": "1"}))
    assert page["total_rows"] == 5 and page["next_offset"] == 3 and "note" not in page
    past = _envelope([], httpx.Headers({"X-Total-Count": "5", "X-Offset": "9"}))
    assert "past the last row" in past["note"]
    last = _envelope([1], httpx.Headers({"X-Total-Count": "1"}))
    assert "next_offset" not in last and "note" not in last
    empty = _envelope([], httpx.Headers({"X-Total-Count": "0"}))
    assert empty["rows"] == [] and "No rows match" in empty["note"]
    # older APIs send no paging headers
    assert _envelope([1, 2], httpx.Headers())["total_rows"] == 2


def test_get_wraps_rows_but_not_objects() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if req.url.path == "/bad":
            return httpx.Response(400, json={"error": 'Unknown state "X".'})
        assert req.url.params["flag"] == "true"  # R's flag() reads lowercase
        return httpx.Response(200, json=[{"a": 1}], headers={"X-Total-Count": "1"})

    srv = _SourceServer(source_id="mock", pkg_name="mock")
    srv._url = "http://mock"
    srv._http = httpx.Client(transport=httpx.MockTransport(handler))
    assert srv.get("/health", {}) == {"status": "ok"}
    assert srv.get("/rows", {"flag": True, "skip": None})["rows"] == [{"a": 1}]
    try:
        srv.get("/bad", {})
        raise AssertionError("400 should raise")
    except RuntimeError as e:
        assert "mock rejected the call" in str(e) and "Unknown state" in str(e)


def test_health_must_come_from_our_package() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "ok", "package": "someone_else"})

    srv = _SourceServer(source_id="mock", pkg_name="mockindia")
    real = httpx.get
    httpx.get = lambda url, **kw: handler(httpx.Request("GET", url))  # type: ignore[assignment]
    try:
        assert not srv._healthy("http://127.0.0.1:1")
        srv.pkg_name = "someone_else"
        assert srv._healthy("http://127.0.0.1:1")
    finally:
        httpx.get = real  # type: ignore[assignment]


@functools.cache
def _plumber_routes(pkg: str) -> dict[str, set[str]] | None:
    """route -> @param names, parsed from the R package's plumber.R."""
    path = plumber_path(pkg)
    if not path.is_file():
        return None
    routes: dict[str, set[str]] = {}
    params: set[str] = set()
    for line in path.read_text().splitlines():
        if m := re.match(r"#\*\s*@param\s+([A-Za-z_][\w]*)", line):
            params.add(m.group(1))
        elif m := re.match(r"#\*\s*@get\s+(\S+)", line):
            routes[m.group(1)] = params | {"limit", "offset"}
            params = set()
        elif not line.startswith("#*"):
            params = set()
    return routes


def test_shared_plumber_header_has_not_drifted() -> None:
    # hmisindia, mccdindia and crsindia carry one copied block of request helpers
    blocks = {}
    for pkg in ("hmisindia", "mccdindia", "crsindia"):
        path = plumber_path(pkg)
        if not path.is_file():
            return
        text = path.read_text()
        start = text.index("`%||%` <- rlang::`%||%`")
        end = text.index("\n}\n", text.index("respond <- function(req, res, expr)")) + 3
        blocks[pkg] = text[start:end]
    assert len(set(blocks.values())) == 1, (
        "shared plumber.R helpers differ between packages"
    )


def test_llm_argument_mistakes_are_repaired() -> None:
    from bharatvitals.normalize import normalize

    string = {"anyOf": [{"type": "string"}, {"type": "null"}]}
    schema = {
        "properties": {
            k: string
            for k in (
                "state",
                "year",
                "indicator",
                "sex",
                "period",
                "from_date",
                "to_date",
                "sector",
                "geography",
                "cause",
            )
        }
        | {
            "limit": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
            "include_totals": {"type": "boolean"},
        },
        "required": ["indicator"],
    }
    cases = [
        ({"state": ["Kerala", "TN"]}, {"state": "Kerala,TN"}),
        ({"year": 2020}, {"year": "2020"}),
        ({"year": [2019, 2020]}, {"year": "2019,2020"}),
        ({"year": "2015-2020"}, {"year": "2015:2020"}),
        ({"year": "2015 to 2020"}, {"year": "2015:2020"}),
        ({"state": "all", "year": ""}, {}),
        ({"indicator": "all"}, {"indicator": "all"}),  # required: kept
        ({"states": "Kerala", "years": "2020"}, {"state": "Kerala", "year": "2020"}),
        (
            {"start_date": "2023-01", "end": "2023"},
            {"from_date": "2023-01", "to_date": "Dec 2023"},
        ),
        ({"from_date": "2023"}, {"from_date": "Jan 2023"}),
        (
            {"state": "Delhi NCT, J&K, Orissa, Kerala State"},
            {"state": "Delhi,Jammu & Kashmir,Odisha,Kerala"},
        ),
        ({"state": "all india"}, {"state": "India"}),
        ({"period": "2019-23"}, {"period": "2019-2023"}),
        ({"limit": 50000}, {"limit": 10000}),
        ({"limit": "20"}, {"limit": 20}),
        ({"include_totals": "yes"}, {"include_totals": True}),
        ({"sector": "Combined"}, {"sector": "total"}),
        ({"geography": "Districts"}, {"geography": "district"}),
        ({"sex": "Female"}, {"sex": "female"}),
        ({"bogus": 1}, {"bogus": 1}),  # left for validation to report
    ]
    for given, want in cases:
        assert normalize("srs_query_bulletin", given, schema) == want, (
            given,
            normalize("srs_query_bulletin", given, schema),
        )
    # a cause alone picks the cause table
    assert normalize(
        "mccd_query", {"sex": "female", "cause": "heart attack"}, schema
    ) == {
        "sex": "F",
        "cause": "myocardial infarction",
        "table": "cause",
    }
    periods = {"properties": {"period": string, "state": string}}
    assert normalize("srs_query_mmr", {"year": "2018:2020"}, periods) == {
        "period": "2018-2020"
    }
    search = {
        "properties": {
            "pattern": string,
            "match": {"type": "string", "enum": ["fixed", "regex", "fuzzy"]},
        }
    }
    assert normalize("hmis_list_indicators", {"pattern": "Immunization"}, search) == {
        "pattern": "(Immunization|immunisation)",
        "match": "regex",
    }


def test_dead_ends_name_the_tool_that_has_the_data() -> None:
    from bharatvitals.normalize import dead_end

    assert "census_population" in dead_end("census_query", {"state": "Kerala,India"})
    assert "census_population" in dead_end("census_query", {"year": "2021"})
    assert "srs_query_bulletin" in dead_end("crs_births", {"state": "India"})
    assert dead_end("crs_population_state", {"state": "India"}) is None
    assert dead_end("census_query", {"year": "2011", "state": "KL"}) is None


def test_district_argument_narrows_rows() -> None:
    from bharatvitals.normalize import narrow_to_district

    page = {
        "source": "crs",
        "complete": True,
        "total_rows": 2,
        "returned": 2,
        "rows": [
            {"state": "Goa", "district": "North Goa"},
            {"state": "Goa", "district": "South Goa"},
        ],
    }
    got = json.loads(narrow_to_district(json.dumps(page), "north goa"))
    assert [r["district"] for r in got["rows"]] == ["North Goa"] and got[
        "total_rows"
    ] == 1
    assert (
        "No district matches"
        in json.loads(narrow_to_district(json.dumps(page), "Pune"))["note"]
    )


def test_overlapping_rows_are_flagged() -> None:
    rows = [
        {"state": "India", "sector": "total"},
        {"state": "Kerala", "sector": "rural"},
        {"state": "M/O Defence", "sector": "total"},
    ]
    (warning,) = _envelope(rows, httpx.Headers())["warnings"]
    assert (
        "India with its states" in warning
        and "ministry" in warning
        and "sector rural, total" in warning
    )
    assert "warnings" not in _envelope(
        [{"state": "Kerala", "sector": "total"}], httpx.Headers()
    )


def test_unrepairable_arguments_get_a_short_fixable_error() -> None:
    from fastmcp import Client

    from bharatvitals import server

    async def run() -> str:
        async with Client(server.mcp) as c:
            r = await c.call_tool(
                "census_query",
                {"year": "two thousand", "bogus": 1},
                raise_on_error=False,
            )
            return r.content[0].text

    text = asyncio.run(run())
    assert (
        "Invalid arguments for census_query" in text
        and "Valid parameters: year" in text
    ), text
    assert "pydantic" not in text and "errors.pydantic.dev" not in text, text


def test_api_errors_name_tools_not_r_functions() -> None:
    from bharatvitals.client import _api_error

    body = {
        "error": '"Kerla" is not a recognized state name.\nℹ Run `list_states()` to see valid names.'
    }
    msg = _api_error("srs", httpx.Response(400, json=body))
    assert "srs_list_states" in msg and "list_states()" not in msg and "ℹ" not in msg, (
        msg
    )
    route = _api_error(
        "crs", httpx.Response(400, json={"error": "Use a code from /states."})
    )
    assert "crs_list_states" in route, route
    assert "server fault" in _api_error(
        "hmis", httpx.Response(500, json={"error": "boom"})
    )


def _sample(schema: dict[str, Any]) -> Any:
    kinds = _types(schema)
    return 1 if "integer" in kinds else True if "boolean" in kinds else "x"


def test_every_tool_runs_and_matches_its_route() -> None:
    from fastmcp import Client

    from bharatvitals import server

    calls: list[tuple[str, str, dict[str, Any]]] = []

    def fake_get(
        source: str, endpoint: str, params: dict[str, Any], timeout: Any = None
    ) -> Any:
        calls.append((source, endpoint, params))
        return {"total_rows": 0, "offset": 0, "returned": 0, "rows": []}

    real_get = server._client.get
    server._client.get = fake_get  # type: ignore[method-assign]
    try:

        async def run() -> list[str]:
            async with Client(server.mcp) as c:
                tools = await c.list_tools()
                for t in tools:
                    schema = t.inputSchema
                    args = {
                        k: _sample(schema["properties"][k])
                        for k in schema.get("required", [])
                    }
                    r = await c.call_tool(t.name, args, raise_on_error=False)
                    assert not r.is_error, (t.name, r.content)
                    assert t.annotations and t.annotations.readOnlyHint, t.name
                    assert t.description, t.name
                for res in await c.list_resources():
                    await c.read_resource(res.uri)
                return [t.name for t in tools]

        names = asyncio.run(run())
    finally:
        server._client.get = real_get  # type: ignore[method-assign]

    sources = {m.SOURCE: m.PACKAGE for m in server.MODULES}
    for name in names:
        assert name.split("_")[0] in {*sources, "bharatvitals"}, name
    checked = 0
    for source, endpoint, params in calls:
        routes = _plumber_routes(sources[source])
        if routes is None:
            continue
        route = next(
            (r for r in routes if re.fullmatch(re.sub(r"<\w+>", "[^/]+", r), endpoint)),
            None,
        )
        assert route, f"{source}{endpoint} is not a plumber route"
        unknown = set(params) - routes[route]
        assert not unknown, (
            f"{source}{endpoint} sends {unknown}; plumber takes {routes[route]}"
        )
        checked += 1
    print(
        f"  {len(names)} tools ran; {checked} calls checked against plumber.R under {R_SRC}"
    )


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
