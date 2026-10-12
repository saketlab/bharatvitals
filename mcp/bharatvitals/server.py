import importlib
import json
import pkgutil
import subprocess
from concurrent.futures import ThreadPoolExecutor

import httpx
from fastmcp import FastMCP

from bharatvitals import tools
from bharatvitals.client import BharatVitalsClient

# each tools/<id>.py is a source; _-prefixed modules are helpers
MODULES = tuple(
    importlib.import_module(f"{tools.__name__}.{m.name}")
    for m in sorted(pkgutil.iter_modules(tools.__path__), key=lambda m: m.name)
    if not m.name.startswith("_")
)
_SOURCES = tuple(m.SOURCE for m in MODULES)

mcp = FastMCP(
    "bharatvitals",
    instructions=" ".join(
        [
            "India public health and demographic data.",
            "Tools prefixed by source: " + ", ".join(f"{s}_*" for s in _SOURCES) + ".",
            *(f"{m.LABEL}: {m.GUIDE}" for m in MODULES),
            "If a tool reports an unreachable API, call bharatvitals_health.",
        ]
    ),
)

_client = BharatVitalsClient({m.SOURCE: m.PACKAGE for m in MODULES})

for module in MODULES:
    module.register(mcp, _client)


def _probe(source: str) -> object:
    # ponytail: unprobed local sources stay down; health never launches R
    if not _client.attempted(source):
        return {"status": "not started; the first tool call starts it"}
    try:
        return _client.get(source, "/health", {}, timeout=10.0)
    except (httpx.HTTPError, RuntimeError, OSError, subprocess.SubprocessError) as e:
        return {"error": str(e)}


@mcp.tool()
def bharatvitals_health() -> str:
    """Probe /health of every data API that is configured or has been called; one entry per source."""
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
