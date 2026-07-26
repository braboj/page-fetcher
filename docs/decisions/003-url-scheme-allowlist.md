# ADR-003: Allowlist URL schemes; leave private-range blocking to the caller

**Status:** Accepted
**Date:** 2026-07-26

## Context

`urllib.request.urlopen` handles more than HTTP. Handed `file:///etc/passwd`
it reads the file; `ftp://` and a few other schemes work too. The package
passed caller-supplied URLs straight through, so a consumer that fetches a URL
originating anywhere outside its own code had a file-read primitive it did not
ask for. Ruff flagged it as S310 in four places, suppressed at file level while
the decision was pending.

Scheme handling is the narrow question. The broader one is how far a *page
fetcher* should go in protecting consumers who pass untrusted URLs. The usual
next step is resolving the host and rejecting loopback and private ranges
(`127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`,
`169.254.0.0/16`, `::1`, `fc00::/7`), re-validating after every redirect to
defeat DNS rebinding.

## Decision

**1. Reject any scheme that is not http or https, at every public entry point.**

`require_supported_scheme` runs in `fetch`, `fetch_batch`, `download_bytes`,
and `screenshot` — before a request is made or a browser is launched. It raises
`ValueError` with a message naming the offending scheme and the allowed set. A
URL with no scheme at all gets a different message suggesting the `https://`
form, because naming an empty scheme helps nobody.

```text
caller -> fetch / fetch_batch / download_bytes / screenshot
             |
             +-- require_supported_scheme   <- raises here, nothing launched
             |
             v
          tier ladder -> urllib / playwright / nodriver / uc
```

`fetch_batch` validates the entire list before starting rather than as it goes.
A batch launches a browser and can run for minutes; failing on URL 87 of 100
after all that work is worse than refusing immediately.

**2. Private-range and loopback blocking is out of scope.**

Not deferred — decided against, for this layer. Three reasons.

It would break legitimate use. Fetching an intranet page, a staging host on
`10.x`, or `localhost:8000` during development are all ordinary things to do
with a page fetcher. Blocking them by default breaks real users to protect a
case that may not apply to them.

It cannot be done properly here. Sound SSRF defence resolves the hostname,
checks the resolved address, re-checks after every redirect, and handles
IPv6-mapped and encoded forms. Doing it partially is worse than not doing it:
a consumer who sees "SSRF protection" in the README stops writing their own
filter, and a partial implementation is a false guarantee.

The caller has the context. Only the consumer knows whether a URL came from a
config file it controls or from a form field. `pagefetch` cannot distinguish
those, so the filter belongs where the trust boundary actually is.

The README and the `require_supported_scheme` docstring both say plainly that
this is a scheme allowlist and nothing more, so nobody infers protection that
is not there.

**3. `FakeFetcher` deliberately does not validate.**

The test double accepts any key as a URL. Its keys are map lookups that never
reach a socket, so the scheme carries no meaning, and tests are free to use
short labels — the downstream consumer that prompted the split uses keys like
`"u1"` in 26 places.

This is a knowing divergence between the double and the real implementation,
which is normally a defect: a consumer can pass an unsupported scheme, watch it
pass against the fake, and see it raise in production. It is accepted because
the alternative is breaking every existing consumer test to enforce a property
the fake cannot violate anyway. The divergence is documented in `fake.py` so it
is discoverable rather than surprising.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Private-range blocking on by default | Breaks intranet, staging, and localhost fetching — ordinary uses of a page fetcher — to protect a case that may not apply. |
| Private-range blocking behind an opt-in flag | Still needs DNS resolution, redirect re-validation, and IPv6 handling to be sound. A flag that half-works is a false guarantee, and nobody is asking for it yet. |
| Return a failed `FetchResult` instead of raising | An unsupported scheme is a caller mistake, not a fetch failure. Folding it into the normal result type means it can be ignored silently, and the fetcher would report "not ok" for something it never attempted. |
| Validate only in `_fetch_urllib` | Matches the letter of the ruff warning and misses the point: `screenshot` and the browser tiers take a URL too. |
| Keep the file-level S310 suppression | A file-wide ignore hides future genuine cases. Two `# noqa: S310` comments at the actual call sites, each naming the guarantee, say what a blanket ignore cannot. |
| Enforce the allowlist in `FakeFetcher` too | Contract fidelity, but it breaks existing consumer tests to enforce a property a map lookup cannot violate. Documented instead. |

## Consequences

| Consequence | Effect |
| --- | --- |
| `file://`, `ftp://`, `data:` and friends now raise | A breaking change for anyone relying on them. Nothing in the package or its known consumer did. |
| Failure is immediate and cheap | No browser launch, no cache read, no request — the error names the scheme and what is allowed. |
| The file-level S310 suppression is gone | Replaced by two line-level `# noqa: S310` comments that each cite the boundary check. A new unguarded `urlopen` will be flagged. |
| `require_supported_scheme` and `ALLOWED_SCHEMES` are public | So a consumer can apply the same check at its own boundary rather than reimplementing it. |
| Consumers passing untrusted URLs still need their own filter | Stated in the README and the docstring. This ADR is the record that it is deliberate. |
| The fake and the real fetcher disagree on scheme handling | Documented in `fake.py`. Revisit if a consumer is ever bitten by it. |
