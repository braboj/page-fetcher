"""CLI exit-code tests.

`main()` used to return 0 whatever came back, so a caller writing
`pagefetch "$url" > page.txt && process page.txt` processed an empty file
on total failure. These drive `main()` with a stubbed fetcher and assert
the code, since that is the only signal a shell pipeline can act on.
"""

import pytest

from pagefetch import FetchResult
from pagefetch.__main__ import (
    EXIT_ALL_FAILED,
    EXIT_OK,
    EXIT_PARTIAL,
    _batch_exit_code,
    main,
)


def _result(url: str, content: str) -> FetchResult:
    return FetchResult(url=url, content=content, tier_used="fake", ok=bool(content))


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path, monkeypatch):
    """Keep every case off the project cache dir."""
    monkeypatch.delenv("PAGEFETCH_CACHE_DIR", raising=False)
    monkeypatch.chdir(tmp_path)


def _stub_fetcher(monkeypatch, single=None, batch=None):
    """Replace the fetcher main() builds, so no network is touched."""

    class _Stub:
        def __init__(self, *a, **kw):
            pass

        def fetch(self, url, options=None):
            return single

        def fetch_batch(self, urls, options=None):
            return batch

    monkeypatch.setattr("pagefetch.__main__.NetworkFetcher", _Stub)


def _run(monkeypatch, argv):
    monkeypatch.setattr("sys.argv", ["pagefetch", *argv])
    with pytest.raises(SystemExit) as exc:
        main()
    return exc.value.code


# --- single URL ------------------------------------------------------


def test_single_url_failure_exits_non_zero(monkeypatch, capsys):
    _stub_fetcher(monkeypatch, single=_result("https://x.test", ""))
    assert _run(monkeypatch, ["https://x.test"]) == EXIT_ALL_FAILED
    assert "no content fetched" in capsys.readouterr().err


def test_single_url_failure_writes_nothing_to_stdout(monkeypatch, capsys):
    # A bare newline on stdout is worse than nothing — it makes an empty
    # file look like a successful fetch of an empty page.
    _stub_fetcher(monkeypatch, single=_result("https://x.test", ""))
    _run(monkeypatch, ["https://x.test"])
    assert capsys.readouterr().out == ""


def test_single_url_success_returns_without_exiting(monkeypatch, capsys):
    _stub_fetcher(monkeypatch, single=_result("https://x.test", "real content"))
    monkeypatch.setattr("sys.argv", ["pagefetch", "https://x.test"])

    main()

    assert capsys.readouterr().out.strip() == "real content"


def test_rejected_scheme_exits_non_zero(monkeypatch, capsys):
    # The ValueError path shares the failure code rather than tracebacking.
    assert _run(monkeypatch, ["file:///etc/passwd"]) == EXIT_ALL_FAILED
    assert "only fetches http, https" in capsys.readouterr().err


# --- batch -----------------------------------------------------------


def test_batch_all_failed_exits_all_failed(monkeypatch):
    _stub_fetcher(
        monkeypatch,
        batch=[_result("https://a.test", ""), _result("https://b.test", "")],
    )
    assert _run(monkeypatch, ["https://a.test", "https://b.test"]) == EXIT_ALL_FAILED


def test_batch_partial_failure_exits_partial(monkeypatch):
    _stub_fetcher(
        monkeypatch,
        batch=[_result("https://a.test", "ok"), _result("https://b.test", "")],
    )
    assert _run(monkeypatch, ["https://a.test", "https://b.test"]) == EXIT_PARTIAL


def test_batch_all_succeeded_exits_ok(monkeypatch):
    _stub_fetcher(
        monkeypatch,
        batch=[_result("https://a.test", "ok"), _result("https://b.test", "ok")],
    )
    assert _run(monkeypatch, ["https://a.test", "https://b.test"]) == EXIT_OK


def test_batch_writes_partial_output_before_exiting(monkeypatch, tmp_path):
    # A partial batch still writes what it got — the non-zero code reports
    # the gap, it does not discard the successes.
    out = tmp_path / "out"
    _stub_fetcher(
        monkeypatch,
        batch=[_result("https://a.test", "ok"), _result("https://b.test", "")],
    )
    code = _run(
        monkeypatch, ["https://a.test", "https://b.test", "--output-dir", str(out)]
    )
    assert code == EXIT_PARTIAL
    assert len(list(out.iterdir())) == 1


# --- _batch_exit_code ------------------------------------------------


def test_empty_batch_is_not_a_failure():
    assert _batch_exit_code([]) == EXIT_OK
