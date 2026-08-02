# ADR-006: Keep two bot-bypass tiers, ordered by cost and split by display

**Status:** Accepted
**Date:** 2026-08-02

## Context

Tiers 3 and 4 both exist to get past bot protection. Tier 3 drives Chrome
over CDP through `nodriver`, with no chromedriver in the picture. Tier 4
runs SeleniumBase in UC mode, which patches chromedriver to remove the
markers that identify it as automation. Two tiers, one apparent purpose.

Nothing records why. The ladder arrived whole from `tools/fetch-page.py`
in the upstream wuseria repository, and the ADR that extracted it into a
package — [wuseria ADR-035](https://github.com/Imbra-Ltd/wuseria/blob/main/docs/decisions/035-pagefetch-package-and-brandkit.md)
— preserved the four tiers "byte-for-byte" without arguing for them. No ADR
in this repository covers it either. The only written trace is the README's
performance history: UC was tier 3 from v2, nodriver was added in v5 and
took precedence, cutting a three-page bot-protected batch from 27s to 16s.

The question became live because the transport modes are being renamed off
their libraries. `Transport.NODRIVER` and `Transport.UC` name implementations
and say nothing about when to pick one; whatever replaces them has to encode
the actual distinction, which first has to be written down.

## Decision

**1. Keep both tiers.**

They are not redundant. Tier 3 is roughly three times faster and is tried
first. Tier 4 is the only bypass tier that runs without a display, so it is
the only one available in CI, on a headless server, or in any container
without an X server. Dropping tier 4 would make bot-protected pages
unreachable in exactly the environments where automation usually runs;
dropping tier 3 would triple the cost of the common case.

**2. Order them by cost, not by capability.**

AUTO tries tier 3 before tier 4 because it is faster, not because it is
stronger. A caller that reaches tier 4 has already spent the cost of tier 3.

**3. Name them by their operating requirement, not their evasion technique.**

`Transport.HEADED` and `Transport.HEADLESS` replace `NODRIVER` and `UC`.
The display requirement is the property a caller has to decide about — it is
a hard constraint of their environment. Which fingerprints each library
hides is an implementation detail that changes without notice.

This makes the ladder read `HTTP → JS → HEADED → HEADLESS`, which looks
non-monotonic: headless sounds cheaper than headed. It is not. Tier 4's
stealth patching plus a cold Chrome launch costs more than tier 3's CDP
attach, and the name records what the caller must satisfy rather than what
it costs. The ordering is documented in `docs/ARCHITECTURE.md` instead of
being encoded in the names.

**4. Treat differing coverage as a benefit, not a guarantee.**

The two tiers hide from detection by unrelated mechanisms, so a site that
fingerprints one may miss the other. The sites-tested table is consistent
with this — mobile01.com is served by tier 4 while zyoptics.net and
bhphotovideo.com are served by tier 3. That table records which tier
*succeeded*, not which tiers were tried and failed, so it is suggestive
rather than conclusive. The claim is not load-bearing: tiers 3 and 4 would
both stay on the display argument alone.

## Alternatives considered

**Drop tier 4 and run nodriver headless.** `nodriver` supports headless, and
one bypass tier would be simpler. Rejected: a visible window is a large part
of why tier 3 defeats Cloudflare, so a headless nodriver is not a substitute
for a stealth-patched chromedriver. This would trade a working fallback for
one that fails in the same conditions as the tier above it.

**Drop tier 3 and keep only UC.** Simpler and headless everywhere. Rejected
on cost: it reverts the v5 improvement and triples the time for every
bot-protected page, on the machine where these fetches actually run.

**Select by environment rather than escalate.** Detect whether a display is
available and pick tier 3 or tier 4 directly. Rejected as premature — it
adds a platform probe to a package that deliberately has none, and the
escalation already produces the right outcome, just after one failed
attempt. Worth revisiting if the wasted tier-3 attempt on headless hosts
becomes a real cost.

**Name the tiers `STEALTH_FAST` / `STEALTH_SLOW`.** Encodes the ordering in
the names. Rejected: relative speed is a measurement that drifts with
library versions and hardware, while the display requirement is a fact about
the caller's environment.

## Consequences

- The API stops naming libraries. `playwright`, `nodriver`, and
  `seleniumbase` remain in `pyproject.toml`, the Dependencies table, and the
  architecture tier table, because they are what you install — but no caller
  writes them.
- Swapping a library behind a tier is no longer a breaking change to
  consumers, as long as the display requirement holds.
- The ladder order has to be documented, since the names no longer imply it.
- A caller on a headless host still pays one failed tier-3 attempt before
  reaching tier 4. Accepted for now; forcing `--headless` avoids it.

## Related

- [ADR-001](001-extract-pagefetch-into-standalone-repo.md) — extraction of
  this package into a standalone repository
- [ADR-005](005-chrome-ownership-by-ancestry.md) — cleanup of the Chrome
  processes tiers 3 and 4 leave behind
- [wuseria ADR-035](https://github.com/Imbra-Ltd/wuseria/blob/main/docs/decisions/035-pagefetch-package-and-brandkit.md)
  — the extraction that carried the four-tier ladder over unexamined
