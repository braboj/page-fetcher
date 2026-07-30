"""Bot-detection tests — one per pattern plus the meta-refresh case."""

from pathlib import Path

import pytest

from pagefetch import (
    is_bot_blocked,
    is_cacheable_junk,
    is_error_page,
    looks_like_real_content,
)
from pagefetch.detection import (
    AMBIGUOUS_ERROR_PAGE_PATTERNS,
    BOT_DETECTION_PATTERNS,
    ERROR_PAGE_PATTERNS,
    MIN_REAL_CONTENT_BYTES,
    html_to_text,
)

FIXTURES = Path(__file__).parent / "fixtures"

REAL_PAGE = "<html><body>" + ("Lorem ipsum lens specs. " * 100) + "</body></html>"
# A real content page comfortably above the size floor.
BIG_REAL_PAGE = "<html><body>" + ("Lorem ipsum lens specs. " * 1000) + "</body></html>"


def test_real_page_is_not_blocked():
    assert is_bot_blocked(REAL_PAGE) is False


def test_short_meta_refresh_is_blocked():
    html = '<html><head><meta http-equiv="refresh" content="0;url=/x"></head></html>'
    assert is_bot_blocked(html) is True


def test_long_page_with_meta_refresh_is_not_short_circuited():
    # The meta-refresh short-circuit only fires under 500 bytes.
    html = "<meta refresh>" + ("x" * 600)
    assert is_bot_blocked(html) is False


@pytest.mark.parametrize(
    "snippet",
    [
        "<title>403 Forbidden</title>",
        "<title>Access Denied</title>",
        "Checking your browser before accessing",
        "Checking the site connection security",
        "Enable JavaScript and cookies to continue",
        "Attention Required! | Cloudflare",
        "Just a moment...",
        "Verifying you are human",
        "Please allow cookies",
        "This page requires cookies to be enabled",
        "<title>429 Too Many Requests</title>",
        "Too Many Requests",
        "Rate limit exceeded",
        "Our systems have detected unusual traffic",
        "We detected a translation service and are reloading",
        '<script src="/cdn-cgi/challenge-platform/h/b/orchestrate"></script>',
        '<div id="cf-challenge-running">',
        '<div id="px-captcha">',
        "_pxhd=abc123",
    ],
)
def test_each_bot_pattern_is_detected(snippet):
    html = f"<html><body>{snippet}</body></html>"
    assert is_bot_blocked(html) is True


def test_patterns_list_is_covered_by_parametrization():
    # Guard: if a new pattern is added, the parametrized test above must grow.
    assert len(BOT_DETECTION_PATTERNS) == 19


@pytest.mark.parametrize(
    "prose",
    [
        "Discussing rate limits in REST APIs and how to design them. ",
        "The rate limit is 100 requests per minute for this endpoint. ",
        "Rate limiting protects a service from a thundering herd. ",
    ],
)
def test_rate_limit_in_ordinary_prose_is_not_bot_blocked(prose):
    # #12: "Rate.?limit" matched the bare phrase, so an article about API
    # rate limiting was unfetchable — every tier applies this same gate, so
    # there was no escalation path that could return the page.
    article = "<html><title>API design</title><body>" + (prose * 200) + "</body></html>"
    assert is_bot_blocked(article) is False
    assert looks_like_real_content(article) is True


@pytest.mark.parametrize(
    "snippet",
    [
        "Rate limit exceeded",
        "Rate limits exceeded, please slow down",
        "You have reached your rate limit",
        "rate-limited — try again in 60 seconds",
    ],
)
def test_real_throttle_wording_is_still_detected(snippet):
    # Guard against tightening the pattern until genuine throttle pages slip
    # through, the same way the Cloudflare pattern is guarded above.
    assert is_bot_blocked(f"<html><body>{snippet}</body></html>") is True


def test_dpreview_real_body_is_not_bot_blocked():
    # Imbra-Ltd/wuseria#870 regression: a real 137 KB DPReview spec page
    # embeds the substring "checking your browser extensions and settings"
    # inside ad-blocker help text. The Cloudflare pattern must not
    # false-match on that text.
    html = (FIXTURES / "dpreview_specifications.html").read_text(
        encoding="utf-8", errors="replace"
    )
    assert "checking your browser" in html.lower()  # the false-positive bait
    assert is_bot_blocked(html) is False
    assert looks_like_real_content(html) is True


def test_cloudflare_checking_your_browser_still_detected():
    # Guard against tightening the pattern so much that the real CF
    # interstitial slips through. CF emits "Checking your browser before
    # accessing <site>" — that exact shape must still register as a bot block.
    cf = "<html><body>Checking your browser before accessing example.com</body></html>"
    assert is_bot_blocked(cf) is True


def test_checking_your_browser_substring_alone_is_not_bot_blocked():
    # The bare substring without the " before " anchor (e.g. ad-blocker help
    # text on real content pages) must not trigger a bot match.
    benign = (
        "<html><body>"
        + ("We recommend checking your browser extensions and settings. " * 200)
        + "</body></html>"
    )
    assert is_bot_blocked(benign) is False


@pytest.mark.parametrize(
    "closing",
    [
        "</script>",
        "</script >",
        "</script\t\n>",
        '</script foo="bar">',
    ],
)
def test_html_to_text_strips_script_whatever_the_closing_tag(closing):
    # Browsers accept whitespace and even attributes inside an end tag.
    # Anchoring on a bare "</script>" left those blocks unmatched, the
    # outer tag strip then removed only the tags, and the JavaScript body
    # survived as text. Flagged by CodeQL as py/bad-tag-filter.
    html = f"<html><body><script>var secret=1;{closing}Real text</body></html>"
    assert html_to_text(html) == "Real text"


@pytest.mark.parametrize("closing", ["</style>", "</style >", '</style x="1">'])
def test_html_to_text_strips_style_whatever_the_closing_tag(closing):
    html = f"<html><body><style>.a{{color:red}}{closing}Real text</body></html>"
    assert html_to_text(html) == "Real text"


def test_html_to_text_strips_scripts_styles_and_tags():
    html = (
        "<html><head><style>.a{color:red}</style>"
        "<script>var x=1;</script></head>"
        "<body><p>Hello   world</p></body></html>"
    )
    assert html_to_text(html) == "Hello world"


# --- looks_like_real_content -----------------------------------------


def test_big_real_page_is_real_content():
    assert looks_like_real_content(BIG_REAL_PAGE) is True


def test_bot_blocked_page_is_not_real_content():
    # Recognized bot page fails regardless of size.
    big_bot_page = "Too Many Requests" + ("x" * 20000)
    assert looks_like_real_content(big_bot_page) is False


def test_short_page_is_not_real_content():
    # A throttle/error stub below the floor is rejected even with no
    # recognizable bot text (the B&H ~7-8 KB throttle-page case).
    stub = "<html><body>" + ("x" * 7700) + "</body></html>"
    assert len(stub) < MIN_REAL_CONTENT_BYTES
    assert looks_like_real_content(stub) is False


def test_min_bytes_threshold_is_configurable():
    page = "<html>" + ("x" * 2000) + "</html>"
    assert looks_like_real_content(page, min_bytes=10_000) is False
    assert looks_like_real_content(page, min_bytes=1_000) is True


def test_big_real_page_is_not_an_error_page():
    assert is_error_page(BIG_REAL_PAGE) is False


@pytest.mark.parametrize(
    "snippet",
    [
        "<title>404 Not Found</title>",
        "<title>Page Not Found</title>",
        "<title>410 Gone</title>",
        "<h1>404 error</h1>",
        "<p>Page Not Found</p>",
        "The page you requested could not be found",
        "This product is no longer available",
    ],
)
def test_each_error_pattern_is_detected(snippet):
    html = f"<html><body>{snippet}</body></html>"
    assert is_error_page(html) is True


def test_error_patterns_list_is_covered_by_parametrization():
    # Guard: if a new error pattern is added, the parametrized test must grow.
    assert len(ERROR_PAGE_PATTERNS) == 7
    assert len(AMBIGUOUS_ERROR_PAGE_PATTERNS) == 2


@pytest.mark.parametrize(
    "aside",
    [
        "Note: the silver finish is no longer available.",
        "The original 2019 model has been discontinued.",
    ],
)
def test_ambiguous_phrase_in_body_copy_of_a_real_page_is_not_an_error(aside):
    # #12: these phrases were unanchored, so a real product page mentioning
    # a dead variant read as a soft-404. That verdict is terminal in AUTO
    # mode — no escalation, no cache, no content — so the page was lost.
    page = (
        "<html><head><title>Canon RF 50mm f/1.2L USM Lens</title></head><body>"
        + ("<p>Full specifications and sample images. " * 400)
        + f"<p>{aside}</p></body></html>"
    )
    assert len(page) >= MIN_REAL_CONTENT_BYTES
    assert is_error_page(page) is False
    assert looks_like_real_content(page) is True
    assert is_cacheable_junk(page) is False


@pytest.mark.parametrize(
    "snippet",
    [
        "This item is no longer available for purchase",
        "This model has been discontinued",
    ],
)
def test_ambiguous_phrase_on_a_small_page_is_still_an_error(snippet):
    # The soft-404 case the phrases exist for: a discontinued product served
    # as HTTP 200 with a stub body. Below the size floor there is too little
    # else on the page for the phrase to be incidental.
    stub = f"<html><body><p>{snippet}</p></body></html>"
    assert len(stub) < MIN_REAL_CONTENT_BYTES
    assert is_error_page(stub) is True
    assert is_cacheable_junk(stub) is True


def test_unambiguous_error_wording_is_detected_at_any_size():
    # The strong patterns keep working on a big soft-404, so a site that
    # pads its 404 page past the size floor is still caught.
    big_404 = "<title>Page Not Found</title>" + ("filler " * 5000)
    assert len(big_404) >= MIN_REAL_CONTENT_BYTES
    assert is_error_page(big_404) is True


def test_error_page_even_when_large_is_not_real_content():
    # A soft-404 served as a big HTTP-200 page is still not real content.
    soft_404 = "<title>Page Not Found</title>" + ("filler " * 5000)
    assert len(soft_404) >= MIN_REAL_CONTENT_BYTES
    assert is_error_page(soft_404) is True
    assert looks_like_real_content(soft_404) is False


# --- is_cacheable_junk -----------------------------------------------


def test_real_page_is_not_cacheable_junk():
    assert is_cacheable_junk(BIG_REAL_PAGE) is False


def test_bot_page_is_cacheable_junk():
    assert is_cacheable_junk("<body>Too Many Requests</body>") is True


def test_error_page_is_cacheable_junk():
    assert is_cacheable_junk("<title>404 Not Found</title>") is True
