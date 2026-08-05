# Risks and Technical Debt

## Risks

| ID | Risk | Probability | Impact | Mitigation |
| ---- | ------ | ------------- | -------- | ------------ |
| R-1 | A wrong "not a page" verdict is silent and final: the caller gets no content and a non-zero status for a page that exists, indistinguishable from a page that does not. Nothing detects it afterwards, and no cheaper correction exists than fetching the URL by hand | Low | High | Ambiguous phrasing counts only below the size floor; every pattern carries a negative case on real content; a report of a lost page is triaged as a correctness defect rather than a usability one |
| R-2 | Classification is pattern-based against sites that change their protection without notice. A wall in a shape no pattern matches is returned as content, stored, and served from the store from then on | Medium | Medium | The size floor catches short stubs whatever they say; new shapes arrive as defects and are added with a positive and a negative case |
| R-3 | Completeness is never assessed. A page over the floor whose content renders in JavaScript comes back partial and is stored under the key a complete body would have used | Certain | Medium | Stated as a limitation in the README and in the crosscutting concepts; a caller who needs completeness names the JavaScript transport. Reopening it needs a corpus of pages captured by someone other than whoever proposes the rule, which the no-network suite cannot produce from inside itself |
| R-4 | The user agent is a pinned browser version string. It ages, and a version far enough behind real browsers becomes a signal in itself; it is a constructor argument with no environment variable or flag behind it, so a consumer cannot change it from the command line | Medium | Medium | Bump it alongside the engines; promote it to configuration if a second value ever needs one |
| R-5 | Challenges requiring a human gesture block every transport. No rung clears one, and none can | Certain | Low | Recorded as a standing limitation. Whether challenge frequency tracks request velocity is an open question and the cheapest one to answer |
| R-6 | Orphaned-browser cleanup does not run outside Windows: on other platforms a browser that outlives its fetch keeps running | Medium | Low | Accepted. Each fetch releases its own browser first, and leaving one behind is the safe direction to fail in |
| R-7 | The engine behind the headed transport is AGPL-3.0. A consumer who installs it and then distributes a network service built on that transport takes on section 13 | Low | Medium | The engine is optional, un-vendored and imported inside the transport, so it reaches nobody who does not install it; the obligation is stated in the constraints and in the README |
| R-8 | There is no rate limiting, backoff or robots.txt handling. A consumer looping over a long list is indistinguishable from a scraper, and the package offers nothing to moderate that | Medium | Medium | Scope is stated as a limitation; batch mode is sequential and single-session by construction, so the package cannot be made fast by configuration alone |

## Technical Debt

| ID | Debt | Impact | Effort |
| ---- | ------ | -------- | -------- |
| TD-1 | An automatic batch fetches its first URL twice. The probe deciding whether to hold a browser calls the plain transport directly, neither reading nor writing the store, and the loop then fetches the same URL again. A batch whose URLs are all stored still costs one request | Low | Low |
| TD-2 | Naming several transports at once resolves to the most escalated one rather than being rejected. Pinned by test as the current behaviour, but never decided — whether it should be an error is open | Low | Trivial |
| TD-3 | The JavaScript transport writes a screenshot into the store directory as a side effect of an ordinary text fetch, whether or not a screenshot was asked for | Low | Trivial |
| TD-4 | The abstract page source declares byte download and screenshot capture; the command line exposes neither, so both are library-only surface | Low | Low |
| TD-5 | The store key scheme carries no version marker. A change to the digest, its length or the suffixes orphans every existing entry silently rather than failing, which is why the scheme is treated as frozen | Low | Medium |
| TD-6 | The coverage floor deliberately sits a few points below the measured figure, as headroom for the platforms covering different branches. The ratchet therefore always lags what the suite reaches | Low | Trivial |
| TD-7 | Browser transport bodies are the bulk of what is uncovered and are validated by hand, so a regression inside one is found by a person running it rather than by the gate | Medium | High |

## Evidence Base

Two records of measurement sit here rather than among the decisions,
because what they mostly establish is how much is not known.

### How the Ladder Reached Its Current Shape

- **v1** — one browser engine, waiting for network idle. Around 5-9s
  everywhere, and failure on anything bot-protected.
- **v2** — three transports. Static pages around 1s; protected pages
  around 27s.
- **v3** — skip the JavaScript rung on a wall, wait for the document
  rather than the network, and poll instead of sleeping. Protected pages
  fell to 18-24s.
- **v4** — one browser per batch instead of one per URL. Three protected
  pages went from about 60s to about 27s.
- **v5** — a debug-protocol engine added and preferred over the stealth
  one. The same three pages went from 27s to 16s.
- **v6** — refactored from a single script into this package. Behaviour
  preserved.
- **v7** — throttle pages stopped reaching the store: broader wall
  patterns and the size floor, so short stubs escalate rather than being
  kept.
- **v8** — not-found handling and validity by content. A not-found body is
  final, and a stored one heals itself on read. No expiry.
- **v9** — stored junk is deleted rather than merely ignored when it is
  scrubbed, and a sweep does the same in bulk.

### Sites Exercised by Hand

| Site | Transport | Notes |
| ------ | ----------- | ------- |
| allphotolenses.com | `http` | Static markup |
| ttartisan.com | `js` | Rendered in the browser, query-parameter routing |
| zyoptics.net | `headed` | Captcha and bot protection |
| bhphotovideo.com | `headed` | Clears a challenge with a real window |
| viltrox.com | `http` | Static markup plus a JSON endpoint |
| mobile01.com | `headless` | Blocks plain headless browsers |
| adorama.com | none | Press-and-hold challenge; manual only |

The column records which transport *succeeded*, not which ones were tried
and failed. That makes the table weak evidence for the claim it looks like
it supports — that the two bypass transports cover different sites — and it
is the reason the split between them rests on their costs rather than on
this table.
