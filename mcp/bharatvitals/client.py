import atexit
import glob
import os
import secrets
import shutil
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

_RETRY_AFTER = 60.0  # seconds


@dataclass
class _SourceServer:
    source_id: str
    pkg_name: str
    # Path of the Plumber entry point inside the installed R package's `inst/`
    # directory. Most packages ship `plumber/plumber.R`.
    plumber_path: str = "plumber/plumber.R"
    _proc: Optional[subprocess.Popen] = field(default=None, repr=False)  # type: ignore[type-arg]
    _url: Optional[str] = field(default=None, repr=False)
    _http: Optional[httpx.Client] = field(default=None, repr=False)
    _failed: Optional[tuple[float, str]] = field(default=None, repr=False)

    @staticmethod
    def _find_rscript() -> str:
        env_path = os.environ.get("BHARATVITALS_RSCRIPT", "").strip()
        if env_path:
            if os.path.isfile(env_path):
                return os.path.abspath(env_path)
            executable = shutil.which(env_path)
            if executable:
                return executable
            raise FileNotFoundError(
                f"Configured BHARATVITALS_RSCRIPT executable was not found: {env_path}"
            )

        executable = shutil.which("Rscript")
        if executable:
            return executable

        candidates = []
        r_home = os.environ.get("R_HOME")
        if r_home:
            candidates.extend(
                (
                    os.path.join(r_home, "bin", "Rscript.exe"),
                    os.path.join(r_home, "bin", "x64", "Rscript.exe"),
                )
            )

        if os.name == "nt":
            for program_files in (
                os.environ.get("ProgramW6432"),
                os.environ.get("ProgramFiles"),
                os.environ.get("ProgramFiles(x86)"),
            ):
                if program_files:
                    candidates.extend(
                        glob.glob(
                            os.path.join(program_files, "R", "R-*", "bin", "Rscript.exe")
                        )
                    )
                    candidates.extend(
                        glob.glob(
                            os.path.join(
                                program_files, "R", "R-*", "bin", "x64", "Rscript.exe"
                            )
                        )
                    )

        for candidate in sorted(set(candidates), reverse=True):
            if os.path.isfile(candidate):
                return candidate

        raise FileNotFoundError(
            "Rscript.exe was not found. Install R and add its bin directory to PATH, "
            "or set BHARATVITALS_RSCRIPT to the full path of Rscript.exe."
        )

    def _find_plumber_r(self, rscript: Optional[str] = None) -> str:
        env_key = f"BHARATVITALS_{self.source_id.upper()}_PLUMBER_R"
        env_path = os.environ.get(env_key)
        if env_path and os.path.isfile(env_path):
            return env_path
        rscript = rscript or self._find_rscript()

        if "/" in self.plumber_path:
            subdir, fname = self.plumber_path.rsplit("/", 1)
            expr = f"system.file('{subdir}', '{fname}', package='{self.pkg_name}')"
        else:
            expr = f"system.file('{self.plumber_path}', package='{self.pkg_name}')"

        result = subprocess.run(
            [rscript, "--vanilla", "-e", f"cat({expr})"],
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
        for _ in range(100):
            port = secrets.randbelow(49151 - 1024 + 1) + 1024
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
        raise OSError("Could not find a free local port in Plumber's supported range.")

    @staticmethod
    def _wait_healthy(
        url: str,
        timeout: float = 45.0,
        process: Optional[subprocess.Popen] = None,  # type: ignore[type-arg]
    ) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if process is not None and process.poll() is not None:
                return False
            try:
                httpx.get(f"{url}/health", timeout=2.0)
                return True
            except Exception:
                time.sleep(0.75)
        return False

    def _start(self) -> str:
        rscript = self._find_rscript()
        plumber_r = self._find_plumber_r(rscript)
        port = self._free_port()
        script = os.path.basename(plumber_r)
        with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as startup_log:
            self._proc = subprocess.Popen(
                [
                    rscript,
                    "--vanilla",
                    "-e",
                    f"plumber::plumb('{script}')$run(host='127.0.0.1', port={port}, quiet=TRUE)",
                ],
                cwd=os.path.dirname(plumber_r),
                stdout=startup_log,
                stderr=subprocess.STDOUT,
            )
            atexit.register(self._proc.terminate)
            url = f"http://127.0.0.1:{port}"
            if not self._wait_healthy(url, process=self._proc):
                if self._proc.poll() is None:
                    self._proc.terminate()
                    self._proc.wait()
                startup_log.seek(0)
                details = startup_log.read().strip()
                message = (
                    f"Source '{self.source_id}' plumber API did not become healthy within "
                    f"45 s (package: {self.pkg_name}, exit code: {self._proc.returncode})."
                )
                if details:
                    message += f" Rscript output: {details[-2000:]}"
                raise RuntimeError(message)
        return url

    def _resolve_url(self) -> str:
        if self._url is not None:
            return self._url
        env_url = os.environ.get(f"BHARATVITALS_{self.source_id.upper()}_URL")
        if not env_url and self._failed and time.monotonic() - self._failed[0] < _RETRY_AFTER:
            raise RuntimeError(self._failed[1])
        try:
            self._url = env_url.rstrip("/") if env_url else self._start()
            self._failed = None
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

    def _decode(self, resp: httpx.Response) -> Any:
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
        return self._decode(resp)

    def post(
        self,
        endpoint: str,
        json: Any,
        timeout: Any = httpx.USE_CLIENT_DEFAULT,
    ) -> Any:
        url = self._resolve_url()
        resp = self._http.post(  # type: ignore[union-attr]
            f"{url}{endpoint}",
            json=json,
            timeout=timeout,
        )
        return self._decode(resp)


class BharatVitalsClient:
    def __init__(
        self,
        packages: dict[str, str],
        plumber_paths: Optional[dict[str, str]] = None,
    ) -> None:
        """packages: source id -> R package that ships its Plumber entry point.

        plumber_paths: optional source id -> path of that entry point inside the
        package's ``inst/`` directory (default ``plumber/plumber.R``).
        """
        paths = plumber_paths or {}
        self._servers: dict[str, _SourceServer] = {
            sid: _SourceServer(
                source_id=sid,
                pkg_name=pkg,
                plumber_path=paths.get(sid, "plumber/plumber.R"),
            )
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

    def post(
        self,
        source: str,
        endpoint: str,
        json: Any,
        timeout: Any = httpx.USE_CLIENT_DEFAULT,
    ) -> Any:
        return self._server(source).post(endpoint, json, timeout)

    def attempted(self, source: str) -> bool:
        return self._server(source).attempted
