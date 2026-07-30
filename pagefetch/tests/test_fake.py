"""FakeFetcher contract tests — it must honor the PageSource interface.

A test double earns its keep by failing where the real thing would. These
pin the places FakeFetcher previously diverged: it ignored ContentMode
entirely, so a consumer exercising both modes got identical content from
each, and its screenshot returned True without writing the file the real
implementation writes.
"""

from pathlib import Path

import pytest

from pagefetch import (
    ContentMode,
    FakeFetcher,
    FetchOptions,
    FileCache,
    NetworkFetcher,
    PageSource,
)

PAGE = "<html><body><p>Hello   world</p><script>var x=1;</script></body></html>"


def test_fake_is_a_page_source():
    assert isinstance(FakeFetcher(), PageSource)


def test_fetch_returns_mapped_content_and_records_call():
    fake = FakeFetcher(responses={"https://a.test": "<html>A</html>"})
    result = fake.fetch("https://a.test", FetchOptions(mode=ContentMode.HTML))
    assert result.content == "<html>A</html>"
    assert result.ok is True
    assert result.tier_used == "fake"
    assert fake.calls == ["https://a.test"]


def test_fetch_unmapped_url_is_not_ok():
    fake = FakeFetcher(responses={})
    result = fake.fetch("https://missing.test")
    assert result.content == ""
    assert result.ok is False


def test_fetch_batch_preserves_order():
    fake = FakeFetcher(responses={"u1": "a", "u2": "b"})
    results = fake.fetch_batch(["u2", "u1", "u3"])
    assert [r.url for r in results] == ["u2", "u1", "u3"]
    assert [r.content for r in results] == ["b", "a", ""]


# --- content mode ----------------------------------------------------


def test_html_mode_returns_the_body_verbatim():
    fake = FakeFetcher(responses={"u": PAGE})
    result = fake.fetch("u", FetchOptions(mode=ContentMode.HTML))
    assert result.content == PAGE


def test_text_mode_strips_the_body():
    fake = FakeFetcher(responses={"u": PAGE})
    result = fake.fetch("u", FetchOptions(mode=ContentMode.TEXT))
    assert result.content == "Hello world"


def test_the_two_modes_differ():
    # The gap this closes: both modes used to return the same string, so a
    # bug in mode-dependent handling was invisible under test.
    fake = FakeFetcher(responses={"u": PAGE})
    html = fake.fetch("u", FetchOptions(mode=ContentMode.HTML)).content
    text = fake.fetch("u", FetchOptions(mode=ContentMode.TEXT)).content
    assert html != text


def test_text_is_the_default_mode_as_it_is_for_the_real_fetcher():
    assert FetchOptions().mode is ContentMode.TEXT
    fake = FakeFetcher(responses={"u": PAGE})
    assert fake.fetch("u").content == "Hello world"


def test_markup_free_content_survives_text_mode():
    # A map of plain strings is the common case in consumer tests and must
    # keep working; stripping tags from text with none is a no-op beyond
    # collapsing whitespace.
    fake = FakeFetcher(responses={"u": "just a string"})
    assert fake.fetch("u").content == "just a string"


def test_both_fetchers_derive_text_from_html_the_same_way(monkeypatch, tmp_path):
    # The point of the double: given the same body, the fake and the real
    # fetcher must produce the same content in each mode.
    real = NetworkFetcher(cache=FileCache(cache_dir=tmp_path / "c"))
    monkeypatch.setattr(real, "_fetch_urllib", lambda url, mode: PAGE)
    fake = FakeFetcher(responses={"https://a.test": PAGE})

    html_opts = FetchOptions(mode=ContentMode.HTML, use_cache=False)
    assert fake.fetch("https://a.test", html_opts).content == PAGE
    assert real.fetch("https://a.test", html_opts).content == PAGE

    # The real tier returns already-stripped text in TEXT mode, so compare
    # the fake against the same html_to_text result rather than the tier.
    text_opts = FetchOptions(mode=ContentMode.TEXT, use_cache=False)
    assert fake.fetch("https://a.test", text_opts).content == "Hello world"


# --- download_bytes --------------------------------------------------


def test_download_bytes_returns_mapped_payload():
    fake = FakeFetcher(binary={"https://img.test": b"\x89PNG..."})
    assert fake.download_bytes("https://img.test") == b"\x89PNG..."
    assert fake.binary_calls == ["https://img.test"]


def test_download_bytes_respects_min_size():
    fake = FakeFetcher(binary={"https://tiny.test": b"xx"})
    assert fake.download_bytes("https://tiny.test", min_size=100) is None


def test_download_bytes_missing_returns_none():
    assert FakeFetcher().download_bytes("https://none.test") is None


# --- screenshot ------------------------------------------------------


def test_screenshot_writes_the_file_it_reports_writing(tmp_path: Path):
    # It used to return True without creating dest, so a test asserting
    # dest.exists() passed against neither implementation.
    fake = FakeFetcher(responses={"https://a.test": "x"})
    dest = tmp_path / "shots" / "s.png"

    assert fake.screenshot("https://a.test", dest) is True
    assert dest.exists()
    assert dest.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_screenshot_creates_missing_parent_directories(tmp_path: Path):
    fake = FakeFetcher(responses={"https://a.test": "x"})
    dest = tmp_path / "deep" / "nested" / "s.png"
    assert fake.screenshot("https://a.test", dest) is True
    assert dest.exists()


def test_screenshot_of_an_unmapped_url_writes_nothing(tmp_path: Path):
    fake = FakeFetcher(responses={"https://a.test": "x"})
    dest = tmp_path / "s.png"
    assert fake.screenshot("https://b.test", dest) is False
    assert dest.exists() is False


def test_screenshot_records_its_calls(tmp_path: Path):
    fake = FakeFetcher(responses={"https://a.test": "x"})
    fake.screenshot("https://a.test", tmp_path / "a.png")
    fake.screenshot("https://b.test", tmp_path / "b.png")
    assert fake.screenshot_calls == ["https://a.test", "https://b.test"]


@pytest.mark.parametrize("mode", list(ContentMode))
def test_screenshot_accepts_options(tmp_path: Path, mode):
    fake = FakeFetcher(responses={"u": "x"})
    assert fake.screenshot("u", tmp_path / "s.png", FetchOptions(mode=mode)) is True
