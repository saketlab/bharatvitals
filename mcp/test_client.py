"""Run: uv run python test_client.py"""

from bharatvitals.client import _SourceServer


def test_failed_start_is_cached() -> None:
    srv = _SourceServer(source_id="nosuch", pkg_name="nosuch")
    assert not srv.attempted

    def boom() -> str:
        raise RuntimeError("boom")

    srv._start = boom  # type: ignore[method-assign]
    for _ in range(2):
        try:
            srv.get("/health", {})
        except RuntimeError as e:
            assert str(e) == "boom"
        srv._start = lambda: 1 / 0  # type: ignore[method-assign]  # cooldown must skip it
    assert srv.attempted


if __name__ == "__main__":
    test_failed_start_is_cached()
    print("ok")
