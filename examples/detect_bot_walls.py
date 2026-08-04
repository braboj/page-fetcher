"""Decide whether a response is a page or a wall, without fetching one.

The detection predicates are pure functions over a response body — the same
ones that decide, inside `NetworkFetcher`, whether a tier-1 response is
returned, escalated to a browser, or given up on. Running them directly is
the cheapest way to see why a page took the route it did.

The first sample is a real page captured into `tests/fixtures/`; the rest
are the smallest bodies that reach each verdict. Nothing here touches the
network.
"""

from pathlib import Path

from pagefetch import (
    MIN_REAL_CONTENT_BYTES,
    html_to_text,
    is_bot_blocked,
    is_error_page,
    looks_like_real_content,
)

# Resolved from this file rather than the working directory, so the example
# runs the same from anywhere.
FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "tests"
    / "fixtures"
    / "dpreview_specifications.html"
)

BOT_WALL = (
    "<html><head><title>Just a moment...</title></head>"
    "<body>Checking your browser before accessing example.com</body></html>"
)

SOFT_404 = "<html><head><title>Page Not Found</title></head><body></body></html>"

# "no longer available" is a gone page on a stub and body copy about one
# variant on a real product page. It counts only below
# MIN_REAL_CONTENT_BYTES, because an error verdict is terminal — no
# escalation, no cache — and a real page lost to one sentence is the worst
# failure this package has. The two samples below differ only in size.
GONE_STUB = "<html><body>The silver finish is no longer available.</body></html>"
LONG_PAGE = (
    "<html><body><h1>Fujifilm X100VI</h1>"
    "<p>The silver finish is no longer available.</p>"
    + "<p>Sensor 40MP. Mount fixed. Weight 521g.</p>" * 300
    + "</body></html>"
)


def report(label: str, html: str) -> None:
    """Print one row of verdicts for a response body."""
    print(
        f"{label:<32} {len(html):>7} {is_bot_blocked(html)!s:<7}"
        f"{is_error_page(html)!s:<7}{looks_like_real_content(html)}"
    )


def main() -> None:
    """Run every predicate over each sample and show the extracted text."""
    captured = FIXTURE.read_text(encoding="utf-8", errors="replace")

    print(f"real-content floor: {MIN_REAL_CONTENT_BYTES} bytes\n")
    print(f"{'sample':<32} {'bytes':>7} {'bot':<7}{'error':<7}real")
    report("captured page (dpreview)", captured)
    report("cloudflare interstitial", BOT_WALL)
    report("soft 404", SOFT_404)
    report("'no longer available' stub", GONE_STUB)
    report("same sentence, real page", LONG_PAGE)

    # What TEXT mode hands a caller: the same body with script, style and
    # tags gone and whitespace collapsed.
    text = html_to_text(captured)
    opening = " ".join(text.split()[:13])
    print(f"\nde-tagged text: {len(text)} chars, starting:\n{opening}")


if __name__ == "__main__":
    main()
