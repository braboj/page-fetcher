# ADR-014: Keep network.py as one module

**Status:** Accepted
**Date:** 2026-08-04

## Context

`quality.md` gained a rule in `v2.41.0` — **Split an oversized module
into a package behind its import path** — and `src/pagefetch/network.py`
is the only file in this repository a reader would point at on seeing it.
Issue #92 raised the question as a spike rather than a task because the
file is almost entirely one class, and a module split on the seams that
class already has is a design change rather than a file move.

### What is actually in the file

```text
  src/pagefetch/network.py — 915 lines

  1      docstring, imports, constants ................  84
  86     require_supported_scheme .....................  25   no self
  113    _decompress ..................................  35   no self
  150    _BatchSession ................................  62   no self
  213    _scroll_page_js ..............................  13   no self
  228    class NetworkFetcher ......................... 688
           244  public PageSource interface ...  67
           311  tier 1: urllib ................  73
           384  tier 2: js ....................  46
           430  tier 3: headed ................  92
           522  tier 4: headless .............. 102
           624  escalation + cache ............ 132
           756  batch ......................... 160
```

Against the other package modules: `__main__.py` 373, `cache.py` 218,
`chrome.py` 187, `detection.py` 180, `source.py` 103, `fake.py` 92,
`__init__.py` 69. So `network.py` is 2.5× the CLI and 4.2× the largest
library module beside it.

The line count is a weaker signal than it looks. #92 measured 897; the
file is 915 now, and every one of those 18 lines is a docstring added by
the `D`-rule adoption in the same `v2.41.0` bump that introduced the
split rule. The metric that triggered the question moved 2% on a change
that added no logic.

### What the rule tests

The split rule is not a size rule. It sits in `quality.md` directly under
**High Cohesion** — "modules that change together should live together; a
module whose parts serve unrelated concerns should be split" — and it
prescribes splitting "by a cohesive seam (data-flow stage is the usual
one)". It names no threshold, and asking whether 915 lines crosses one is
asking a question the rule does not pose.

Posed the way the rule does pose it: `network.py`'s parts do not serve
unrelated concerns. Four tiers are four implementations of one operation,
the orchestrator picks between them, and the batch machinery amortises
one tier's launch cost across a list. A change to escalation policy
touches the orchestrator and at least one tier in the same commit. That
is the cohesion test passing, not failing.

### The seam that does not touch the class

#92 identified it correctly and sized it correctly: `require_supported_scheme`,
`_decompress`, `_BatchSession` and `_scroll_page_js`, about 140 lines,
none of which reference `self`. The problem is that they are not *a*
seam. They are four unrelated leftovers:

| Symbol | Concern | Would sit with |
| -- | -- | -- |
| `require_supported_scheme` | URL validation (ADR-003) | nothing else here |
| `_decompress` | HTTP content-encoding | tier 1, which stays |
| `_BatchSession` | browser lifecycle | the batch loop, which stays |
| `_scroll_page_js` | a JS string literal | tier 2, which stays |

Collected into one submodule they make a junk drawer, which fails
cohesion harder than the status quo. Distributed into four they make four
tiny submodules plus a package `__init__` for a 15% reduction, and three
of the four end up importing back across the boundary they just crossed —
`ACCEPT_ENCODING` is documented as the counterpart to
`DECODABLE_ENCODINGS` and is read by the tier that would stay behind.
That is the rule's own "constants travel with the functions that use
them" violated by the act of following it.

### Moving the tiers is a reshape

`NetworkFetcher` reads its three constructor-injected fields from 16
sites, spread across all four tiers, the cache pair and both batch
starters:

```text
  _ua       274, 299, 328, 402
  _cache    419, 642, 646, 661
  _reaper   445, 447, 537, 539, 785, 787, 811, 814
```

The tiers also cross-call: `_fetch_uc` → `_fetch_uc_with_session`,
`_fetch_nodriver` → `_nodriver_read_page`, and both callees are reached
independently from the batch path. Moving any tier out means passing
`ua`, `cache` and `reaper` explicitly or introducing a strategy protocol
— dependency injection and a new abstraction, not a move.

That is the decisive point, because it is what the rule's verification
recipe assumes you are not doing. The reason the rule forbids touching
the test module is that an untouched suite is a *regression oracle*: it
proves a mechanical move behaviour-neutral precisely because nothing but
file boundaries changed. Change the signatures and the same suite is
still green, but it is no longer evidence of the same thing — it now
passes over rewritten call paths it was never written to distinguish. The
split would spend its own oracle on the change it exists to check.

### The one argument in favour

The per-file ruff exemptions. `network.py` carries four, and `PLR0911`
is granted over all 915 lines to serve one function, `_escalate`. A split
would narrow each exemption to the file that earns it, and `PLC0415`,
`BLE001` and `S110` would land on the tier submodules where the lazy
imports and the deliberate broad catches actually live.

This is real and it is small. It improves a lint configuration; it does
not improve correctness, navigability or the cost of a change. Weighed
against introducing a strategy protocol under a weakened oracle, it does
not pay.

## Decision

**1. `network.py` stays one module.**

The file is long and cohesive. Length alone is not what `quality.md`'s
rule tests, the seam that requires no design change is four unrelated
leftovers rather than a stage boundary, and the seam that would matter
cannot be crossed without reshaping `NetworkFetcher` — which forfeits the
untouched-suite oracle that makes the rule's verification recipe worth
following. #92 is answered and closed by this record.

**2. The section comments are the navigation aid, and they stay.**

Seven of them, one per concern, already delimit what a split would
separate. They are load-bearing under this decision rather than
decorative: they are the reason a 915-line file is navigable, so removing
or blurring them reopens the question this ADR closes.

**3. If a split ever happens, submodules are named for the tiers.**

`http`, `js`, `headed`, `headless` — never `urllib`, `playwright`,
`nodriver`, `seleniumbase`. ADR-006 put the library names out of the
`Transport` members, the flags, the `tier_used` values and the stderr
prefixes; an import path is the one surface that decision has not had to
cover yet, and a split is exactly where it would leak back in. Recorded
now because the person doing the split will be reaching for the library
name as the obvious file name.

**4. What would reopen this.**

Named conditions, so a future reader can check rather than re-argue:

- A fifth tier lands. Six tier sections is past what section comments
  carry, and PLAYBOOK §2.1 already documents adding one.
- The tiers stop sharing state — if `_ua`, `_cache` and `_reaper` are
  ever reached through a passed-in context rather than `self`, the
  reshape this ADR declines has already happened for other reasons and
  the move becomes mechanical.
- A tier acquires enough logic to be independently testable without a
  browser. Today the tier bodies are validated by hand (CLAUDE.md §3),
  which is why the untouched-suite oracle carries so much weight here.

Growth in line count alone is not a trigger. It was not one here.

## Alternatives considered

| Alternative | Why rejected |
| -- | -- |
| Split into `network/` on the four tier boundaries | The design change §Context describes. Needs `ua`/`cache`/`reaper` injected or a strategy protocol, and the four tiers cross-call each other. The payoff is narrower ruff exemptions and a shorter longest file; the cost is a new abstraction landed under a suite that can no longer tell a move from a rewrite. |
| Partial split — move the four `self`-free symbols into `network/` | Buys ~140 lines (15%), leaves the class at ~750, and adds a package directory plus an `__init__` re-export layer to do it. The four have no concern in common, so grouping them fails cohesion and distributing them creates four modules that import back across the boundary. #92 anticipated this: "it does not address what makes the file long." |
| Extract `require_supported_scheme` to a sibling `urls.py` | Defensible on its own merits — public API, its own ADR, its own test file, never touches the network — and it needs no package, since `network.py` importing it keeps `from pagefetch.network import require_supported_scheme` working. But it is ordinary module placement dressed as an answer to #92: 25 lines against 915, and the spike was not asking where URL validation lives. Available later as its own change if it is ever wanted for its own reason. |
| Same, for `_decompress` to a sibling `encoding.py` | Weaker than the above and rejected for a reason of its own. Its docstring is written from tier 1's position — "an encoding this tier cannot undo" — and it exists because tier 1 is standard-library-only. Moving it away from the tier that gives it its shape costs more in provenance than 35 lines are worth. |
| Set a line-count threshold in CLAUDE.md so the question is mechanical next time | Would invent a rule the chain deliberately does not state, and this file is the argument against one: 18 of its lines arrived as docstrings in the same bump that raised the question. A threshold would have fired on that. |
| Leave #92 open as a standing question | An open spike with a known answer is a question nobody asks again and nobody closes. The reasoning is the deliverable, and `docs.md` puts it here. |

## Consequences

| Consequence | Detail |
| -- | -- |
| `network.py` stays the largest file in the package | 915 lines, 4.2× `cache.py`. A reader meeting it for the first time will ask #92's question again; this ADR is the answer they find. |
| The section comments become a documented invariant | Decision 2 makes them structural. A refactor that removes them removes the reason this decision holds — noted in CLAUDE.md §1.2 alongside the existing placement rules. |
| The four ruff exemptions stay broader than they need to be | `PLR0911` in particular covers 915 lines to serve `_escalate`. Accepted as the cost of decision 1, and recorded so a future reader does not mistake breadth for carelessness. |
| ADR-006's scope now includes import paths | Decision 3 extends it to a surface it had not reached. ADR-006 is not amended — it is immutable and its decisions are unchanged; this records where its principle lands next. |
| A fifth tier makes this ADR the first thing to re-read | Decision 4 names it, and PLAYBOOK §2.1 is where someone adding a tier will be standing. |
| No code changes, and the suite is untouched | The verification `quality.md` prescribes for a split — static gates, import smoke check, collection, then the full suite — has nothing to verify. The gate still runs on this PR because the repository runs it on every PR. |

## Related

- [ADR-006](006-two-bot-bypass-tiers.md) — the library names kept out of
  the API, extended to import paths by decision 3
- [ADR-003](003-url-scheme-allowlist.md) — why
  `require_supported_scheme` is in this package at all, and the reason it
  reads as a candidate for extraction
- [ADR-010](010-move-the-package-to-a-src-layout.md) — the last layout
  decision, and the one that made `tests/` importing only the install a
  property this decision relies on
- [ADR-004](004-adopt-solid-ai-templates.md) — the chain the split rule
  arrives through
