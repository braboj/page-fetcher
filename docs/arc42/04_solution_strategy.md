# Solution Strategy

## Technology Decisions

| Decision | Rationale |
| ---------- | ----------- |
| urllib (plain transport) | The common case is a static page, and the standard library serves it in about a second. Using it keeps the default install free of any third-party package, which is what makes the package safe to vendor into a consumer that wants no dependencies |
| Playwright (JavaScript transport) | Renders a page whose content is assembled in the browser, headlessly and with no driver binary to install or match against a browser version |
| Nodriver (headed bot-bypass transport) | Drives an ordinary Chrome over its debug protocol, so what a site inspects is a real browser rather than a patched one. It costs a visible window, which is why it is not the only bypass |
| SeleniumBase UC (headless bot-bypass transport) | Clears the same walls with no display available, at the cost of a stealth-patching pass plus a cold browser launch — several times the price of attaching to a browser already starting |
| Classification from the response body | A bot wall, a throttle stub and a discontinued-product page are routinely served with a success status. The status code cannot distinguish any of them from a page, so the body is the only evidence there is |
| Store validity decided by content, not age | Reference pages change rarely, and the change that matters — the page going away — arrives as a not-found body that the classifier already recognizes. An expiry time would re-fetch unchanged pages on a schedule and still miss that |
| An abstract page source with a canned implementation | A consumer's tests exercise their own code, not this package's network handling. Substituting a source backed by a map of URLs to bodies removes the network from their suite entirely |
| Process attribution by ancestry | Deciding which browser processes belong to this one by walking parents is the only method that distinguishes them from a browser window the user opened while a fetch was running |

## Architecture Approach

- **Escalate on evidence, do not predict.** Which transport a URL needs is
  decided by what the previous transport returned, never by a per-site
  table or a guess made before the request. Nothing has to be known about
  a site in advance, and a site that changes its protection is followed
  without a code change.
- **Ordered by cost, named by requirement.** Transports run cheapest
  first. They are named for what they ask of the caller — a display, or
  nothing — rather than for the engine behind them, so replacing an engine
  changes no name a caller has written down. The headed transport running
  before the headless one reads backwards until the costs are compared:
  attaching to a real browser is cheaper than patching one for stealth and
  launching it cold.
- **Skip a rung that would fail identically.** A bot wall on the plain
  transport skips the JavaScript one, which presents the same client
  signature and meets the same wall. The ladder is an ordering, not an
  obligation to try everything.
- **End where escalation cannot help.** A not-found or gone body ends the
  fetch immediately. Every remaining transport would retrieve the same
  page, and retrying would spend a browser launch to confirm it.
- **Degrade rather than fail.** A transport whose library is not installed
  removes itself from the ladder and says so. The package is useful with
  no engines at all, which is also the shape of the default install.
- **One browser for a batch, not one per URL.** A batch decides once
  whether it needs a browser, keeps it for the whole run, and releases it
  in a path that runs whatever else happens.
- **Pure classification, isolated side effects.** The rules deciding what
  a body is are pure functions of that body, with no I/O and no
  configuration. Everything that touches the host — process enumeration,
  signalling — is confined to one module that does nothing else.

## Quality Approach

| Quality Goal | Approach |
| -------------- | ---------- |
| Correctness | Phrasing that means "this page is gone" on a stub and "one variant is out of stock" in ordinary body copy counts only below the size floor, where there is too little else on the page for it to be incidental. The floor is deliberately generous. Completeness is not assessed at all: a body over the floor that trips no pattern is returned as it stands, even when part of the page renders in JavaScript |
| Functional Correctness | One definition of what is not a page, applied at four points: before returning, before storing, on reading a stored body, and during a sweep. Bodies below a size floor are rejected whatever they contain, which catches stubs that carry no recognizable wording |
| Portability | The declared dependency list is empty and every engine import happens inside the transport that uses it. Both supported Python versions and both platforms are built, because the process-cleanup module takes a different path on each |
| Reliability | Every transport catches broadly and returns nothing rather than raising, so a failure inside an engine costs one rung. A batch releases its browser, its event loop and its session in a path that runs on every exit, and each release step is independent so a browser that has already died does not skip the steps after it |
| Security | The scheme check runs at every public entry point, before a request is made or a browser is started, so no code path reaches a transport without it. Cleanup requires both that a process is new since the launch and that it descends from this one; where ancestry cannot be established, nothing is tracked and nothing is killed |
| Performance Efficiency | The plain transport answers the common case in one request. A browser is launched only after a response says one is needed, and a batch launches at most one. A stored body is served without any request |
| Maintainability | Patterns live in one module of pure predicates, transports in one module with the escalation order beside them, and the junk definition in a single function that the read path and the sweep both call. Configuration is one environment variable and one flag, validated with the standard library, because a typed settings object would be a dependency for one value |

## How the Ladder Was Tuned

The ordering above was arrived at by measurement, one version at a time,
rather than designed in advance. The figures below are what was measured
when each change landed. They are a record of the direction each change
moved things, not a current benchmark — the engines and the sites have both
moved since.

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
