import atexit
import glob
import json
import os
import random
import re
import shutil
import socket
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

_RETRY_AFTER = 60.0  # seconds
_START_TIMEOUT = 45.0  # seconds
# plumber's findPort() refuses ports outside this range
_PORT_RANGE = (1024, 49151)
# the API caps limit at 10000
DEFAULT_LIMIT = 1000


def _find_rscript() -> str:
    configured = os.environ.get("BHARATVITALS_RSCRIPT", "").strip()
    if configured:
        found = configured if os.path.isfile(configured) else shutil.which(configured)
        if not found:
            raise FileNotFoundError(f"BHARATVITALS_RSCRIPT not found: {configured}")
        return os.path.abspath(found)
    found = shutil.which("Rscript")
    if found:
        return found
    # Windows installers don't put R on PATH
    roots = [os.environ.get("R_HOME", "")]
    roots += glob.glob(
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "R", "R-*")
    )
    for root in sorted(filter(None, roots), reverse=True):
        for sub in ("bin", os.path.join("bin", "x64")):
            exe = os.path.join(root, sub, "Rscript.exe")
            if os.path.isfile(exe):
                return exe
    raise FileNotFoundError(
        "Rscript not found. Install R and put it on PATH, or set BHARATVITALS_RSCRIPT."
    )


def _envelope(
    rows: list[Any], headers: httpx.Headers, source: str = ""
) -> dict[str, Any]:
    """Wrap a page of rows with the total and the next offset."""
    total = int(headers.get("x-total-count", len(rows)))
    offset = int(headers.get("x-offset", 0))
    complete = offset == 0 and len(rows) >= total
    out: dict[str, Any] = {
        "source": source,
        "complete": complete,
        "total_rows": total,
        "offset": offset,
        "returned": len(rows),
    }
    if not source:
        del out["source"]
    warnings = _mixed(rows)
    if offset + len(rows) < total:
        out["next_offset"] = offset + len(rows)
        warnings.insert(
            0,
            (
                f"Partial result: rows {offset + 1}-{offset + len(rows)} of {total}. Fetch "
                f"offset={offset + len(rows)} or narrow the filters before answering."
            ),
        )
    if warnings:
        out["warnings"] = warnings
    if not rows and total:
        out["note"] = f"offset {offset} is past the last row; total_rows is {total}."
    elif not rows:
        out["note"] = (
            "No rows match. The filters are valid, so the source has no data for them; "
            "its list or coverage tool shows the years and places it has."
        )
    out["rows"] = rows
    return out


@dataclass
class _SourceServer:
    source_id: str
    pkg_name: str
    _url: Optional[str] = field(default=None, repr=False)
    _http: Optional[httpx.Client] = field(default=None, repr=False)
    _failed: Optional[tuple[float, str]] = field(default=None, repr=False)
    # concurrent first calls must start one R process
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def _env(self) -> str:
        return f"BHARATVITALS_{self.source_id.upper()}"

    @staticmethod
    def _free_port() -> int:
        for _ in range(100):
            port = random.randint(*_PORT_RANGE)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", port))
                except OSError:
                    continue
            return port
        raise OSError(f"No free port in {_PORT_RANGE[0]}-{_PORT_RANGE[1]}.")

    def _healthy(self, url: str) -> bool:
        try:
            r = httpx.get(f"{url}/health", timeout=2.0)
            # another server may answer on this port
            return r.status_code == 200 and r.json().get("package") == self.pkg_name
        except (httpx.HTTPError, ValueError):
            return False

    def _start(self) -> str:
        rscript = _find_rscript()
        port = self._free_port()
        env_path = os.environ.get(f"{self._env}_PLUMBER_R")
        where = (
            json.dumps(env_path)
            if env_path
            else f"system.file('plumber', 'plumber.R', package = '{self.pkg_name}')"
        )
        # censusindia routes call package internals
        script = (
            f"f <- {where}; if (!nzchar(f) || !file.exists(f)) "
            f"stop('plumber.R not found; install {self.pkg_name} or set {self._env}_PLUMBER_R'); "
            f"plumber::pr(f, envir = new.env(parent = asNamespace('{self.pkg_name}')))"
            f"$run(host = '127.0.0.1', port = {port}, quiet = TRUE)"
        )
        # stdout logs every request and is dropped; stderr keeps a bounded tail
        proc = subprocess.Popen(
            [rscript, "--vanilla", "-e", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
        )
        tail: deque[str] = deque(maxlen=40)
        reader = threading.Thread(target=tail.extend, args=(proc.stderr,), daemon=True)
        reader.start()
        atexit.register(proc.terminate)
        url = f"http://127.0.0.1:{port}"
        deadline = time.monotonic() + _START_TIMEOUT
        while time.monotonic() < deadline and proc.poll() is None:
            if self._healthy(url):
                return url
            time.sleep(0.2)
        proc.terminate()
        proc.wait()
        reader.join(timeout=2.0)
        output = "".join(tail).strip()[-2000:]
        raise RuntimeError(
            f"Source '{self.source_id}' plumber API did not start within "
            f"{_START_TIMEOUT:.0f} s (package: {self.pkg_name}, exit code "
            f"{proc.returncode})." + (f" R said: {output}" if output else "")
        )

    def _resolve_url(self) -> str:
        if self._url is not None:
            return self._url
        with self._lock:
            return self._url or self._resolve_locked()

    def _resolve_locked(self) -> str:
        env_url = os.environ.get(f"{self._env}_URL")
        # a configured URL starts no R, so no cooldown
        if (
            not env_url
            and self._failed
            and time.monotonic() - self._failed[0] < _RETRY_AFTER
        ):
            raise RuntimeError(self._failed[1])
        try:
            self._url = env_url.rstrip("/") if env_url else self._start()
        except (OSError, RuntimeError, subprocess.SubprocessError) as e:
            # don't repeat a slow failed start on every call
            self._failed = (time.monotonic(), str(e))
            raise
        self._failed = None
        http = httpx.Client(timeout=120.0, headers={"X-Client": "mcp/bharatvitals"})
        atexit.register(http.close)
        self._http = http
        return self._url

    def health(self) -> Any:
        """Probe /health of a configured or running API; never starts R."""
        if self._url is None and f"{self._env}_URL" not in os.environ:
            if self._failed:
                return {"error": self._failed[1]}
            return {"status": "not started; the first tool call starts it"}
        return self.get("/health", {}, timeout=10.0)

    def get(
        self,
        endpoint: str,
        params: dict[str, Any],
        timeout: Any = httpx.USE_CLIENT_DEFAULT,
    ) -> Any:
        url = self._resolve_url()
        clean = {k: v for k, v in params.items() if v is not None}
        if "limit" in params and params["limit"] is None:
            clean["limit"] = DEFAULT_LIMIT
        resp = self._http.get(  # type: ignore[union-attr]
            f"{url}{endpoint}",
            params=clean,
            timeout=timeout,
        )
        if resp.is_error:
            raise RuntimeError(_api_error(self.source_id, resp))
        try:
            data = resp.json()
        except ValueError as e:
            raise RuntimeError(
                f"{self.source_id} API returned non-JSON: {resp.text[:500]}"
            ) from e
        return (
            _envelope(data, resp.headers, self.source_id)
            if isinstance(data, list)
            else data
        )


# columns whose different values are different slices of the same total
_SLICE_COLUMNS = ("sector", "Sex", "sex", "category", "level")


def _mixed(rows: list[Any]) -> list[str]:
    """Warnings for rows that overlap, so that summing them double counts."""
    dicts = [r for r in rows if isinstance(r, dict)]
    states = {r["state"] for r in dicts if r.get("state")}
    found = []
    if "India" in states and len(states) > 1:
        found.append("India with its states")
    if any(str(s).startswith("M/O ") for s in states):
        found.append("ministry rows reported outside the states")
    for col in _SLICE_COLUMNS:
        values = sorted({str(r[col]) for r in dicts if r.get(col) is not None})
        if len(values) > 1:
            found.append(f"{col} {', '.join(values[:6])}")
    if not found:
        return []
    return [
        f"Rows mix {'; '.join(found)}. Filter to one of each before summing or comparing."
    ]


# R messages name R functions and API routes; the model can only call tools
_R_HINT = re.compile(r"`?\b((?:list|available)_[a-z_]+)\(\)`?")
_ROUTE_HINT = re.compile(
    r"(?<![\w/])/(states|districts|indicators|tables|datasets|nsso_divisions)\b"
)


def _api_error(source: str, resp: httpx.Response) -> str:
    try:
        msg = str(resp.json().get("error", resp.text))
    except (ValueError, AttributeError):
        msg = resp.text
    msg = " ".join(msg.replace("ℹ", "").replace("✖", "").split())[:600]
    msg = _R_HINT.sub(lambda m: f"{source}_{m.group(1)}", msg)
    msg = _ROUTE_HINT.sub(lambda m: f"{source}_list_{m.group(1)}", msg)
    if resp.status_code < 500:
        return f"{source} rejected the call: {msg} Fix the argument and retry."
    return (
        f"{source} API failed (HTTP {resp.status_code}): {msg} This is a server fault, "
        "not your arguments; call bharatvitals_health."
    )


class BharatVitalsClient:
    def __init__(self, packages: dict[str, str]) -> None:
        """packages: source id -> R package that ships its plumber.R."""
        self._servers: dict[str, _SourceServer] = {
            sid: _SourceServer(source_id=sid, pkg_name=pkg)
            for sid, pkg in packages.items()
        }

    def _server(self, source: str) -> _SourceServer:
        if source not in self._servers:
            raise KeyError(
                f"Unknown source '{source}'. Known: {', '.join(sorted(self._servers))}"
            )
        return self._servers[source]

    def get(
        self,
        source: str,
        endpoint: str,
        params: dict[str, Any],
        timeout: Any = httpx.USE_CLIENT_DEFAULT,
    ) -> Any:
        return self._server(source).get(endpoint, params, timeout)

    def health(self, source: str) -> Any:
        return self._server(source).health()
