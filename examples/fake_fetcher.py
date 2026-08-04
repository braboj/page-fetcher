"""Test consuming code with no network and no browser.

The README claims that code taking a `PageSource` can be tested against a
`FakeFetcher`. This is that claim as something you can run: `mentions`
below never learns which implementation it was handed.

The assertions are the point rather than decoration — this file is the test
pattern a consumer would write, executed as a script.
"""

from pagefetch import ContentMode, FakeFetcher, FetchOptions, PageSource

# Map values are page bodies — the HTML a real fetch would have returned.
# TEXT mode derives from them exactly as NetworkFetcher does, by stripping
# the markup, so the double and the real fetcher disagree about nothing that
# matters here.
PAGES = {
    "https://example.com/x100vi": (
        "<html><head><title>Fujifilm X100VI</title></head><body>"
        "<h1>Fujifilm X100VI</h1>"
        "<p>A 40MP sensor in a fixed-lens compact.</p>"
        '<a href="/accessories">Accessories</a>'
        "</body></html>"
    ),
    "https://example.com/x100v": (
        "<html><head><title>Fujifilm X100V</title></head><body>"
        "<h1>Fujifilm X100V</h1>"
        "<p>A 26MP sensor in a fixed-lens compact.</p>"
        "</body></html>"
    ),
}


def mentions(source: PageSource, url: str, term: str) -> bool:
    """Report whether a page's visible text mentions a term.

    Consuming code of the kind this package exists to serve: it depends on
    the `PageSource` contract and nothing else — no `NetworkFetcher`
    import, no cache, no knowledge of which tier answered.
    """
    result = source.fetch(url, FetchOptions(mode=ContentMode.TEXT))
    if not result.ok:
        return False
    return term.lower() in result.content.lower()


def main() -> None:
    """Exercise `mentions` against a FakeFetcher and report what happened."""
    fetcher = FakeFetcher(PAGES)

    in_body = mentions(fetcher, "https://example.com/x100vi", "40MP")
    print(f"visible text mentions '40MP': {in_body}")
    assert in_body

    # TEXT mode strips markup, so an attribute name is not visible text.
    # Consuming code that searched the raw HTML instead would match here and
    # report a page that says nothing of the sort.
    in_markup = mentions(fetcher, "https://example.com/x100vi", "href")
    print(f"visible text mentions 'href': {in_markup}")
    assert not in_markup

    # An unmapped URL is what a failed fetch looks like: ok=False, empty
    # content, no exception. `mentions` handles it the same way it would
    # handle a real page that every tier failed to reach.
    missing = fetcher.fetch("https://example.com/nope")
    print(
        f"unmapped URL: ok={missing.ok} "
        f"tier_used={missing.tier_used!r} content={missing.content!r}"
    )
    assert not missing.ok

    # HTML mode hands the body back verbatim.
    url = "https://example.com/x100v"
    raw = fetcher.fetch(url, FetchOptions(mode=ContentMode.HTML))
    print(f"HTML mode returns the body verbatim: {raw.content == PAGES[url]}")

    # The double records every URL it was asked for, in order, so a test can
    # assert on call behaviour and not only on return values.
    print(f"calls: {fetcher.calls}")


if __name__ == "__main__":
    main()
