"""FakeFetcher — a deterministic PageSource test double.

Returns canned content from a URL-to-content map, with no network, no
browser, and no disk beyond the screenshots it is asked to write. It
records the URLs it was asked for so tests can assert on call behavior.
It is part of the public package surface so consumers (e.g. brand tools)
can test their pipelines against it.

Map values are page bodies — the HTML a real fetch would have returned.
TEXT mode derives its content from them exactly as NetworkFetcher does,
by running html_to_text over the body, so a consumer exercising both
modes sees them differ the way they will in production. Canned content
with no markup survives that unchanged apart from whitespace collapsing,
so a map of plain strings still behaves as before.

One deliberate divergence from NetworkFetcher remains: this double
accepts any key as a "URL", while NetworkFetcher rejects anything that is
not http or https (see require_supported_scheme). The keys here are map
lookups that never reach a socket, so the scheme carries no meaning and
tests are free to use short labels. The cost is that a consumer passing
an unsupported scheme sees it pass against the fake and raise against the
real fetcher — validate at your own boundary if you accept URLs from
elsewhere.
"""

from pathlib import Path

from .detection import html_to_text
from .source import ContentMode, FetchOptions, FetchResult, PageSource

# A valid 1x1 transparent PNG. screenshot() writes this so `dest` exists
# and parses as an image afterwards, the way it does for the real
# fetcher — returning True without writing anything let a test that
# asserts on the file pass against neither implementation.
_PLACEHOLDER_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0bIDATx\x9cc`\x00"
    b"\x02\x00\x00\x05\x00\x01z^\xab?\x00\x00\x00\x00IEND\xaeB`\x82"
)


class FakeFetcher(PageSource):
    """A PageSource backed by in-memory maps instead of the network."""

    def __init__(
        self,
        responses: dict[str, str] | None = None,
        binary: dict[str, bytes] | None = None,
    ) -> None:
        """Seed the fetcher with per-URL text and binary responses."""
        self._responses = responses or {}
        self._binary = binary or {}
        self.calls: list[str] = []
        self.binary_calls: list[str] = []
        self.screenshot_calls: list[str] = []

    def fetch(self, url: str, options: FetchOptions | None = None) -> FetchResult:
        """Return the mapped body for a URL, or an ok=False empty result."""
        self.calls.append(url)
        opts = options or FetchOptions()
        body = self._responses.get(url, "")
        content = body if opts.mode is ContentMode.HTML else html_to_text(body)
        return FetchResult(url=url, content=content, tier_used="fake", ok=bool(content))

    def fetch_batch(
        self, urls: list[str], options: FetchOptions | None = None
    ) -> list[FetchResult]:
        """Fetch each URL in order. No session to reuse, so no batching."""
        return [self.fetch(url, options) for url in urls]

    def download_bytes(self, url: str, min_size: int = 0) -> bytes | None:
        """Return the mapped bytes, or None when unmapped or under size."""
        self.binary_calls.append(url)
        data = self._binary.get(url)
        if data is None or len(data) < min_size:
            return None
        return data

    def screenshot(
        self, url: str, dest: Path, options: FetchOptions | None = None
    ) -> bool:
        """Write a placeholder image to dest.

        The real fetcher writes a real one. Returns False without touching
        dest for an unmapped URL, which is what a failed capture does.
        """
        self.screenshot_calls.append(url)
        if url not in self._responses:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(_PLACEHOLDER_PNG)
        return True
