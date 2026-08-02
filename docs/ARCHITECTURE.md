# Architecture

How pagefetch decides which transport to use, what it treats as a failed
response, and how it caches.

> Interim document. It holds the technical detail moved out of the README
> and will be restructured as arc42 when those documents are written.

## Escalation ladder

```text
http (plain request, ~1s)
  +- success -> done
  +- HTTP error (404, timeout) -> js
  +- bot protection (captcha, 403) -> skip js -> headed
                                            |
js (~5-9s)                                  |
  +- success -> done                        |
  +- bot detection / error -> headed <------+
                |
headed (~6-8s)
  +- success -> done
  +- failure -> headless
                |
headless (~18-24s)
  +- success -> done
  +- failure -> all tiers failed (content="")
```

| Tier       | Engine          | Speed   | Display  | Use case                    |
| ---------- | --------------- | ------- | -------- | --------------------------- |
| `http`     | urllib          | ~1s     | —        | Static HTML (most sites)    |
| `js`       | Playwright      | ~5-9s   | not used | JS-rendered content         |
| `headed`   | Nodriver        | ~6-8s   | required | Bot bypass, preferred       |
| `headless` | SeleniumBase UC | ~18-24s | not used | Bot bypass, no display      |

When `http` detects bot protection, `js` is skipped — it would fail the same
way — and the fetcher goes straight to `headed`, then `headless`.

**On the order.** `headed → headless` reads like a step backwards, since
headless sounds cheaper. It is not: the `headless` tier pays for stealth
patching plus a cold Chrome launch, which costs more than attaching to
Chrome over CDP. The ladder is ordered by cost, and the tiers are named for
what they require of the caller — a display or not — because that is the
part a caller cannot change. [ADR-006](decisions/006-two-bot-bypass-tiers.md)
records why both bypass tiers exist.

The engine column is the only place a library name appears in the tier
model. Swapping any engine leaves the tier names, the CLI flags, and
`tier_used` unchanged.

## Detection

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

## Response decoding

Tier 1 advertises `gzip, deflate` and undoes whichever comes back, falling
back to a raw deflate stream when the zlib header is missing — some servers
send one.

It also sniffs the gzip magic bytes when the header does not claim gzip,
because a server that compresses without declaring it is not hypothetical
and is the worst case here. Decoded as text, an undeclared gzip body becomes
mojibake, which is comfortably larger than `MIN_REAL_CONTENT_BYTES` — so it
passes the real-content gate and is written to the cache as though it were a
page. A declared encoding this tier cannot undo, including any chain of
them, is rejected for the same reason rather than handed back unchanged.
Escalating to a browser beats caching garbage.

## Event-driven waits

Browser tiers poll rather than sleeping a fixed time. They wait for
`document.readyState === "complete"`, poll the page source with exponential
backoff (0.5s to a 2s cap, 15s timeout) until bot-detection patterns
disappear, then scroll and poll `scrollHeight` until it stabilizes. This
adapts to the actual security handshake time instead of guessing it.

## Cache

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

## Why configuration stays minimal

Configuration is one environment variable and one CLI flag, validated with
the standard library. A typed settings object (Pydantic) and `.env` loading
are not used — they would add dependencies that break the
standard-library-only contract for tier 1, and they are overkill for a
single knob. Revisit if the package grows several config values (user agent,
timeouts, tier toggles, concurrency), at which point a typed settings object
would be introduced across all of them.

The resolved cache directory is validated at construction, not at first
write. A path that is an existing file, or whose nearest existing ancestor
is missing or read-only, raises a `ValueError` naming the source that
supplied it. The directory itself is created lazily on first write.

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

That is a deliberate boundary rather than an omission;
[ADR-003](decisions/003-url-scheme-allowlist.md) records why blocking
private ranges here would break ordinary intranet and localhost fetching
while offering a guarantee this layer cannot honestly make.

## nodriver and the AGPL

`pagefetch` is MIT licensed and stays MIT. It does not vendor, bundle, or
redistribute `nodriver`; the tier 3 import is lazy and is skipped when the
package is absent, so installing `pagefetch` alone pulls in no AGPL code.
The AGPL becomes your concern if you install `nodriver` and then distribute
a network service built on the combination — the scenario section 13 of the
AGPL covers, which obliges you to offer your service's source to its users.
If that applies to you, install only `playwright` and `seleniumbase` and
leave tier 3 out; the ladder degrades to three tiers and skips Nodriver with
a stderr message.

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

## Sites tested

| Site               | Tier       | Notes                                   |
| ------------------ | ---------- | --------------------------------------- |
| allphotolenses.com | `http`     | static HTML                             |
| ttartisan.com      | `js`       | JS-rendered (query-param routing)       |
| zyoptics.net       | `headed`   | SiteGround captcha + bot protection     |
| bhphotovideo.com   | `headed`   | bypasses Cloudflare with a real window  |
| viltrox.com        | `http`     | static HTML + Shopify JSON              |
| mobile01.com       | `headless` | Akamai blocks plain headless browsers   |
| adorama.com        | BLOCKED    | PerimeterX "Press & Hold" — manual only |

The column records which tier _succeeded_, not which tiers were tried and
failed, so it is weak evidence for the two bypass tiers covering different
sites. See ADR-006.
