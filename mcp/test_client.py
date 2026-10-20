"""Run: uv run pytest test_client.py"""

import subprocess
import sys
from unittest.mock import Mock

import pytest

from bharatvitals.client import _SourceServer


def test_find_rscript_prefers_explicit_executable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "Rscript.exe"
    executable.touch()
    monkeypatch.setenv("BHARATVITALS_RSCRIPT", str(executable))
    monkeypatch.setattr("bharatvitals.client.shutil.which", lambda _: None)

    assert _SourceServer._find_rscript() == str(executable)


def test_find_rscript_uses_path_before_r_home(monkeypatch) -> None:
    monkeypatch.delenv("BHARATVITALS_RSCRIPT", raising=False)
    monkeypatch.setenv("R_HOME", r"C:\R")
    monkeypatch.setattr("bharatvitals.client.shutil.which", lambda _: r"C:\Path\Rscript.exe")

    assert _SourceServer._find_rscript() == r"C:\Path\Rscript.exe"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows installation path")
def test_find_rscript_searches_standard_program_files_install(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "R" / "R-4.6.1" / "bin" / "Rscript.exe"
    executable.parent.mkdir(parents=True)
    executable.touch()
    monkeypatch.delenv("BHARATVITALS_RSCRIPT", raising=False)
    monkeypatch.delenv("R_HOME", raising=False)
    monkeypatch.setenv("ProgramW6432", str(tmp_path))
    monkeypatch.delenv("ProgramFiles", raising=False)
    monkeypatch.delenv("ProgramFiles(x86)", raising=False)
    monkeypatch.setattr("bharatvitals.client.shutil.which", lambda _: None)

    assert _SourceServer._find_rscript() == str(executable)


def test_find_rscript_reports_missing_or_invalid_executable(monkeypatch) -> None:
    monkeypatch.setenv("BHARATVITALS_RSCRIPT", r"C:\missing\Rscript.exe")
    monkeypatch.setattr("bharatvitals.client.shutil.which", lambda _: None)

    with pytest.raises(FileNotFoundError, match="BHARATVITALS_RSCRIPT"):
        _SourceServer._find_rscript()

    monkeypatch.delenv("BHARATVITALS_RSCRIPT")
    monkeypatch.delenv("R_HOME", raising=False)
    monkeypatch.delenv("ProgramW6432", raising=False)
    monkeypatch.delenv("ProgramFiles", raising=False)
    monkeypatch.delenv("ProgramFiles(x86)", raising=False)
    monkeypatch.setattr("bharatvitals.client.glob.glob", lambda *_args: [])
    with pytest.raises(FileNotFoundError, match="add its bin directory to PATH"):
        _SourceServer._find_rscript()


def test_find_plumber_r_uses_resolved_executable(monkeypatch) -> None:
    run = Mock(return_value=Mock(stdout=r"C:\R\library\crsindia\plumber\plumber.R"))
    monkeypatch.setattr("bharatvitals.client.subprocess.run", run)
    monkeypatch.setattr("bharatvitals.client.os.path.isfile", lambda _: True)
    server = _SourceServer("crs", "crsindia")

    result = server._find_plumber_r(r"C:\R\bin\Rscript.exe")

    assert result == r"C:\R\library\crsindia\plumber\plumber.R"
    run.assert_called_once_with(
        [
            r"C:\R\bin\Rscript.exe",
            "--vanilla",
            "-e",
            "cat(system.file('plumber', 'plumber.R', package='crsindia'))",
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )


def test_free_port_is_within_plumber_supported_range() -> None:
    port = _SourceServer._free_port()

    assert 1024 <= port <= 49151


def test_start_uses_selected_executable_and_reports_startup_output(monkeypatch) -> None:
    process = Mock()
    process.poll.return_value = 1
    process.wait.return_value = 1

    def fail_to_start(*_args, **kwargs):
        kwargs["stdout"].write("plumber startup failed")
        return process

    popen = Mock(side_effect=fail_to_start)
    monkeypatch.setattr("bharatvitals.client.subprocess.Popen", popen)
    monkeypatch.setattr("bharatvitals.client.atexit.register", Mock())
    monkeypatch.setattr(_SourceServer, "_find_rscript", Mock(return_value=r"C:\R\Rscript.exe"))
    monkeypatch.setattr(
        _SourceServer,
        "_find_plumber_r",
        Mock(return_value=r"C:\R\library\crsindia\plumber\plumber.R"),
    )
    monkeypatch.setattr(_SourceServer, "_free_port", staticmethod(lambda: 8484))
    monkeypatch.setattr(
        _SourceServer, "_wait_healthy", staticmethod(lambda *_args, **_kwargs: False)
    )
    server = _SourceServer("crs", "crsindia")

    with pytest.raises(
        RuntimeError,
        match="did not become healthy within 45 s.*plumber startup failed",
    ):
        server._start()

    args, kwargs = popen.call_args
    assert args[0] == [
        r"C:\R\Rscript.exe",
        "--vanilla",
        "-e",
        "plumber::plumb('plumber.R')$run(host='127.0.0.1', port=8484, quiet=TRUE)",
    ]
    assert kwargs["cwd"] == r"C:\R\library\crsindia\plumber"
    assert kwargs["stdout"] is not subprocess.DEVNULL
    assert kwargs["stderr"] is subprocess.STDOUT


def test_configured_url_bypasses_startup_and_clears_cached_failure(monkeypatch) -> None:
    server = _SourceServer("crs", "crsindia", _failed=(0.0, "Rscript.exe missing"))
    monkeypatch.setattr(server, "_start", Mock(side_effect=AssertionError("must not start")))
    http_client = Mock()
    monkeypatch.setattr("bharatvitals.client.httpx.Client", Mock(return_value=http_client))
    monkeypatch.setenv("BHARATVITALS_CRS_URL", "http://127.0.0.1:8484/")

    assert server._resolve_url() == "http://127.0.0.1:8484"
    assert server._failed is None
    server._start.assert_not_called()


def test_failed_start_is_cached_until_cooldown(monkeypatch) -> None:
    server = _SourceServer("crs", "crsindia")
    start = Mock(side_effect=FileNotFoundError("Rscript.exe missing"))
    monkeypatch.setattr(server, "_start", start)
    monkeypatch.delenv("BHARATVITALS_CRS_URL", raising=False)
    monkeypatch.setattr("bharatvitals.client.time.monotonic", lambda: 10.0)

    with pytest.raises(FileNotFoundError, match="Rscript.exe missing"):
        server._resolve_url()
    with pytest.raises(RuntimeError, match="Rscript.exe missing"):
        server._resolve_url()

    start.assert_called_once_with()
    assert server.attempted


def test_configured_url_bypasses_startup(monkeypatch) -> None:
    server = _SourceServer("census", "censusindia")
    monkeypatch.setattr(server, "_start", Mock(side_effect=AssertionError("must not start")))
    http_client = Mock()
    monkeypatch.setattr("bharatvitals.client.httpx.Client", Mock(return_value=http_client))
    monkeypatch.setenv("BHARATVITALS_CENSUS_URL", "https://census.local/api")

    assert server._resolve_url() == "https://census.local/api"
    server._start.assert_not_called()
