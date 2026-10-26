import importlib
import json
import pkgutil
import subprocess
from concurrent.futures import ThreadPoolExecutor

import httpx
from fastmcp import FastMCP

from bharatvitals import tools
from bharatvitals.client import BharatVitalsClient
from bharatvitals.normalize import ForgivingArguments
from bharatvitals.tools._common import READ_ONLY

# each tools/<id>.py is a source; _-prefixed modules are helpers
MODULES = tuple(
    importlib.import_module(f"{tools.__name__}.{m.name}")
    for m in sorted(pkgutil.iter_modules(tools.__path__), key=lambda m: m.name)
    if not m.name.startswith("_")
)
_SOURCES = tuple(m.SOURCE for m in MODULES)

CONVENTIONS = """\
Conventions shared by every tool:
- State: a name or a two-letter code, case-insensitive, comma-separated ("Kerala,TN"). An unknown name is an error; <source>_list_states has the valid ones.
- India: "India" gives the national row where the source has one; a source without one says so.
- Year: comma-separated years or a range ("2015:2020").
- Sector: "total", "rural" or "urban".
- District: rows name it in a district column. Spellings follow each source, and a name can cover different areas across sources and years (Barddhaman split in 2017).
- Row tools return {source, complete, total_rows, offset, returned, rows}, 1000 rows per page unless limit is set (up to 10000). complete is false on a partial page: fetch next_offset before answering. warnings flag a partial page or rows that overlap (India with its states, several sexes or sectors); a note explains an empty result.
- Never sum rows unless a tool says they add up: results often mix national, state and subtotal rows, and SRS, CRS and MCCD values are not interchangeable.
- Errors carry the API's reason (bad value, or a filter the table cannot apply). Fix the argument and retry.
- If a tool reports an unreachable API, call bharatvitals_health."""

mcp = FastMCP(
    "bharatvitals",
    instructions="\n\n".join(
        [
            "India public health and demographic data. Tools are prefixed by source: "
            + ", ".join(f"{s}_*" for s in _SOURCES)
            + ". The sources measure different things and disagree, so pick by question:",
            "\n".join(f"- {m.LABEL}: {m.GUIDE}" for m in MODULES),
            CONVENTIONS,
        ]
    ),
)

mcp.add_middleware(ForgivingArguments())

_client = BharatVitalsClient({m.SOURCE: m.PACKAGE for m in MODULES})

for module in MODULES:
    module.register(mcp, _client)


def _probe(source: str) -> object:
    try:
        return _client.health(source)
    except (httpx.HTTPError, RuntimeError, OSError, subprocess.SubprocessError) as e:
        return {"error": str(e)}


@mcp.tool(annotations=READ_ONLY)
def bharatvitals_health() -> str:
    """Probe /health of every data API that is configured or has been called; one entry per source.

    Never starts an R backend; a source not yet used reports "not started".
    """
    with ThreadPoolExecutor(len(_SOURCES)) as pool:
        return json.dumps(dict(zip(_SOURCES, pool.map(_probe, _SOURCES))))


def main() -> None:
    import os

    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "http":
        host = os.environ.get("MCP_HOST", "127.0.0.1")
        port = int(os.environ.get("MCP_PORT", "9000"))
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
