"""Store, re-read and sweep cached page bodies.

`FileCache` is the on-disk cache `NetworkFetcher` reads and writes. Driving
it directly shows the three behaviours the README calls out — keys derived
from the URL, one entry per content mode, and the sweep that lets a
poisoned cache heal itself — with no fetch involved.

Everything happens in a temporary directory, so running this never touches
the cache your own fetches use.
"""

import tempfile
from pathlib import Path

from pagefetch import ContentMode, FileCache, is_bot_blocked, is_cacheable_junk

URL = "https://example.com/x100vi"
BLOCKED_URL = "https://example.com/blocked"

PAGE_TEXT = "Fujifilm X100VI A 40MP sensor in a fixed-lens compact."
PAGE_HTML = "<html><body><p>A 40MP sensor in a fixed-lens compact.</p></body></html>"

# A Cloudflare interstitial of the kind that reached the cache before the
# current write-time guards existed. Sweeping is what clears the ones
# already on disk.
BOT_WALL = (
    "<html><head><title>Just a moment...</title></head>"
    "<body>Checking your browser before accessing example.com</body></html>"
)


def classify(body: str) -> str | None:
    """Return a reason when a cached body is junk, or None to keep it.

    The verdict comes from `is_cacheable_junk` alone — the package's single
    definition of junk, shared with the read-time scrub. Only the label is
    worked out here, and only for bodies already judged junk, so this can
    never disagree with the fetcher about what is worth keeping.
    """
    if not is_cacheable_junk(body):
        return None
    return "bot-blocked" if is_bot_blocked(body) else "404/error"


def main() -> None:
    """Write two entries plus a bot wall, then sweep the wall out."""
    with tempfile.TemporaryDirectory() as tmp:
        cache = FileCache(cache_dir=Path(tmp))

        # The key is sha256(url) truncated to 16 hex characters, plus a
        # suffix per content mode. One URL fetched both ways occupies two
        # entries, and neither can collide with another URL's.
        cache.write(URL, ContentMode.TEXT, PAGE_TEXT)
        cache.write(URL, ContentMode.HTML, PAGE_HTML)
        # Labelled "entry" and not "key" on purpose: a line reading
        # `key: <16 hex chars>` is what gitleaks' generic-api-key rule
        # looks for, and this output is pasted into examples/README.md,
        # where it failed the secret scan.
        print(f"text entry: {cache.key(URL, ContentMode.TEXT).name}")
        print(f"html entry: {cache.key(URL, ContentMode.HTML).name}")

        # A hit returns the stored body; a miss returns None rather than
        # raising, so "not cached yet" is an ordinary branch for the caller.
        print(f"hit:  {cache.read(URL, ContentMode.TEXT)!r}")
        print(f"miss: {cache.read('https://example.com/other', ContentMode.TEXT)!r}")

        cache.write(BLOCKED_URL, ContentMode.HTML, BOT_WALL)
        print(f"entries: {[p.name for p in cache.entries()]}")

        # A dry run reports what it would delete and deletes nothing, which
        # is what `--clean-cache --dry-run` does from the command line.
        dry = cache.clean(classify, dry_run=True)
        print(f"dry run: would remove {[(p.name, why) for p, why in dry.removed]}")
        print(f"dry run: kept {dry.kept}, files still on disk {len(cache.entries())}")

        swept = cache.clean(classify)
        print(f"sweep:   removed {[(p.name, why) for p, why in swept.removed]}")
        print(f"sweep:   kept {swept.kept}, files still on disk {len(cache.entries())}")


if __name__ == "__main__":
    main()
