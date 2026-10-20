"""bharatvitals MCP server entry point.

Imports the vendored tool modules (each registers its tools on the shared
``mcp`` instance in :mod:`bharatvitals.runtime`) and the extra modules under
``bharatvitals.tools``, then exposes the MCP endpoint. The console script
``bharatvitals-mcp`` points here, so ``main`` and ``mcp`` must stay importable.
"""

from __future__ import annotations

import importlib
import pkgutil

from starlette.responses import JSONResponse

from bharatvitals import tools as _tools
from bharatvitals.runtime import (
    LABELS,
    MCP_ALLOWED_HOSTS,
    MCP_HOST,
    MCP_PATH,
    MCP_PORT,
    MCP_STATELESS_HTTP,
    MCP_TRANSPORT,
    REQUEST_TIMEOUT_SECONDS,
    SOURCES,
    client,
    mcp,
)

# Importing these registers the vendored tools on ``mcp``. The star-imports also
# keep ``bharatvitals.server.query_hmis`` and friends working for callers/tests.
from bharatvitals.tools.census import *  # noqa: F401,F403
from bharatvitals.tools.hmis import *  # noqa: F401,F403
from bharatvitals.tools.mccd import *  # noqa: F401,F403
from bharatvitals.tools.meta import *  # noqa: F401,F403
from bharatvitals.tools.srs import *  # noqa: F401,F403
from bharatvitals.tools.surveys import *  # noqa: F401,F403

# Discover every module under bharatvitals.tools. Vendored modules registered
# their tools on import; the extras (crs, srs_resources) expose register().
MODULES = tuple(
    importlib.import_module(f"{_tools.__name__}.{info.name}")
    for info in sorted(pkgutil.iter_modules(_tools.__path__), key=lambda i: i.name)
    if not info.name.startswith("_")
)
for _module in MODULES:
    _register = getattr(_module, "register", None)
    if _register is not None:
        _register(mcp, client)


@mcp.custom_route("/health", methods=["GET"])
async def _health(request):
    """Liveness probe for supervisors and reverse proxies."""
    return JSONResponse({"status": "ok", "package": "bharatvitals"})


def main() -> None:
    """Entry point used by the ``bharatvitals-mcp`` console script."""
    if MCP_TRANSPORT in ("http", "streamable-http"):
        try:
            mcp.run(
                transport="streamable-http",
                host=MCP_HOST,
                port=MCP_PORT,
                path=MCP_PATH,
                stateless_http=MCP_STATELESS_HTTP,
                allowed_hosts=MCP_ALLOWED_HOSTS or None,
            )
        except TypeError:
            mcp.run(transport="streamable-http", host=MCP_HOST, port=MCP_PORT)
    elif MCP_TRANSPORT == "stdio":
        mcp.run(transport="stdio")
    else:
        raise ValueError('MCP_TRANSPORT must be "stdio" or "streamable-http"')


if __name__ == "__main__":
    main()
