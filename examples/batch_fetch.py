"""Fetch a list of URLs in one call and grade the outcome.

`fetch_batch` returns one `FetchResult` per input URL, in the input order,
whether or not each one succeeded — a failure is a result with `ok=False`,
never a gap in the list and never an exception.

Driven here by `FakeFetcher` so it runs offline. Against `NetworkFetcher`
the same call reuses one browser session for the whole list rather than
launching a browser per URL; the result list reads identically.
"""

from pagefetch import ContentMode, FakeFetcher, FetchOptions, FetchResult

PAGES = {
    "https://example.com/x100vi": "<html><body><p>40MP APS-C.</p></body></html>",
    "https://example.com/x100v": "<html><body><p>26MP APS-C.</p></body></html>",
    "https://example.com/gfx100": "<html><body><p>102MP medium.</p></body></html>",
}

# The third URL is deliberately not in the map, which is how this example
# reaches the partial-failure case without a network to fail against.
URLS = [
    "https://example.com/x100vi",
    "https://example.com/x100v",
    "https://example.com/nothing-here",
    "https://example.com/gfx100",
]


def exit_code(results: list[FetchResult]) -> int:
    """Grade a batch the way the CLI does — see the README's exit codes.

    0 when every URL returned content, 1 when none did, 2 when some did.
    "Some pages are missing" and "nothing came back" usually call for
    different handling in a pipeline, so they are not the same code.
    """
    if not results:
        return 0
    failed = sum(1 for r in results if not r.ok)
    if failed == 0:
        return 0
    return 1 if failed == len(results) else 2


def main() -> None:
    """Fetch the batch, print one row per result, then grade it."""
    fetcher = FakeFetcher(PAGES)
    results = fetcher.fetch_batch(URLS, FetchOptions(mode=ContentMode.TEXT))

    print(f"{'url':<38} {'ok':<6} {'tier':<6} chars")
    for result in results:
        print(
            f"{result.url:<38} {result.ok!s:<6} "
            f"{result.tier_used:<6} {len(result.content)}"
        )

    # Order is guaranteed to match the input, so the two lists can be zipped
    # without matching on URL.
    print(f"order preserved: {[r.url for r in results] == URLS}")
    print(f"exit code: {exit_code(results)}")


if __name__ == "__main__":
    main()
