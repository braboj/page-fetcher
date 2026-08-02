# pagefetch

![CI](https://github.com/braboj/page-fetcher/actions/workflows/ci.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)

_Fetch a page by the cheapest means that works - built for research and
other low-volume work, not for bulk scraping._

A plain HTTP request is enough for static HTML. Pages that render in
JavaScript, or that block anything that looks automated, need a browser.
pagefetch selects the transport per request. It issues a plain HTTP request,
inspects the response body, and escalates to a headless and then a headed
browser only when the body is a bot wall, an error page, or too small to be
plausible content.

## Features

- Fetch a URL as text or raw HTML through a four-tier escalation ladder
- Detect bot walls, throttle pages, and soft-404s in a response body
- Skip a tier that cannot help — a bot wall sends the fetcher past headless
  straight to a headed browser
- Fetch many pages in one browser session, so the browser launches once
  rather than per URL
- Ask for gzip and deflate and decode them, including from servers that
  compress without declaring it
- Reject anything that is not an http or https URL, before a request is
  made or a browser is launched
- Cache responses on disk, keyed by URL and content mode, with no TTL
- Self-heal a poisoned cache: junk entries are deleted on read and
  re-fetched, or swept in bulk with `--clean-cache`
- Run without a single third-party package — tier 1 is standard library only
- Swap in a `FakeFetcher` so consuming code is testable with no network

## Quick start

Prerequisites: Python 3.10 or later.

```bash
git clone https://github.com/braboj/page-fetcher.git
cd page-fetcher
py -m pagefetch https://en.wikipedia.org/wiki/Web_scraping
```

That prints the page text to stdout — tens of kilobytes of it, starting:

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

That prints the tier that served the page and the size of the body — for
this URL, `http` and a few hundred kilobytes of raw HTML.

## Usage

### Command line

Fetch one page as text, letting the fetcher pick its own tier:

```bash
py -m pagefetch https://en.wikipedia.org/wiki/Web_scraping
```

Stdout carries the stripped page text. A successful tier 1 fetch says
nothing on stderr — the tiers only narrate when they escalate:

```text
[http] Not real content (559 bytes) — escalating
[auto] Skipping js (bot protection), trying headed...
```

Force one transport instead of letting the fetcher escalate:

```bash
py -m pagefetch <url> --http       # plain request only, never escalate
py -m pagefetch <url> --js         # browser that renders JavaScript
py -m pagefetch <url> --headed     # bot bypass, needs a display
py -m pagefetch <url> --headless   # bot bypass, no display needed
```

Change the output, the wait, or the cache:

```bash
py -m pagefetch <url> --html       # raw HTML instead of stripped text
py -m pagefetch <url> --wait 5000  # extra post-load wait (ms)
py -m pagefetch <url> --no-cache   # refetch, ignoring any cached copy
py -m pagefetch <url> --cache-dir DIR
```

Fetch many pages in one browser session:

```bash
py -m pagefetch --batch urls.txt                    # one URL per line
py -m pagefetch --batch -                           # from stdin
py -m pagefetch url1 url2 url3                      # from arguments
py -m pagefetch --batch urls.txt --output-dir out/  # one file per URL
```

Purge junk that accumulated in the cache before the current guards existed:

```bash
py -m pagefetch --clean-cache
py -m pagefetch --clean-cache --dry-run   # list junk, delete nothing
```

`--dry-run` prints the entries it would remove and exits without deleting.

### Exit codes

| Code | Meaning                                            |
| ---- | -------------------------------------------------- |
| 0    | Every requested URL returned content               |
| 1    | Nothing came back, or the arguments were rejected  |
| 2    | A batch returned content for some URLs but not all |

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

Map values are page bodies — the HTML a real fetch would have returned.
`FakeFetcher` derives TEXT mode from them the same way `NetworkFetcher`
does, by stripping tags, so code that reads both modes sees them differ
under test as it will in production.

| Symbol           | Purpose                                         |
| ---------------- | ----------------------------------------------- |
| `PageSource`     | Abstract base — the transport interface         |
| `NetworkFetcher` | Real fetcher with four-tier escalation          |
| `FakeFetcher`    | Test double backed by a URL→content map         |
| `FileCache`      | On-disk response cache (configurable directory) |
| `FetchOptions`   | `mode`, `transport`, `wait_ms`, `use_cache`     |
| `FetchResult`    | `url`, `content`, `tier_used`, `ok`             |
| `ContentMode`    | `TEXT` (stripped) / `HTML` (raw)                |
| `Transport`      | `AUTO` / `HTTP` / `JS` / `HEADED` / `HEADLESS`  |
| `is_bot_blocked` | Pure bot-detection predicate                    |

Point the cache somewhere specific:

```python
from pathlib import Path
from pagefetch import NetworkFetcher, FileCache

fetcher = NetworkFetcher(cache=FileCache(cache_dir=Path("/my/cache")))
```

## Project structure

| Path                       | Purpose                                            |
| -------------------------- | -------------------------------------------------- |
| `pagefetch/`               | The package — import this                          |
| `pagefetch/source.py`      | `PageSource` ABC and the option / result types     |
| `pagefetch/network.py`     | `NetworkFetcher` — the four-tier escalation ladder |
| `pagefetch/detection.py`   | Bot-wall, error-page, and real-content predicates  |
| `pagefetch/cache.py`       | `FileCache` — on-disk cache and junk sweep         |
| `pagefetch/chrome.py`      | Chrome / CDP launch helpers for the browser tiers  |
| `pagefetch/fake.py`        | `FakeFetcher` test double                          |
| `pagefetch/__main__.py`    | CLI entry point — a thin wrapper over the library  |
| `pagefetch/tests/`         | pytest suite, including captured HTML fixtures     |
| `docs/ARCHITECTURE.md`     | How the ladder, detection, and cache work          |
| `docs/decisions/`          | Architecture Decision Records                      |
| `docs/audits/`             | 360-degree audit reports, one per run              |
| `docs/solid-ai-templates/` | Quality conventions — a git submodule              |
| `docs/ONBOARDING.md`       | Fresh clone to a passing gate                      |
| `docs/PLAYBOOK.md`         | Operational reference for recurring tasks          |
| `docs/dev-journal.md`      | Session log — what changed and why                 |
| `.github/workflows/`       | CI and CodeQL pipelines                            |
| `CLAUDE.md`                | Project rules for AI agents                        |
| `pyproject.toml`           | Package metadata and every tool's configuration    |

## Development setup

Clone the repository, install the dependencies and run the test suite:

```bash
git clone https://github.com/braboj/page-fetcher.git
cd page-fetcher
py -m pip install -e ".[dev]"
pre-commit install
py -m pytest
```

To exercise the browser tiers locally, add the optional engines:

```bash
py -m pip install -e ".[browsers]"
playwright install chromium
```

The gate is four checks, each runnable on its own:

```bash
py -m ruff check .          # lint
py -m ruff format --check . # formatting, including Python in this README
py -m mypy                  # type check
py -m pytest --cov=pagefetch
```

`pre-commit install` runs the first three on every commit, plus a secret
scan. CI runs all four on every pull request, because a hook can be skipped
with `--no-verify`.

## Configuration reference

`cache_dir` is the only configurable value. It resolves in this precedence,
highest first:

| Source                       | Type | Default              | Notes                       |
| ---------------------------- | ---- | -------------------- | --------------------------- |
| `--cache-dir DIR`            | path | unset                | CLI flag, one invocation    |
| `cache_dir=` constructor arg | path | unset                | Programmatic use            |
| `PAGEFETCH_CACHE_DIR`        | path | unset                | Environment variable        |
| built-in default             | path | `./.cache/pagefetch` | Relative to the working dir |

## Known limitations

- **headed** opens a Chrome window, so it cannot run in CI or on a host with
  no display.
- **headless** costs ~18-24s, most of it Chrome launch overhead.
- PerimeterX "Press & Hold" blocks every tier.
- Each URL launches its own browser unless you use batch mode.
- The scheme check is an allowlist, not SSRF protection. See
  [Architecture](docs/ARCHITECTURE.md#url-schemes-and-what-this-is-not).

## Links

- [Architecture](docs/ARCHITECTURE.md) — the escalation ladder, detection
  rules, cache behaviour, and performance history
- [Onboarding](docs/ONBOARDING.md) — fresh clone to a passing gate
- [Playbook](docs/PLAYBOOK.md) — git workflow, adding a tier or a detection
  pattern, the quality checks, maintenance
- [Dev journal](docs/dev-journal.md) — what changed each session and why
- [Audits](docs/audits/) — 360-degree assessments, one report per run

## Dependencies

| Dependency        | Tier       | Required | License    |
| ----------------- | ---------- | -------- | ---------- |
| `urllib` (stdlib) | `http`     | always   | PSF        |
| `playwright`      | `js`       | optional | Apache-2.0 |
| `nodriver`        | `headed`   | optional | AGPL-3.0   |
| `seleniumbase`    | `headless` | optional | MIT        |

The three browser engines live in the `browsers` extra
(`pip install ".[browsers]"`). A missing one skips its tier with a message
on stderr rather than failing.

## License

MIT — see [LICENSE](LICENSE).

The optional `nodriver` dependency is AGPL-3.0 and is not covered by this
license. It affects you only if you install it and then distribute a
network service built on the **headed** tier; see
[Architecture](docs/ARCHITECTURE.md#nodriver-and-the-agpl).
