# ADR-017: Decline under-render detection at tier 1

**Status:** Accepted
**Date:** 2026-08-05

## Context

Escalation asks whether a response *failed*. It never asks whether the
response is *complete*. A tier 1 body escalates when it is a bot wall, an
error page, or shorter than `MIN_REAL_CONTENT_BYTES` (10 KB). A page whose
raw HTML clears that floor and trips no pattern is returned as it stands.

That is right for static HTML and wrong for a page that renders a
meaningful part of itself in JavaScript. The response is plausible, large
enough, and partial. Nothing escalates, nothing reaches stderr, and the
truncated body is cached under the key a complete one would have used.
`--js` forces the render, but a caller has to already suspect the problem
to reach for it.

[#124](https://github.com/braboj/page-fetcher/issues/124) asked whether
under-rendering is detectable at tier 1 without paying for the browser the
detection is trying to avoid, and named four candidate signals: a
body-to-markup ratio, an SPA mount point with no children, framework
bootstrap markers, and a `<noscript>` block that names the requirement.

## Evidence

Each signal was measured against six pages — the one captured fixture in
the corpus plus five constructed cases, all of them above the 10 KB floor,
because a page under the floor already escalates and tests nothing:

```text
case                                bytes    ratio   root   nosc
------------------------------------------------------------------------
dpreview specs (captured)         135,253   0.1016  False  False  complete
CRA shell, padded past floor       10,218   0.0050   True   True  PARTIAL
article + empty widget mount       19,447   0.9428   True  False  complete
article about blank React pages    20,880   0.9485  False   True  complete
SSR page, large __NEXT_DATA__     242,544   0.0077  False  False  complete
image gallery, srcset + lazy       34,387   0.0147  False  False  complete
```

Every signal produces a false positive on a complete page:

**Text-to-markup ratio.** The under-rendered shell scores 0.0050 and the
lowest-scoring complete page scores 0.0077 — separable on this corpus by a
factor of 1.5, which is not separation, it is an artifact. The ordering is
set by how much inline JSON a complete page carries, and that is unbounded:
enlarging the `__NEXT_DATA__` blob moves a fully rendered page below the
shell at will. The ratio measures how much of a byte stream is prose, and a
complete page may legitimately have almost none — the gallery at 0.0147 is
missing nothing.

**Empty mount point.** Fires on a 19 KB article that is complete and leaves
an empty `<div id="app">` behind for a comments widget. The whole article is
present; a mount point elsewhere on the page is not evidence about it.

**Bootstrap markers.** Fire on the complete SSR page and not on the shell —
backwards. The marker says the page uses a framework, and the server-rendered
case is the one that carries it. It cannot distinguish the two classes
because it is not about rendering at all.

**`<noscript>` requirement.** Fires on a 21 KB article *about* debugging
blank React pages, which quotes the phrase in its body copy. This is exactly
the failure CLAUDE.md §2.5 warns about: both lists are scanned over 20 KB of
de-tagged text, so a bare phrase hits real pages.

The conjunction `empty mount AND ratio < 0.02` survives all six cases. It is
still not adoptable: six cases, five of them written by the same person
choosing the rule, measure nothing about real pages.

## Decision

**1. No under-render signal is added to detection or to the ladder.**

The reason is not that the signals are weak. It is what a false positive
costs here, and it is structural rather than empirical.

In AUTO mode `_fetch_urllib` returns the `_BOT_BLOCKED` sentinel *instead
of* the body — the tier 1 HTML is discarded at the moment escalation is
signalled. Every browser tier returns `None` on `ImportError`, and
`_escalate` turns that into `""`. Runtime `dependencies` is empty by
policy (CLAUDE.md §2.4) and the browsers are an optional extra, so the
default install has no browser tier at all.

On that install, a false under-render verdict converts a successful fetch
of a complete page into `("", "none")`: `ok=False` for a page that exists,
which §5.1 names as the worst failure this package has. A change aimed at
one silent failure would manufacture the other, on the most common
deployment, for pages that are perfectly fine.

**2. The gap is documented rather than detected.**

A bullet under README "Known limitations" and a subsection under
`ARCHITECTURE.md` "Detection". A caller who needs guaranteed completeness
is told to force `--js` rather than trust AUTO. This is the fallback #124
named, and it is the honest one: the package cannot detect the condition,
so it says so where a caller looks.

**3. The evidentiary bar is recorded as unmet, not lowered.**

CLAUDE.md §2.5 requires a negative case proving a pattern does not fire on
real content. `tests/fixtures/` holds one captured page, which is not an
SPA, and the suite runs with no network (§3), so the corpus cannot grow
from inside the suite. The bar is not unreasonable — it is unmet, and no
amount of reasoning substitutes for the pages.

## Reopening conditions

This is a decline on the evidence available, not a decision that the
problem is unreal. Any of these changes the answer:

- **A captured corpus with both classes above the floor.** Enough real SPA
  shells and real complete pages — JSON-heavy SSR, galleries, articles with
  widget mounts — to measure a false-positive rate instead of asserting one.
  Captured by hand, the way "Sites tested" was built for the browser tiers.
- **A design that does not discard the tier 1 body.** Whatever is built
  must not route through the `_BOT_BLOCKED` sentinel. A browser-less host
  has to degrade to "the content, plus a warning" rather than to nothing.
  Decision 1 is about that path, not about the idea.
- **A stderr warning before an escalation trigger.** A warning's false
  positive costs one line, not a page, so it clears a far lower bar than
  escalation does. It still needs the corpus: a warning that fires on
  complete pages teaches callers to ignore it, which is worse than silence.

## Alternatives considered

| Alternative | Why rejected |
| -- | -- |
| Ship the surviving conjunction (`empty mount AND ratio < 0.02`) | Tuned on six cases, five of them synthetic and authored alongside the rule. The threshold is fitted to the corpus, not measured against it. |
| Raise `MIN_REAL_CONTENT_BYTES` | Explicitly out of scope in #124, and it does not address the case: a 40 KB page missing its content clears any floor a stub would fail. The floor catches stubs and is doing that job. |
| Escalate on the signal and accept false positives as a latency cost | This is the argument decision 1 refutes. It is only a latency cost where a browser tier exists; on the default install it is total failure. |
| Warn on stderr now, without the corpus | Same precision problem, lower stakes. Recorded as a reopening condition rather than done blind — an unreliable warning is spent credibility. |
| Always escalate JS-looking pages in AUTO | Inverts the package. Tier 1 is the point; a ladder that launches Chrome for anything framework-shaped is `--js` with extra steps. |
| Leave it undocumented | The condition is silent by nature. A caller has no way to learn it from behaviour, which is the argument for writing it down even without a fix. |

## Consequences

| Consequence | Detail |
| -- | -- |
| No code changes | `detection.py`, `network.py` and the pattern counts are untouched. The suite is unchanged at 354 passing. |
| The gap is now stated in two places | README "Known limitations" for the caller, `ARCHITECTURE.md` "Detection" for the reader who wants why. |
| `--js` is the documented answer | A caller needing guaranteed completeness forces the tier rather than trusting AUTO, and now knows to. |
| The fixture corpus is the named blocker | Whoever reopens this starts by capturing pages, not by writing patterns. That is recorded here so the next attempt does not re-derive it. |
| A design constraint outlives the decline | Any future detector must preserve the tier 1 body. Recorded above so it is inherited rather than rediscovered. |

**Upstream:** candidate, not yet filed —
`templates/base/core/quality.md`. Domain skin stripped, the finding is:
*a heuristic whose positive verdict discards the cheap result must be
evaluated against what happens when the expensive fallback is unavailable,
not only against its false-positive rate.* The false-positive rate framing
made this look like a tuning problem for as long as the cost of a false
positive was assumed to be latency. It was not; on the default install it
was the loss of the page.

The second, smaller finding is about spike hygiene and would sit with it: a
spike that cannot clear its own evidentiary bar with the available corpus
should record the corpus gap as its finding, rather than lower the bar to
produce a shippable answer.

Neither is project-specific. Both would read the same in any project with a
cheap path, an expensive fallback, and a detector deciding between them.

## Related

- [ADR-006](006-two-bot-bypass-tiers.md) — the tier model and the naming
  rule this would have had to extend
- [ADR-014](014-keep-network-as-one-module.md) — `network.py` as one
  module, and the conditions for reopening that; the ladder this declines
  to add a rung to
- [ADR-002](002-python-toolchain-and-ci.md) — the coverage ratchet and the
  gate a code change here would have had to clear
