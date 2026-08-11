"""Scheme allowlisting at the public entry points.

urllib opens file://, ftp:// and more. For a package whose job is
fetching web pages that is never the intent, and when the URL came from
somewhere the caller does not control, file:// turns the fetcher into a
file-read primitive. Every public entry point rejects anything that is
not http or https before a request is made or a browser is launched.
"""

from pathlib import Path

import pytest

from pagefetch import (
    ALLOWED_SCHEMES,
    ContentMode,
    FetchOptions,
    NetworkFetcher,
    require_supported_scheme,
)
from pagefetch.errors import InvalidURL

REJECTED = [
    "file:///etc/passwd",
    "file://C:/Windows/win.ini",
    "ftp://ftp.example.com/pub/file.txt",
    "data:text/html,<h1>hi</h1>",
    "javascript:alert(1)",
    "gopher://example.com/",
    "jar:file:///tmp/x.jar!/y",
]

ACCEPTED = [
    "http://example.com",
    "https://example.com",
    "https://example.com/path?q=1#frag",
    "HTTPS://EXAMPLE.COM",  # scheme comparison is case-insensitive
]


@pytest.fixture
def fetcher(cache):
    return NetworkFetcher(cache=cache)


@pytest.fixture
def no_tiers(monkeypatch):
    """Record tier calls so a test can prove none of them ran."""
    calls: list[str] = []

    def recorder(name):
        def _tier(*args, **kwargs):
            calls.append(name)
            return ""

        return _tier

    monkeypatch.setattr(NetworkFetcher, "_fetch_urllib", recorder("urllib"))
    monkeypatch.setattr(NetworkFetcher, "_fetch_playwright", recorder("playwright"))
    monkeypatch.setattr(NetworkFetcher, "_fetch_nodriver", recorder("nodriver"))
    monkeypatch.setattr(NetworkFetcher, "_fetch_uc", recorder("uc"))
    return calls


# --- the predicate ----------------------------------------------------


@pytest.mark.parametrize("url", ACCEPTED)
def test_supported_schemes_pass(url):
    require_supported_scheme(url)


@pytest.mark.parametrize("url", REJECTED)
def test_unsupported_schemes_raise(url):
    with pytest.raises(InvalidURL):
        require_supported_scheme(url)


def test_error_names_the_scheme_and_what_is_allowed():
    with pytest.raises(InvalidURL) as excinfo:
        require_supported_scheme("ftp://example.com/x")
    message = str(excinfo.value)
    assert "ftp" in message
    assert "http" in message and "https" in message


def test_scheme_relative_url_gets_a_usable_hint():
    # "example.com/page" parses to an empty scheme. Naming the scheme in
    # the error would be useless, so this case says what to do instead.
    with pytest.raises(InvalidURL) as excinfo:
        require_supported_scheme("example.com/page")
    message = str(excinfo.value)
    assert "no scheme" in message
    assert "https://example.com/page" in message


def test_allowed_schemes_is_exactly_http_and_https():
    assert {"http", "https"} == ALLOWED_SCHEMES


# --- the entry points -------------------------------------------------


@pytest.mark.parametrize("url", REJECTED)
def test_fetch_rejects_before_touching_any_tier(fetcher, url, no_tiers):
    with pytest.raises(InvalidURL):
        fetcher.fetch(url)
    assert no_tiers == []


@pytest.mark.parametrize("url", REJECTED)
def test_download_bytes_rejects(fetcher, url):
    with pytest.raises(InvalidURL):
        fetcher.download_bytes(url)


@pytest.mark.parametrize("url", REJECTED)
def test_screenshot_rejects(fetcher, url, tmp_path):
    with pytest.raises(InvalidURL):
        fetcher.screenshot(url, tmp_path / "shot.png")


def test_batch_rejects_before_fetching_anything(fetcher, no_tiers):
    # The bad URL is last. A batch launches a browser and can run for
    # minutes, so the whole list is checked up front rather than failing
    # part-way through with work already done.
    urls = ["https://a.test", "https://b.test", "file:///etc/passwd"]
    with pytest.raises(InvalidURL) as excinfo:
        fetcher.fetch_batch(urls)
    assert "file" in str(excinfo.value)
    assert no_tiers == []


def test_batch_of_supported_urls_still_runs(fetcher, monkeypatch):
    monkeypatch.setattr(
        NetworkFetcher, "_run_batch", lambda self, urls, opts: ["ran"] * len(urls)
    )
    assert fetcher.fetch_batch(["https://a.test", "http://b.test"]) == ["ran", "ran"]


def test_supported_url_reaches_the_tiers(fetcher, monkeypatch):
    monkeypatch.setattr(
        NetworkFetcher, "_fetch_urllib", lambda self, url, mode: "real content"
    )
    result = fetcher.fetch(
        "https://example.com", FetchOptions(mode=ContentMode.HTML, use_cache=False)
    )
    assert result.ok is True
    assert result.content == "real content"


def test_rejection_happens_before_the_cache_is_consulted(fetcher, tmp_path: Path):
    # Nothing should be written or read for a URL that never runs.
    with pytest.raises(InvalidURL):
        fetcher.fetch("file:///etc/passwd")
    assert fetcher._cache.read("file:///etc/passwd", ContentMode.TEXT) is None
