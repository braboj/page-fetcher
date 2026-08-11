"""pagefetch — a self-contained, auto-escalating web page fetcher.

Public API:

    from pagefetch import NetworkFetcher, FetchOptions, ContentMode

    fetcher = NetworkFetcher()
    result = fetcher.fetch("https://example.com",
                           FetchOptions(mode=ContentMode.HTML))
    if result.ok:
        print(result.content)

The fetcher escalates urllib -> Playwright -> Nodriver -> SeleniumBase UC
as needed. See README.md for the full strategy and CLI usage.

This package has no dependency on any consuming project — drop it in as a
directory, a git submodule, or clone it on its own.
"""

from .cache import CleanReport, FileCache
from .detection import (
    AMBIGUOUS_ERROR_PAGE_PATTERNS,
    BOT_DETECTION_PATTERNS,
    ERROR_PAGE_PATTERNS,
    MIN_REAL_CONTENT_BYTES,
    html_to_text,
    is_bot_blocked,
    is_cacheable_junk,
    is_error_page,
    looks_like_real_content,
)
from .errors import (
    CacheDirError,
    CacheDirNotADirectory,
    CacheDirNotSet,
    CacheDirNotWritable,
    CommandLineError,
    InvalidURL,
    MissingScheme,
    PagefetchError,
    UnsupportedEncoding,
    UnsupportedScheme,
)
from .fake import FakeFetcher
from .network import (
    ALLOWED_SCHEMES,
    DEFAULT_USER_AGENT,
    NetworkFetcher,
    require_supported_scheme,
)
from .source import (
    ContentMode,
    FetchOptions,
    FetchResult,
    PageSource,
    Transport,
)

__all__ = [
    "ALLOWED_SCHEMES",
    "AMBIGUOUS_ERROR_PAGE_PATTERNS",
    "BOT_DETECTION_PATTERNS",
    "DEFAULT_USER_AGENT",
    "ERROR_PAGE_PATTERNS",
    "MIN_REAL_CONTENT_BYTES",
    "CacheDirError",
    "CacheDirNotADirectory",
    "CacheDirNotSet",
    "CacheDirNotWritable",
    "CleanReport",
    "CommandLineError",
    "ContentMode",
    "FakeFetcher",
    "FetchOptions",
    "FetchResult",
    "FileCache",
    "InvalidURL",
    "MissingScheme",
    "NetworkFetcher",
    "PageSource",
    "PagefetchError",
    "Transport",
    "UnsupportedEncoding",
    "UnsupportedScheme",
    "html_to_text",
    "is_bot_blocked",
    "is_cacheable_junk",
    "is_error_page",
    "looks_like_real_content",
    "require_supported_scheme",
]
