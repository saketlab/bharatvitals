import atexit
import os
import socket
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

_RETRY_AFTER = 60.0  # seconds


@dataclass
class _SourceServer:
    source_id: str
    pkg_name: str
    _proc: Optional[subprocess.Popen] = field(default=None, repr=False)  # type: ignore[type-arg]
    _url: Optional[str] = field(default=None, repr=False)
    _http: Optional[httpx.Client] = field(default=None, repr=False)
    _failed: Optional[tuple[float, str]] = field(default=None, repr=False)

    def _find_plumber_r(self) -> str:
        env_key = f"BHARATVITALS_{self.source_id.upper()}_PLUMBER_R"
        env_path = os.environ.get(env_key)
        if env_path and os.path.isfile(env_path):
            return env_path

        result = subprocess.run(
            [
                "Rscript",
                "--vanilla",
                "-e",
                f"cat(system.file('plumber', 'plumber.R', package='{self.pkg_name}'))",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        path = result.stdout.strip()
        if path and os.path.isfile(path):
            return path

        raise FileNotFoundError(
            f"plumber.R not found for '{self.source_id}' (R package: {self.pkg_name}). "
            f"Install the R package or set {env_key}."
        )

    @staticmethod
    def _free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    @staticmethod
    def _wait_healthy(url: str, timeout: float = 45.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                httpx.get(f"{url}/health", timeout=2.0)
                return True
            except Exception:
                time.sleep(0.75)
        return False

    def _start(self) -> str:
        plumber_r = self._find_plumber_r()
        port = self._free_port()
        self._proc = subprocess.Popen(
            [
                "Rscript",
                "--vanilla",
                "-e",
                f"plumber::plumb('plumber.R')$run(host='127.0.0.1', port={port}, quiet=TRUE)",
            ],
            cwd=os.path.dirname(plumber_r),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        atexit.register(self._proc.terminate)
        url = f"http://127.0.0.1:{port}"
        if not self._wait_healthy(url):
            self._proc.terminate()
            raise RuntimeError(
                f"Source '{self.source_id}' plumber API did not start within 45 s "
                f"(package: {self.pkg_name})."
            )
        return url

    def _resolve_url(self) -> str:
        if self._url is not None:
            return self._url
        if self._failed and time.monotonic() - self._failed[0] < _RETRY_AFTER:
            raise RuntimeError(self._failed[1])
        env_url = os.environ.get(f"BHARATVITALS_{self.source_id.upper()}_URL")
        try:
            self._url = env_url.rstrip("/") if env_url else self._start()
        except (OSError, RuntimeError, subprocess.SubprocessError) as e:
            # don't repeat a slow failed start on every call
            self._failed = (time.monotonic(), str(e))
            raise
        http = httpx.Client(timeout=120.0, headers={"X-Client": "mcp/bharatvitals"})
        atexit.register(http.close)
        self._http = http
        return self._url

    @property
    def attempted(self) -> bool:
        """True once a call has resolved or failed, or a URL is configured."""
        return (
            self._url is not None
            or self._failed is not None
            or f"BHARATVITALS_{self.source_id.upper()}_URL" in os.environ
        )

    def get(
        self,
        endpoint: str,
        params: dict[str, Any],
        timeout: Any = httpx.USE_CLIENT_DEFAULT,
    ) -> Any:
        url = self._resolve_url()
        clean = {k: v for k, v in params.items() if v is not None}
        resp = self._http.get(  # type: ignore[union-attr]
            f"{url}{endpoint}",
            params=clean,
            timeout=timeout,
        )
        if resp.is_error:
            # R puts the reason for bad input in the body
            raise RuntimeError(
                f"{self.source_id} API returned HTTP {resp.status_code}: {resp.text[:500]}"
            )
        try:
            return resp.json()
        except ValueError as e:
            raise RuntimeError(
                f"{self.source_id} API returned non-JSON: {resp.text[:500]}"
            ) from e


class BharatVitalsClient:
    def __init__(self, packages: dict[str, str]) -> None:
        """packages: source id -> R package that ships its plumber.R."""
        self._servers: dict[str, _SourceServer] = {
            sid: _SourceServer(source_id=sid, pkg_name=pkg)
            for sid, pkg in packages.items()
        }

    def get(
        self,
        source: str,
        endpoint: str,
        params: dict[str, Any],
        timeout: Any = httpx.USE_CLIENT_DEFAULT,
    ) -> Any:
        if source not in self._servers:
            raise KeyError(
                f"Unknown source '{source}'. Known: {', '.join(sorted(self._servers))}"
            )
        return self._servers[source].get(endpoint, params, timeout)

    def attempted(self, source: str) -> bool:
        return self._servers[source].attempted
