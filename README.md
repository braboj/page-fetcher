# pagefetch

_Fetch a page by the cheapest means that works._

Scraping a handful of sites means meeting a handful of defences. Most pages
are static HTML that `urllib` handles in about a second. A few render their
content in JavaScript. A few more sit behind Cloudflare or PerimeterX and
refuse anything that looks automated.

Reaching for a headless browser everywhere costs five to twenty seconds per
page for content a plain HTTP request would have returned. Reaching for
`urllib` everywhere fails on the sites that matter most. Hand-picking a
strategy per site works until the site changes.

`pagefetch` picks the tier for you. It starts with plain HTTP, inspects what
comes back, and escalates through headless and headed browsers only when the
response is a bot wall, an error, or implausibly short. Responses are cached
on disk, and junk is kept out of the cache rather than re-served from it.

- Fetch a URL as text or raw HTML through a four-tier escalation ladder
- Detect bot walls, throttle pages, and soft-404s in a response body
- Skip a tier that cannot help — a bot wall sends the fetcher past headless
  straight to a headed browser
- Ask for gzip and deflate and decode them, including from servers that
  compress without declaring it — and escalate rather than hand back a
  body in an encoding it cannot undo
- Reject anything that is not an http or https URL, before a request is
  made or a browser is launched
- Cache responses on disk, keyed by URL and content mode, with no TTL
- Self-heal a poisoned cache: junk entries are deleted on read and re-fetched
- Sweep accumulated junk on demand with `--clean-cache`
- Run without a single third-party package — tier 1 is standard library only
- Swap in a `FakeFetcher` so consuming code is testable with no network

## Quick start

Prerequisites: Python 3.10 or later. No other package is needed for tier 1.

```bash
git clone https://github.com/braboj/page-fetcher.git
cd page-fetcher
py -m pagefetch https://en.wikipedia.org/wiki/Web_scraping
```

That prints the page text to stdout — roughly 30 KB of it, starting:

```text
Web scraping - Wikipedia Jump to content Main menu Main menu move to
sidebar hide Navigation Main page Contents Current events Random article
```

To use it as a library, run Python from the repository root so
`import pagefetch` resolves:

```python
from pagefetch import NetworkFetcher, FetchOptions, ContentMode

fetcher = NetworkFetcher()
result = fetcher.fetch(
    "https://en.wikipedia.org/wiki/Web_scraping",
    FetchOptions(mode=ContentMode.HTML),
)
if result.ok:
    print(result.tier_used, len(result.content))
```

That prints `urllib 239100` — tier 1 handled it, and the raw HTML is about
239 KB.

The browser tiers are optional and are skipped when their library is absent
(see [Dependencies](#dependencies)).

## Usage

### Command line

Fetch one page as text, letting the fetcher pick its own tier:

```bash
py -m pagefetch https://en.wikipedia.org/wiki/Web_scraping
```

Stdout carries the stripped page text. A successful tier 1 fetch says
nothing on stderr — the tiers only narrate when they escalate:

```text
[urllib] Not real content (559 bytes) — escalating
[auto] Skipping Playwright (bot protection), trying Nodriver...
```

Force a specific tier, change the output mode, or bypass the cache:

```bash
py -m pagefetch <url> --html       # raw HTML instead of stripped text
py -m pagefetch <url> --js         # force Playwright
py -m pagefetch <url> --nodriver   # force Nodriver (headed)
py -m pagefetch <url> --uc         # force SeleniumBase UC
py -m pagefetch <url> --wait 5000  # extra post-load wait (ms)
py -m pagefetch <url> --no-cache   # refetch, ignoring any cached copy
py -m pagefetch <url> --cache-dir DIR
```

Fetch many pages in one browser session — this is what makes bot-protected
batches affordable, since the browser launches once rather than per URL:

```bash
py -m pagefetch --batch urls.txt                    # one URL per line
py -m pagefetch --batch -                           # from stdin
py -m pagefetch url1 url2 url3                      # from arguments
py -m pagefetch --batch urls.txt --output-dir out/  # one file per URL
```

Three bot-protected pages take about 16 seconds as a batch, against roughly
27 seconds fetched one at a time.

Purge junk that accumulated in the cache before the current guards existed:

```bash
py -m pagefetch --clean-cache
py -m pagefetch --clean-cache --dry-run   # list junk, delete nothing
```

`--dry-run` prints the entries it would remove and exits without deleting.

### Exit codes

| Code | Meaning                                                     |
| ---- | ----------------------------------------------------------- |
| 0    | Every requested URL returned content                        |
| 1    | Nothing came back, or the arguments were rejected           |
| 2    | A batch returned content for some URLs but not all          |

A failed fetch writes nothing to stdout, so `py -m pagefetch "$url" >
page.txt && process page.txt` stops rather than processing an empty file.
Partial batch failure has its own code because "some pages are missing" and
"nothing came back" usually call for different handling.

### Library

Inject a `PageSource` into your own code so it can be faked in tests:

```python
def scrape(source: PageSource, url: str) -> str:
    return source.fetch(url, FetchOptions(mode=ContentMode.HTML)).content


# in tests — no network, no browser:
from pagefetch import FakeFetcher

assert scrape(FakeFetcher({url: "<html>...</html>"}), url) == "<html>...</html>"
```

| Symbol           | Purpose                                         |
| ---------------- | ----------------------------------------------- |
| `PageSource`     | Abstract base — the transport interface         |
| `NetworkFetcher` | Real fetcher with four-tier escalation          |
| `FakeFetcher`    | Test double backed by a URL→content map         |
| `FileCache`      | On-disk response cache (configurable directory) |
| `FetchOptions`   | `mode`, `transport`, `wait_ms`, `use_cache`     |
| `FetchResult`    | `url`, `content`, `tier_used`, `ok`             |
| `ContentMode`    | `TEXT` (stripped) / `HTML` (raw)                |
| `Transport`      | `AUTO` / `PLAYWRIGHT` / `NODRIVER` / `UC`       |
| `is_bot_blocked` | Pure bot-detection predicate                    |

Point the cache somewhere specific:

```python
from pathlib import Path
from pagefetch import NetworkFetcher, FileCache

fetcher = NetworkFetcher(cache=FileCache(cache_dir=Path("/my/cache")))
```

## Project structure

| Path                     | Purpose                                            |
| ------------------------ | -------------------------------------------------- |
| `pagefetch/`             | The package — import this                          |
| `pagefetch/source.py`    | `PageSource` ABC and the option / result types     |
| `pagefetch/network.py`   | `NetworkFetcher` — the four-tier escalation ladder |
| `pagefetch/detection.py` | Bot-wall, error-page, and real-content predicates  |
| `pagefetch/cache.py`     | `FileCache` — on-disk cache and junk sweep         |
| `pagefetch/chrome.py`    | Chrome / CDP launch helpers for the browser tiers  |
| `pagefetch/fake.py`      | `FakeFetcher` test double                          |
| `pagefetch/__main__.py`  | CLI entry point — a thin wrapper over the library  |
| `pagefetch/tests/`       | pytest suite, including captured HTML fixtures     |
| `docs/decisions/`        | Architecture Decision Records                      |
| `docs/audits/`           | 360-degree audit reports, one per run              |
| `docs/ONBOARDING.md`     | Fresh clone to a passing gate                      |
| `docs/PLAYBOOK.md`       | Operational reference for recurring tasks          |
| `docs/dev-journal.md`    | Session log — what changed and why                 |
| `CLAUDE.md`              | Project rules for AI agents                        |
| `pyproject.toml`         | Package metadata and every tool's configuration    |

## Development setup

```bash
git clone https://github.com/braboj/page-fetcher.git
cd page-fetcher
py -m pip install -e ".[dev]"
pre-commit install
py -m pytest
```

The suite runs in a couple of seconds and touches nothing outside the
repository: no network, no browser, and no query of the host's process
list. The escalation logic is tested by stubbing the four tier methods.
The browser-tier method bodies require headed Chrome and are validated by
hand.

To exercise the browser tiers locally, add the optional engines:

```bash
py -m pip install -e ".[browsers]"
playwright install chromium
```

### The gate

`pre-commit install` wires the first four of these to run on every commit.
CI repeats all of them on every pull request, because hooks can be skipped
with `--no-verify`. Run any one directly:

```bash
py -m ruff check .          # lint
py -m ruff format --check . # formatting, including Python in this README
py -m mypy                  # type check
py -m pytest --cov=pagefetch
```

Coverage sits at roughly 65% with a floor of 63% that fails the build if it
drops. What remains uncovered is the browser-tier method bodies, which need
a headed Chrome and cannot run in CI; everything reachable without one is
tested, including the batch session lifecycle. See
[ADR-002](docs/decisions/002-python-toolchain-and-ci.md) for why the floor
is measured against reality rather than set to an aspiration.

## Configuration reference

`cache_dir` is the only configurable value. It resolves in this precedence,
highest first:

| Source                       | Type | Default              | Notes                       |
| ---------------------------- | ---- | -------------------- | --------------------------- |
| `--cache-dir DIR`            | path | unset                | CLI flag, one invocation    |
| `cache_dir=` constructor arg | path | unset                | Programmatic use            |
| `PAGEFETCH_CACHE_DIR`        | path | unset                | Environment variable        |
| built-in default             | path | `./.cache/pagefetch` | Relative to the working dir |

The CLI flag and the constructor argument are the same tier — the flag is
how the CLI passes the explicit argument. The environment variable lets a
consuming project point every entry point at one cache directory without the
package hardcoding any project layout.

The resolved directory is validated at construction, not at first write. A
path that is an existing file, or whose nearest existing ancestor is missing
or read-only, raises a `ValueError` naming the source that supplied it. The
directory itself is created lazily on first write.

Configuration is deliberately lightweight: one environment variable and one
CLI flag, validated with the standard library. A typed settings object
(Pydantic) and `.env` loading are not used — they would add dependencies
that break the standard-library-only contract for tier 1, and they are
overkill for a single knob. Revisit if the package grows several config
values (user agent, timeouts, tier toggles, concurrency), at which point a
typed settings object would be introduced across all of them.

## How it works

```text
urllib (plain HTTP, ~1s)
  +- success -> done
  +- HTTP error (404, timeout) -> Playwright
  +- bot protection (captcha, 403) -> skip Playwright -> Nodriver
                                            |
Playwright (headless Chromium, ~5-9s)       |
  +- success -> done                        |
  +- bot detection / error -> Nodriver <----+
                |
Nodriver (headed Chrome via CDP, ~6-8s)
  +- success -> done
  +- failure -> UC
                |
SeleniumBase UC (headless stealth Chrome, ~18-24s)
  +- success -> done
  +- failure -> all tiers failed (content="")
```

| Tier | Engine          | Speed   | Mode     | Use case                               |
| ---- | --------------- | ------- | -------- | -------------------------------------- |
| 1    | urllib          | ~1s     | —        | Static HTML (most sites)               |
| 2    | Playwright      | ~5-9s   | headless | JS-rendered content                    |
| 3    | Nodriver        | ~6-8s   | headed   | Bot-protected sites (no driver binary) |
| 4    | SeleniumBase UC | ~18-24s | headless | Headless-only fallback                 |

When urllib detects bot protection, Playwright is skipped — it would fail
the same way — and the fetcher goes straight to Nodriver, then UC.

### Bot detection

A response is treated as a bot-detection interstitial when it matches a
known pattern (Cloudflare "Just a moment" / `challenge-platform`, "Checking
your browser", 403/429/Access Denied titles, "Too Many Requests" /
rate-limit / "unusual traffic" throttles, PerimeterX markers, cookie walls)
or is a short HTML page with a meta-refresh redirect. See `detection.py`.

`looks_like_real_content(html, min_bytes=10_000)` is the broader gate: a
response that is bot-blocked, a 404/gone error page, or implausibly short is
not real content. This catches throttle and error stubs carrying no
recognizable bot text — a retailer's 7-8 KB "slow down" page, for instance.
Such responses are never cached or re-served, and in auto mode they trigger
escalation to a browser tier instead of being accepted.

`is_error_page(html)` recognizes 404/410 and soft-404 bodies, where a
discontinued product is served as HTTP 200 with a "page not found" body. A
genuine 404 is terminal: it is not cached and does not escalate, since every
tier returns the same error.

Because that verdict is terminal, two phrases are held to a higher bar. "No
longer available" and "has been discontinued" mean the page is gone on a
stub and mean one variant is out of stock in the body copy of a perfectly
good product page, so they count only below the size floor, where there is
too little else on the page for the phrase to be incidental. Everything
else — a 404 or 410 title, "page not found", "the page you requested could
not be found" — is decisive at any size. The same reasoning applies to
throttle detection: "rate limit" on its own is ordinary technical prose and
only registers alongside a word that a page actually being throttled would
use.

### Event-driven waits

Browser tiers poll rather than sleeping a fixed time. They wait for
`document.readyState === "complete"`, poll the page source with exponential
backoff (0.5s to a 2s cap, 15s timeout) until bot-detection patterns
disappear, then scroll and poll `scrollHeight` until it stabilizes. This
adapts to the actual security handshake time instead of guessing it.

### Cache

Responses are cached by `sha256(url)[:16]` plus a `.txt` or `.html` suffix.
Text and HTML variants are cached separately. The key scheme is fixed —
changing it would invalidate existing caches.

Only real content is cached. On read, a cached body that is recognizably a
bot or throttle page, or a 404/gone error page, is ignored, deleted, and
re-fetched — so a cache poisoned before this guard existed, or one whose
product was discontinued after caching, self-heals on the next fetch rather
than re-serving junk. `--clean-cache` does the same sweep in bulk. The junk
definition (`is_cacheable_junk`) is shared by the read-time scrub and the
sweep, so the two never drift.

The cache has no TTL — validity is decided by content, not age. Specs rarely
change, discontinuation surfaces as a 404, and price refreshes are
deliberate `--no-cache` passes.

`--no-cache` is a refresh, not a bypass: it decides whether a cached body is
_served_, not whether a fresh one is _stored_. The fetch ignores whatever is
on disk and then replaces it, so the next ordinary fetch gets the new copy
rather than the stale one it just skipped. Every path honors this the same
way — single, batch, and a batch holding a persistent browser.

## Dependencies

| Dependency        | Tier | Required | License    |
| ----------------- | ---- | -------- | ---------- |
| `urllib` (stdlib) | 1    | always   | PSF        |
| `playwright`      | 2    | optional | Apache-2.0 |
| `nodriver`        | 3    | optional | AGPL-3.0   |
| `seleniumbase`    | 4    | optional | MIT        |

All three live in the `browsers` extra (`pip install ".[browsers]"`).
Missing optional dependencies are handled gracefully — the tier is skipped
with a message on stderr.

**On `nodriver` and the AGPL.** `pagefetch` is MIT licensed and stays MIT.
It does not vendor, bundle, or redistribute `nodriver`; the tier 3 import is
lazy and is skipped when the package is absent, so installing `pagefetch`
alone pulls in no AGPL code. The AGPL becomes your concern if you install
`nodriver` and then distribute a network service built on the combination —
the scenario section 13 of the AGPL covers, which obliges you to offer your
service's source to its users. If that applies to you, install only
`playwright` and `seleniumbase` and leave tier 3 out; the ladder degrades to
three tiers and skips Nodriver with a stderr message.

## Performance history

- **v1** — Playwright-only, `networkidle` wait. ~5-9s everywhere; failed on
  bot-protected sites.
- **v2** — three tiers (urllib, Playwright, UC). Normal ~1s; bot ~27s.
- **v3** — skip Playwright on bot detection; `domcontentloaded` over
  `networkidle`; event-driven UC waits. Normal ~1s, JS ~5-9s, bot ~18-24s.
- **v4** — persistent-browser batch mode. Three bot-protected pages: ~60s to
  ~27s.
- **v5** — Nodriver tier (CDP, no driver binary), preferred over UC in auto.
  Three bot-protected pages: 27s to 16s.
- **v6** — refactored from a single 748-line script into this package
  (`PageSource` ABC, `NetworkFetcher`, `FakeFetcher`), CLI wrapping the
  class. Behavior preserved.
- **v7** — throttle pages no longer poison the cache: broader bot detection
  (429 / rate-limit / "unusual traffic" / PerimeterX / Cloudflare challenge
  runtime) and a `looks_like_real_content` size floor, so implausibly short
  stubs escalate instead of being cached.
- **v8** — 404 / gone handling and cache validity by content. A 404, 410, or
  soft-404 is terminal; cached error bodies self-heal on read. No TTL.
- **v9** — cache cleanup: junk entries are deleted rather than just ignored
  when scrubbed on read, and `--clean-cache` sweeps on demand.

### Sites tested

| Site               | Tier       | Notes                                   |
| ------------------ | ---------- | --------------------------------------- |
| allphotolenses.com | urllib     | static HTML                             |
| ttartisan.com      | Playwright | JS-rendered (query-param routing)       |
| zyoptics.net       | Nodriver   | SiteGround captcha + bot protection     |
| bhphotovideo.com   | Nodriver   | bypasses Cloudflare (headed)            |
| viltrox.com        | urllib     | static HTML + Shopify JSON              |
| mobile01.com       | UC         | Akamai blocks headless browsers         |
| adorama.com        | BLOCKED    | PerimeterX "Press & Hold" — manual only |

## URL schemes, and what this is not

Every entry point rejects a URL whose scheme is not `http` or `https`,
raising `ValueError` before any request or browser launch:

```text
>>> NetworkFetcher().fetch("file:///etc/passwd")
ValueError: 'file:///etc/passwd' uses the 'file' scheme; pagefetch only
fetches http, https
```

`urllib` would otherwise read that file and hand it back as page content.

**This is a scheme allowlist, not SSRF protection.** It does nothing to
stop an `http://` request to `localhost`, `169.254.169.254`, or anything
else on a private network. If the URLs you pass originate from user input,
a config you do not control, or a redirect chain, you still need your own
filter — resolving the host and checking the address, re-checked after
every redirect. `require_supported_scheme` and `ALLOWED_SCHEMES` are
exported so you can apply the same check at your own boundary.

That is a deliberate boundary rather than an omission; [ADR-003](docs/decisions/003-url-scheme-allowlist.md)
records why blocking private ranges here would break ordinary intranet and
localhost fetching while offering a guarantee this layer cannot honestly
make.

## Known limitations

- Nodriver requires headed mode — a Chrome window opens, so it is unusable
  in CI.
- UC mode costs ~18-24s minimum from Chrome launch overhead.
- PerimeterX "Press & Hold" (Adorama) blocks every automated tier.
- Single-URL mode launches a new browser per call; use batch mode for many
  URLs.

## Links

- [Onboarding](docs/ONBOARDING.md) — fresh clone to a passing gate
- [Playbook](docs/PLAYBOOK.md) — git workflow, adding a tier or a detection
  pattern, the quality checks, maintenance
- [Dev journal](docs/dev-journal.md) — what changed each session and why
- [Audits](docs/audits/) — 360-degree assessments, one report per run
- [Architecture Decision Records](docs/decisions/) —
  [ADR-001](docs/decisions/001-extract-pagefetch-into-standalone-repo.md)
  records this package's extraction from its original home, and
  [ADR-002](docs/decisions/002-python-toolchain-and-ci.md) the toolchain
  and CI gate
- Upstream history: the package grew inside
  [Imbra-Ltd/wuseria](https://github.com/Imbra-Ltd/wuseria) as
  `tools/pagefetch/`, where two earlier decision records still cover it —
  [ADR-035](https://github.com/Imbra-Ltd/wuseria/blob/main/docs/decisions/035-pagefetch-package-and-brandkit.md)
  on the package extraction and the standard-library-only contract, and
  [ADR-037](https://github.com/Imbra-Ltd/wuseria/blob/main/docs/decisions/037-pagefetch-cache-validity-no-ttl.md)
  on content-based cache validity

## License

MIT — see [LICENSE](LICENSE).

The optional `nodriver` dependency is AGPL-3.0 and is not covered by this
license; see [Dependencies](#dependencies) for what that means if you
distribute a service built on tier 3.
