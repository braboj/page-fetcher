"""Page source contract for page fetching.

Defines the PageSource interface that concrete fetchers (NetworkFetcher)
and test doubles (FakeFetcher) implement, plus the typed options and
result shapes that flow through it. This module has no third-party or
project dependencies — it is the stable contract the rest of the package
and any consumer depend on.

Transport here is the enumeration naming the four rungs, not the module
that climbs them; that is network.py.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ContentMode(Enum):
    """What form fetched content takes."""

    TEXT = "text"  # tags stripped, whitespace collapsed
    HTML = "html"  # raw HTML


class Transport(Enum):
    """Which transport tier to use. AUTO escalates on failure.

    Named for what each tier requires of the caller rather than for the
    library behind it, so swapping an engine is not a breaking change.
    HEADED and HEADLESS both get past bot protection and differ only in
    whether a display is available.
    """

    AUTO = "auto"  # http, escalating through the browser tiers as needed
    HTTP = "http"  # force a plain HTTP request, no browser
    JS = "js"  # force a browser that renders JavaScript
    HEADED = "headed"  # force a bot-bypass browser that needs a display
    HEADLESS = "headless"  # force a bot-bypass browser that needs no display


# Post-load settle time the browser tiers apply without being asked. The
# tiers poll for readiness rather than sleeping, so this is a floor, not a
# budget: a caller asking for more than this gets an extra explicit sleep.
DEFAULT_WAIT_MS = 500


@dataclass(frozen=True)
class FetchOptions:
    """Options for a single fetch. Immutable so it can be shared safely."""

    mode: ContentMode = ContentMode.TEXT
    transport: Transport = Transport.AUTO
    wait_ms: int = DEFAULT_WAIT_MS
    use_cache: bool = True


@dataclass(frozen=True)
class FetchResult:
    """Outcome of a fetch. content is "" when every tier failed."""

    url: str
    content: str
    tier_used: str  # "http" | "js" | "headed" | "headless" | "cache" | "fake" | "none"
    ok: bool


class PageSource(ABC):
    """A source of page content.

    Concrete implementations fetch over the network by any means; test
    doubles return canned content. Implementations MUST NOT couple to any
    consuming project's layout — transport only.
    """

    @abstractmethod
    def fetch(self, url: str, options: FetchOptions | None = None) -> FetchResult:
        """Fetch one URL.

        Never raises for fetch failure — returns a FetchResult with
        ok=False and content="" instead.
        """

    @abstractmethod
    def fetch_batch(
        self, urls: list[str], options: FetchOptions | None = None
    ) -> list[FetchResult]:
        """Fetch many URLs, reusing one browser session where applicable.

        Order of results matches the input order.
        """

    @abstractmethod
    def download_bytes(self, url: str, min_size: int = 0) -> bytes | None:
        """Download raw bytes (images, PDFs).

        Returns None on failure or when the payload is smaller than
        min_size. The caller owns the destination path and naming — this
        is transport only.
        """

    @abstractmethod
    def screenshot(
        self, url: str, dest: Path, options: FetchOptions | None = None
    ) -> bool:
        """Capture a full-page screenshot to dest. Returns True on success."""
