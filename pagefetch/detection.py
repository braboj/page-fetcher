"""Bot-protection detection.

Pure functions that decide whether a fetched response is a bot-detection
interstitial (Cloudflare, captcha, 403 page) rather than real content.
This drives the escalation decision in NetworkFetcher: a urllib response
that looks bot-blocked skips Playwright and goes straight to a real
browser tier.
"""

import re

# Patterns that indicate bot protection (triggers escalation).
BOT_DETECTION_PATTERNS = [
    r"<title>403\b",
    r"<title>Access Denied",
    # Cloudflare interstitial. Anchored to the canonical CF phrasing
    # ("Checking your browser before accessing …") so the substring does not
    # false-match on ad-blocker help text like "checking your browser
    # extensions and settings" embedded in real content pages
    # (Imbra-Ltd/wuseria#870).
    r"Checking your browser\b[^.]{0,40}\bbefore\b",
    r"Checking the site connection security",
    r"Enable JavaScript and cookies to continue",
    r"Attention Required.*Cloudflare",
    r"Just a moment\.\.\.",
    r"Verifying you are human",
    r"Please allow cookies",
    r"This page requires cookies to be enabled",
    # Larger throttle / rate-limit interstitials that carry no meta-refresh
    # and are too big for the <500-char short-circuit (e.g. B&H ~7-8 KB
    # throttle pages, Cloudflare challenge runtime, generic 429 pages).
    r"<title>429\b",
    r"Too Many Requests",
    # "rate limit" is ordinary technical prose — an article about API design
    # says it in passing. Require a word that only a page *being* throttled
    # uses, so "discussing rate limits in REST APIs" no longer reads as a
    # throttle interstitial. Real throttle bodies are still caught by the
    # 429 title, "Too Many Requests", the PerimeterX markers, and the
    # MIN_REAL_CONTENT_BYTES floor.
    r"rate.?limit\w*\b[^.<]{0,40}\b(?:exceeded|reached|try again)"
    r"|\b(?:exceeded|reached)\b[^.<]{0,40}\brate.?limit",
    r"unusual traffic",
    r"detected (?:a|an) (?:translation|automated)",
    r"challenge-platform",  # Cloudflare challenge runtime script
    r"cf-challenge",
    r"px-captcha",  # PerimeterX
    r"_pxhd",  # PerimeterX header/cookie marker in throttle bodies
]

# Below this size a response is almost never a real content page — it is a
# throttle, error, or challenge stub. Conservative on purpose: real content
# pages on the sites we scrape are comfortably larger, while throttle stubs
# (e.g. the B&H ~7-8 KB page that carries no spec table) fall under it.
MIN_REAL_CONTENT_BYTES = 10_000

# A meta-refresh in a page this small is a captcha redirect rather than a
# real page that happens to redirect — big pages with a meta-refresh are
# not short-circuited.
META_REFRESH_MAX_BYTES = 500

# Patterns that indicate a "not found" / gone error page. These catch both
# hard 404s (HTTP 404 body) and soft-404s — a discontinued product served
# with HTTP 200 but a "no longer available" / "page not found" body. A
# discontinued lens's page often becomes one of these, so detecting them on
# read lets a stale cache self-heal (the product status really changed).
ERROR_PAGE_PATTERNS = [
    r"<title>\s*404\b",
    r"<title>[^<]*\b(?:Page )?Not Found\b",
    r"<title>\s*410\b",
    r"\b404\b[^<]{0,40}\b(?:Not Found|error)\b",
    r"Page Not Found",
    r"page (?:you (?:requested|are looking for)|could not be found)",
    r"This product is no longer available",
]

# Phrases that mean "this page is gone" on an error stub and "one variant is
# out of stock" in the body copy of a perfectly good product page. A real
# 17 KB lens page reading "the silver finish is no longer available" was
# classified as a soft-404 and failed terminally — no escalation, no cache,
# no content — which is the worst way to lose a page that was there all
# along. They carry weight only below MIN_REAL_CONTENT_BYTES, where there is
# too little else on the page for the phrase to be incidental.
AMBIGUOUS_ERROR_PAGE_PATTERNS = [
    r"no longer available",
    r"has been discontinued",
]


def _matches_any(patterns: list[str], html: str) -> bool:
    """True if any pattern hits the raw head or the de-tagged text.

    Both forms are scanned because bot and error pages embed their text in
    JS/CSS-heavy wrappers: the raw head catches markup-bound markers (a
    <title>, a script src), the de-tagged text catches prose broken across
    tags.
    """
    head = html[:5000]
    text = re.sub(r"<[^>]+>", " ", html[:20000])
    return any(
        re.search(pattern, head, re.IGNORECASE)
        or re.search(pattern, text, re.IGNORECASE)
        for pattern in patterns
    )


def is_bot_blocked(html: str) -> bool:
    """Return True if the response HTML looks like a bot-detection page."""
    # Very short HTML with a meta-refresh is a captcha redirect.
    if (
        len(html) < META_REFRESH_MAX_BYTES
        and "meta" in html
        and "refresh" in html.lower()
    ):
        return True
    return _matches_any(BOT_DETECTION_PATTERNS, html)


def looks_like_real_content(html: str, min_bytes: int = MIN_REAL_CONTENT_BYTES) -> bool:
    """Return True if the response is plausibly a real content page.

    A response that is bot-blocked, or implausibly short, is not real
    content — it should neither be cached nor re-served, and in AUTO mode it
    should trigger escalation to a browser tier. This is the safety net for
    throttle/challenge pages that slip past the pattern list because they
    carry no recognizable bot-detection text.
    """
    if is_bot_blocked(html) or is_error_page(html):
        return False
    return len(html) >= min_bytes


def is_error_page(html: str) -> bool:
    """Return True if the response looks like a 404 / gone error page.

    Covers hard 404s and soft-404s (HTTP 200 with a "not found" / "no longer
    available" body). Used to keep error pages out of the cache and to scrub
    a previously-cached error body so it self-heals on the next fetch.

    A verdict here is terminal in AUTO mode — the fetcher does not escalate,
    because every tier would return the same error — so the ambiguous
    phrases are held to the extra size condition described at
    AMBIGUOUS_ERROR_PAGE_PATTERNS rather than being allowed to fail a real
    page on one sentence of body copy.
    """
    if _matches_any(ERROR_PAGE_PATTERNS, html):
        return True
    return len(html) < MIN_REAL_CONTENT_BYTES and _matches_any(
        AMBIGUOUS_ERROR_PAGE_PATTERNS, html
    )


def is_cacheable_junk(html: str) -> bool:
    """Return True if a body should never be served from cache.

    A bot/throttle page or a 404/gone error page is junk: it must not be
    re-served, and it can be swept from the cache. This is the single
    definition of "junk" shared by the read-time scrub and the cleanup
    sweep — keep them in lock-step here, not duplicated at the call sites.
    """
    return is_bot_blocked(html) or is_error_page(html)


def html_to_text(html: str) -> str:
    """Strip script/style/tags and collapse whitespace to plain text."""
    # HTML5 end tags may carry whitespace and even attributes before the
    # ">" — browsers parse `</script >` and `</script foo="bar">` as end
    # tags and ignore the extra. Anchoring on a bare "</script>" left such
    # blocks unmatched; the outer tag strip then removed only the tags and
    # the script body survived as "text", polluting extracted content with
    # JavaScript. Matching everything up to ">" also matches a malformed
    # `</scriptfoo>`, which is a deliberate trade: over-stripping junk from
    # scraped text is harmless, under-stripping is not.
    text = re.sub(
        r"<script[^>]*>.*?</script[^>]*>", "", html, flags=re.DOTALL | re.IGNORECASE
    )
    text = re.sub(
        r"<style[^>]*>.*?</style[^>]*>", "", text, flags=re.DOTALL | re.IGNORECASE
    )
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()
