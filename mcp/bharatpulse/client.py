import atexit
import os
import socket
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

SOURCE_REGISTRY: dict[str, str] = {
    "hmis": "hmisindia",
    "nfhs5": "nfhs5",
    "nfhs4": "nfhs4",
    "srs": "srsindia",
    "mccd": "mccdindia",
    "census": "censusindia",
    "crs": "crsindia",
    "lasi": "lasi",
    "healthsurvey": "healthsurveyindia",
    "consumption": "consumptionsurveyindia",
}


@dataclass
class _SourceServer:
    source_id: str
    pkg_name: str
    _proc: Optional[subprocess.Popen] = field(default=None, repr=False)  # type: ignore[type-arg]
    _url: Optional[str] = field(default=None, repr=False)
    _http: Optional[httpx.Client] = field(default=None, repr=False)

    def _find_plumber_r(self) -> str:
        env_key = f"BHARATPULSE_{self.source_id.upper()}_PLUMBER_R"
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
        env_url = os.environ.get(f"BHARATPULSE_{self.source_id.upper()}_URL")
        self._url = env_url.rstrip("/") if env_url else self._start()
        http = httpx.Client(timeout=120.0)
        atexit.register(http.close)
        self._http = http
        return self._url

    def get(self, endpoint: str, params: dict[str, Any]) -> Any:
        url = self._resolve_url()  # also lazy-inits self._http
        clean = {k: v for k, v in params.items() if v is not None}
        resp = self._http.get(  # type: ignore[union-attr]
            f"{url}{endpoint}",
            params=clean,
        )
        resp.raise_for_status()
        return resp.json()


class BharatPulseClient:
    def __init__(self) -> None:
        self._servers: dict[str, _SourceServer] = {
            sid: _SourceServer(source_id=sid, pkg_name=pkg)
            for sid, pkg in SOURCE_REGISTRY.items()
        }

    def get(self, source: str, endpoint: str, params: dict[str, Any]) -> Any:
        if source not in self._servers:
            raise KeyError(
                f"Unknown source '{source}'. Known: {', '.join(sorted(self._servers))}"
            )
        return self._servers[source].get(endpoint, params)
