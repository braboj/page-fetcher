"""Content-Encoding handling in the urllib tier.

A compressed body that is never decompressed does not fail loudly: decoded
as UTF-8 with errors="replace" it becomes mojibake, and mojibake from a
real page is far larger than MIN_REAL_CONTENT_BYTES. So it passes the
real-content gate, is returned as content, and is written to the cache.
These tests pin the decode step that stops that.
"""

import gzip
import random
import string
import urllib.request
import zlib
from contextlib import contextmanager

import pytest

from pagefetch import ContentMode, FetchOptions, NetworkFetcher
from pagefetch.detection import MIN_REAL_CONTENT_BYTES
from pagefetch.errors import UnsupportedEncoding
from pagefetch.network import ACCEPT_ENCODING, _decompress

# Deliberately near-incompressible, seeded for determinism. A repetitive
# filler string would gzip down to a couple of hundred bytes, and the
# mojibake from decoding it would fall UNDER the size floor and escalate —
# hiding the failure this module exists to pin. Real pages compress to
# roughly a third, well above the floor, so the undecoded body reads as
# real content and is cached. The assertion below keeps the fixture
# honest if the floor ever moves.
_FILLER = "".join(
    random.Random(0).choices(string.ascii_letters + "   ", k=60_000)  # noqa: S311
)
PAGE_HTML = "<html><body>" + _FILLER + "</body></html>"

assert len(gzip.compress(PAGE_HTML.encode())) > MIN_REAL_CONTENT_BYTES


class _FakeResponse:
    """Stand-in for the object urlopen returns as a context manager."""

    def __init__(self, body: bytes, headers: dict[str, str]):
        self._body = body
        self.headers = headers

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


@contextmanager
def _served(monkeypatch, body: bytes, headers: dict[str, str] | None = None):
    """Serve `body` to the next urlopen call and record the request."""
    captured: dict[str, urllib.request.Request] = {}

    def fake_urlopen(req, timeout=None):
        captured["request"] = req
        return _FakeResponse(body, headers or {})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    yield captured


@pytest.fixture
def fetcher(cache):
    return NetworkFetcher(cache=cache)


# --- _decompress ------------------------------------------------------


def test_decompress_passes_through_identity_bodies():
    assert _decompress(b"<html>plain</html>", "") == b"<html>plain</html>"


def test_decompress_undoes_declared_gzip():
    assert _decompress(gzip.compress(b"<html>hi</html>"), "gzip") == b"<html>hi</html>"


@pytest.mark.parametrize("header", ["gzip", "GZIP", " gzip "])
def test_decompress_gzip_header_is_case_and_space_insensitive(header):
    assert _decompress(gzip.compress(b"<html>hi</html>"), header) == b"<html>hi</html>"


def test_decompress_sniffs_gzip_when_the_header_does_not_declare_it():
    # The case that started this: a server compresses but sends no
    # Content-Encoding, so header-driven decoding alone would miss it.
    assert _decompress(gzip.compress(b"<html>hi</html>"), "") == b"<html>hi</html>"


def test_decompress_undoes_zlib_wrapped_deflate():
    assert (
        _decompress(zlib.compress(b"<html>hi</html>"), "deflate") == b"<html>hi</html>"
    )


def test_decompress_undoes_raw_deflate_without_zlib_header():
    compressor = zlib.compressobj(wbits=-zlib.MAX_WBITS)
    raw = compressor.compress(b"<html>hi</html>") + compressor.flush()
    assert _decompress(raw, "deflate") == b"<html>hi</html>"


# --- the tier ---------------------------------------------------------


def test_gzipped_response_is_decoded_not_returned_as_mojibake(fetcher, monkeypatch):
    # Without the decode step this returns replacement characters, which
    # are long enough to pass the real-content gate.
    body = gzip.compress(PAGE_HTML.encode())
    with _served(monkeypatch, body, {"Content-Encoding": "gzip"}):
        result = fetcher.fetch(
            "https://x.test", FetchOptions(mode=ContentMode.HTML, use_cache=False)
        )
    assert result.ok is True
    assert result.content == PAGE_HTML

    # U+FFFD, what errors="replace" emits for undecodable bytes.
    assert chr(0xFFFD) not in result.content


def test_undeclared_gzip_response_is_still_decoded(fetcher, monkeypatch):
    body = gzip.compress(PAGE_HTML.encode())
    with _served(monkeypatch, body, {}):
        result = fetcher.fetch(
            "https://x.test", FetchOptions(mode=ContentMode.HTML, use_cache=False)
        )
    assert result.content == PAGE_HTML


def test_gzipped_response_is_not_cached_as_mojibake(fetcher, monkeypatch, cache):
    # The damaging half of the bug: garbage clears the size floor, so it
    # was written to the cache and re-served on every later fetch.
    body = gzip.compress(PAGE_HTML.encode())
    with _served(monkeypatch, body, {"Content-Encoding": "gzip"}):
        fetcher.fetch(
            "https://x.test", FetchOptions(mode=ContentMode.HTML, use_cache=True)
        )
    assert cache.read("https://x.test", ContentMode.HTML) == PAGE_HTML


def test_uncompressed_response_still_works(fetcher, monkeypatch):
    with _served(monkeypatch, PAGE_HTML.encode(), {}):
        result = fetcher.fetch(
            "https://x.test", FetchOptions(mode=ContentMode.HTML, use_cache=False)
        )
    assert result.content == PAGE_HTML


def test_tier_advertises_only_encodings_it_can_undo(fetcher, monkeypatch):
    with _served(monkeypatch, PAGE_HTML.encode(), {}) as captured:
        fetcher.fetch("https://x.test", FetchOptions(use_cache=False))
    assert captured["request"].get_header("Accept-encoding") == ACCEPT_ENCODING

    # Advertising an encoding the standard library cannot decode would
    # make the response unreadable.
    assert "br" not in ACCEPT_ENCODING
    assert "zstd" not in ACCEPT_ENCODING


@pytest.mark.parametrize("header", ["br", "zstd", "BR", " compress "])
def test_decompress_rejects_an_encoding_it_cannot_undo(header):
    # Regression: these used to fall through and be returned unchanged, so
    # the compressed bytes became mojibake that cleared the size floor and
    # was cached as if it were a page.
    with pytest.raises(UnsupportedEncoding):
        _decompress(b"\x1b\x2a\x00\x84not-html-at-all", header)


@pytest.mark.parametrize("header", ["gzip, br", "br, gzip", "deflate, zstd"])
def test_decompress_rejects_a_chained_encoding(header):
    # A chain has to be undone in reverse, and any link this tier cannot
    # undo makes the whole body unreadable. Rejected even when one link is
    # gzip and the body still carries the gzip magic bytes.
    with pytest.raises(UnsupportedEncoding):
        _decompress(gzip.compress(b"<html>hi</html>"), header)


@pytest.mark.parametrize("header", ["identity", "", "  ", "identity, gzip"])
def test_decompress_treats_identity_as_no_encoding(header):
    # identity is the no-op encoding; it must not be read as unsupported,
    # and it must not make a single real encoding look like a chain.
    body = gzip.compress(b"<html>hi</html>") if "gzip" in header else b"<html>hi</html>"
    expected = b"<html>hi</html>"
    assert _decompress(body, header) == expected


def test_unsupported_encoding_escalates_instead_of_returning_garbage(
    fetcher, monkeypatch
):
    # The tier fails and the ladder carries on — a browser tier negotiates
    # its own encoding and may well succeed where urllib could not.
    calls: list[str] = []

    def fail_tier(name):
        def _tier(*args, **kwargs):
            calls.append(name)
            return ""

        return _tier

    monkeypatch.setattr(fetcher, "_fetch_playwright", fail_tier("playwright"))
    monkeypatch.setattr(fetcher, "_fetch_nodriver", fail_tier("nodriver"))
    monkeypatch.setattr(fetcher, "_fetch_uc", fail_tier("uc"))

    with _served(monkeypatch, PAGE_HTML.encode(), {"Content-Encoding": "br"}):
        result = fetcher.fetch("https://x.test", FetchOptions(use_cache=False))

    assert calls == ["playwright", "nodriver", "uc"]
    assert result.ok is False
    assert result.content == ""


def test_unsupported_encoding_body_is_not_cached(fetcher, monkeypatch, cache):
    # The body is big enough to clear the size floor, which is exactly why
    # it used to be cached.
    monkeypatch.setattr(fetcher, "_fetch_playwright", lambda *a, **k: "")
    monkeypatch.setattr(fetcher, "_fetch_nodriver", lambda *a, **k: "")
    monkeypatch.setattr(fetcher, "_fetch_uc", lambda *a, **k: "")
    assert len(PAGE_HTML) > MIN_REAL_CONTENT_BYTES

    with _served(monkeypatch, PAGE_HTML.encode(), {"Content-Encoding": "zstd"}):
        fetcher.fetch("https://x.test", FetchOptions(use_cache=True))

    assert cache.read("https://x.test", ContentMode.TEXT) is None


def test_undecompressable_body_escalates_instead_of_returning_garbage(
    fetcher, monkeypatch
):
    # A body that claims gzip but is not gzip must not become content.
    # Escalating is right: the browser tiers may well succeed.
    calls: list[str] = []

    def fail_tier(name):
        def _tier(*args, **kwargs):
            calls.append(name)
            return ""

        return _tier

    monkeypatch.setattr(fetcher, "_fetch_playwright", fail_tier("playwright"))
    monkeypatch.setattr(fetcher, "_fetch_nodriver", fail_tier("nodriver"))
    monkeypatch.setattr(fetcher, "_fetch_uc", fail_tier("uc"))

    with _served(monkeypatch, b"not actually gzipped", {"Content-Encoding": "gzip"}):
        result = fetcher.fetch("https://x.test", FetchOptions(use_cache=False))

    assert calls == ["playwright", "nodriver", "uc"]
    assert result.ok is False
    assert result.content == ""


def test_undecompressable_body_is_not_cached(fetcher, monkeypatch, cache):
    monkeypatch.setattr(fetcher, "_fetch_playwright", lambda *a, **k: "")
    monkeypatch.setattr(fetcher, "_fetch_nodriver", lambda *a, **k: "")
    monkeypatch.setattr(fetcher, "_fetch_uc", lambda *a, **k: "")
    with _served(monkeypatch, b"not actually gzipped", {"Content-Encoding": "gzip"}):
        fetcher.fetch("https://x.test", FetchOptions(use_cache=True))
    assert cache.read("https://x.test", ContentMode.TEXT) is None
