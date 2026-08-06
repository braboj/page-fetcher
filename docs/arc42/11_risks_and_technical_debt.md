# Risks and Technical Debt

## Risks

A risk is a way the system can fail that has not happened yet. A weakness
that is already present is debt; one that is permanent and accepted is a
scope limitation, recorded in System Scope and Context rather than here.
Numbers are not reused — a resolved entry is removed and its number retires
with it.

| ID | Risk | Probability | Impact | Mitigation |
| ---- | ------ | ------------- | -------- | ------------ |
| R01 | A wrong "not a page" verdict is silent and terminal | Low | High | Ambiguous wording counts only below the size floor |
| R02 | A wall in a shape no pattern matches is returned as content and stored | Medium | Medium | The size floor catches short stubs whatever they say |
| R03 | The pinned user agent ages into a bot signal of its own | Medium | Medium | Bumped alongside the engines |
| R04 | Orphaned-browser cleanup does not run outside Windows | Medium | Low | Accepted; each fetch releases its own browser first |
| R05 | Distributing a service built on the headed transport takes on AGPL section 13 | Low | Medium | The engine is optional, un-vendored, and imported inside the transport |
| R06 | A consumer looping over a long list is indistinguishable from a scraper | Medium | Medium | Batch mode is sequential and single-session by construction |

### R01

The caller gets no content and a non-zero status for a page that exists,
indistinguishable from the same answer for a page that does not. Nothing
detects the mistake afterwards, and no correction is cheaper than fetching
the URL by hand.

Beyond the size floor, every pattern carries a negative case proving it does
not fire on real content, and a report of a lost page is triaged as a
correctness defect rather than a usability one.

### R02

Classification is pattern-based against sites that change their protection
without notice. A body that is a wall but matches nothing is returned to the
caller, stored, and served from the store from then on.

New shapes arrive as defect reports and are added with a positive and a
negative case. The floor is what holds while a shape is still unknown.

### R03

The user agent is a constructor argument with no environment variable or
flag behind it, so a consumer cannot change it from the command line. A
version string far enough behind real browsers is a signal in itself.

Promoting it to configuration is deferred until a second value needs one.

### R05

The engine reaches nobody who does not install it, and the obligation is
stated in Architecture Constraints and in the README. What section 13 covers
is distribution of a network service built on that transport, not use of it.

### R06

The package offers no rate limiting, backoff or robots.txt handling, and
none is planned — that scope limit is stated in System Scope and Context.
The risk is what a consumer does with the package regardless: a long loop
looks like collection to the site serving it.

Nothing in the package makes that faster. Batch mode holds one browser for
one sequential pass, so the ceiling is set by construction rather than by
configuration.

## Technical Debt

| ID | Debt | Impact | Effort |
| ---- | ------ | -------- | -------- |
| TD01 | An automatic batch fetches its first URL twice | Low | Low |
| TD02 | Naming several transports at once resolves to the most escalated rather than being rejected | Low | Trivial |
| TD03 | The JavaScript transport writes a screenshot as a side effect of an ordinary text fetch | Low | Trivial |
| TD04 | Byte download and screenshot capture are declared on the interface but reach no command line | Low | Low |
| TD05 | The store key scheme carries no version marker | Low | Medium |
| TD06 | The coverage ratchet always lags what the suite reaches | Low | Trivial |
| TD07 | Browser transport bodies are validated by hand, not by the gate | Medium | High |

### TD01

The probe deciding whether to hold a browser calls the plain transport
directly, neither reading nor writing the store, and the loop then fetches
the same URL again. A batch whose URLs are all stored still costs one
request.

### TD02

Pinned by test as the current behaviour, but never decided. Whether naming
several transports should instead be an error is open.

### TD05

A change to the digest, its length or the suffixes orphans every existing
entry silently rather than failing. That is why the scheme is treated as
frozen.

### TD06

The floor deliberately sits a few points below the measured figure, as
headroom for the platforms covering different branches of the process
cleanup. The lag is the cost of enforcing one number on every matrix leg.

### TD07

They are the bulk of what is uncovered, so a regression inside one is found
by a person running it rather than by the gate. Raising this needs a headed
browser in the environment that runs the suite, which is the reason it has
not been.

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
