"""Shared runtime for the bharatvitals MCP server.

Creates the single :class:`FastMCP` instance and the auto-starting
:class:`BharatVitalsClient`, and holds the request helper used by every tool
module. Tool modules import ``mcp`` (plus the helper and the API URL constants)
from here and register their tools with ``@mcp.tool()``; ``bharatvitals.server``
imports the tool modules to trigger that registration. No tool module is
imported here, so there are no import cycles.
"""

from __future__ import annotations

import os

from fastmcp import FastMCP

from bharatvitals.client import BharatVitalsClient

# Default base URLs, kept for signature compatibility with the vendored tool
# bodies (which pass them to ``_request_json``). ``BharatVitalsClient`` resolves
# the real endpoint and honours ``BHARATVITALS_<SOURCE>_URL`` overrides.
HMIS_API_URL = os.environ.get("BHARATVITALS_HMIS_URL", "http://127.0.0.1:8765")
MCCD_API_URL = os.environ.get("BHARATVITALS_MCCD_URL", "http://127.0.0.1:8585")
CONSUMPTION_API_URL = os.environ.get(
    "BHARATVITALS_CONSUMPTION_URL", "http://127.0.0.1:8795"
)
HEALTHSURVEY_API_URL = os.environ.get(
    "BHARATVITALS_HEALTHSURVEY_URL", "http://127.0.0.1:8685"
)
SRS_API_URL = os.environ.get("BHARATVITALS_SRS_URL", "http://127.0.0.1:8686")
CENSUS_API_URL = os.environ.get("BHARATVITALS_CENSUS_URL", "http://127.0.0.1:8895")
CRS_API_URL = os.environ.get("BHARATVITALS_CRS_URL", "http://127.0.0.1:8484")

# Outbound timeout for calls to the backend REST APIs.
REQUEST_TIMEOUT_SECONDS = int(os.environ.get("REQUEST_TIMEOUT_SECONDS", "30"))


# MCP transport configuration. Defaults preserve local stdio usage; set
# MCP_TRANSPORT=http (or streamable-http) to serve over HTTP behind a proxy.
MCP_TRANSPORT = os.environ.get("MCP_TRANSPORT", "stdio").strip().lower()
MCP_HOST = os.environ.get("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.environ.get("MCP_PORT", "9000"))
MCP_PATH = os.environ.get("MCP_PATH", "/mcp").strip() or "/mcp"


def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


MCP_STATELESS_HTTP = _env_flag("MCP_STATELESS_HTTP", True)
MCP_ALLOWED_HOSTS = [
    item.strip()
    for item in os.environ.get(
        "MCP_ALLOWED_HOSTS", "127.0.0.1:*,localhost:*,[::1]:*"
    ).split(",")
    if item.strip()
]

mcp = FastMCP(
    "bharatvitals",
    instructions=(
        "India health, mortality and survey data. Tools proxy auto-starting R "
        "Plumber APIs for HMIS, MCCD, Census of India, SRS, CRS and the NSS "
        "consumption and health surveys. Call api_health to probe backends and "
        "tool_guide to choose a tool."
    ),
)

# Human-readable labels per source, also consumed by scripts/build_site.py.
SOURCE_LABELS = {
    "hmis": "HMIS",
    "mccd": "MCCD",
    "srs": "SRS",
    "crs": "CRS",
    "census": "Census of India",
    "consumption": "Household Consumption Survey",
    "healthsurvey": "NSS Health Survey",
}

# Source id -> R package that ships the Plumber entry point, and the few
# packages whose entry point is not the conventional plumber/plumber.R.
PACKAGES = {
    "hmis": "hmisindia",
    "mccd": "mccdindia",
    "srs": "srsindia",
    "crs": "crsindia",
    "census": "censusindia",
    "consumption": "consumptionsurveyindia",
    "healthsurvey": "healthsurveyindia",
}
PLUMBER_PATHS = {
    "consumption": "server/api.R",
    "healthsurvey": "server/api.R",
}

client = BharatVitalsClient(PACKAGES, PLUMBER_PATHS)

# Exposed for scripts/build_site.py and re-exported by bharatvitals.server.
SOURCES = SOURCE_LABELS
LABELS = list(SOURCE_LABELS.values())


# Maps the api_name used by the vendored mcp_forall tool bodies onto a
# bharatvitals source id (see PACKAGES). Both the descriptive survey names and
# the backend hostnames are accepted.
_SOURCE_BY_API = {
    "hmisindia": "hmis",
    "mccdindia": "mccd",
    "censusindia": "census",
    "srsindia": "srs",
    "crsindia": "crs",
    "consumptionsurveyindia": "consumption",
    "consumption survey": "consumption",
    "healthsurveyindia": "healthsurvey",
    "health survey": "healthsurvey",
}


def _request_json(api_name: str, base_url: str, method: str, path: str,
                  *, params: dict | None = None, json: dict | None = None) -> dict:
    """Call a Plumber route through the auto-starting client and return JSON.

    ``base_url`` is accepted for signature compatibility with the vendored
    mcp_forall tools but is ignored; ``BharatVitalsClient`` resolves the URL.
    """
    source = _SOURCE_BY_API.get(api_name)
    if source is None:
        raise ValueError(f"Unknown API '{api_name}'")
    endpoint = "/" + path.lstrip("/")
    try:
        if method == "GET":
            payload = client.get(
                source,
                endpoint,
                _string_params(params),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        else:
            payload = client.post(
                source,
                endpoint,
                json,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
    except RuntimeError as exc:
        raise ValueError(f"{api_name} API unavailable: {exc}") from exc
    return payload if isinstance(payload, dict) else {"count": len(payload), "rows": payload}


def _string_params(params: dict | None) -> dict[str, str] | None:
    return {key: str(value) for key, value in (params or {}).items() if value is not None}


