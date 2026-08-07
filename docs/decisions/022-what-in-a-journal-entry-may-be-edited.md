# ADR-022: What in a dev journal entry may be edited

**Status:** Accepted
**Date:** 2026-08-07

## Context

The upstream-history entry at the foot of `docs/dev-journal.md` says the
README's "Performance history" section carries the per-version detail. It
does not. ADR-009 moved that content to the interim architecture file, and
ADR-018 moved it again into chapter 4, where it is now "How the Ladder Was
Tuned". The sentence has pointed at nothing since the first of those moves.

The 2026-08-06 session found it and left it, because nothing said whether a
journal entry may be edited at all. That was raised rather than decided, and
carried forward as an open item since.

The uncertainty is reasonable. Chapter 9 states that decision records are
immutable once merged — changed by superseding, never by editing — and the
journal sits beside them as the other historical record, which invites the
same treatment. `base/core/docs.md` requires the journal and prescribes what
an entry must contain, but says nothing about amending one. Its writing-style
section points the other way: remove outdated documentation promptly.

## Decision

**1. The account of what happened is immutable.**

What a session changed, why a decision went the way it did, what it got
wrong, and what it left undone are the record. A later entry corrects an
earlier one; rewriting the earlier one falsifies it. This covers the **Not
done** lists in particular — a carried item is closed by the next entry
saying so, never by editing the entry that raised it.

**2. A cross-reference is not part of that account.**

A pointer tells the reader where something is now. It makes no claim about
what was true during the session, so correcting it to the current target
changes nothing the entry asserts — and leaving it stale breaks the one
thing the pointer was for. Correct it in place, with no amendment marker.

**3. The test is whether the edit changes what the entry claims happened.**

If following a sentence to its target is the only thing that fails, it is a
pointer. If the sentence would read differently to someone reconstructing
the session, it is the account, and it stands.

**4. A target that is gone rather than moved is said to be gone.**

The correction names where the content went, or records that it went
nowhere. Deleting the sentence loses the fact that the detail existed, which
is itself part of the account.

## Alternatives considered

**Treat the journal as immutable, like the decision records.** Rejected on
purpose rather than on symmetry. The two documents fail differently: nobody
navigates by an ADR to find current state, so a stale pointer inside one is
inert, while `docs.md` gives the journal a single job — continuity for an
agent with no memory across sessions — which a pointer leading nowhere
defeats directly. The breakage also accumulates: under this rule every
future move of a documented target adds another dead reference, permanently.

**Correct the pointer but mark the correction.** A footnote or a bracketed
note at each site. Rejected because at nineteen entries and growing the
markers would outweigh what they annotate, and git already holds the
previous text with the commit that changed it.

**Delete the sentence carrying the dead pointer.** Rejected: it would remove
the fact that per-version detail exists at all, which is the useful half of
the sentence and part of the account under point 1.

## Consequences

- The upstream-history entry now points at
  `docs/arc42/04_solution_strategy.md`.
- Moving a document that the journal cites means sweeping the journal in the
  same change. It is one `rg` over `docs/`, and it is the same sweep
  `quality.md` already requires for a stale citation.
- The **Not done** lists remain exactly as written, including the items this
  session closes. Reading the journal back still shows what each session
  believed was outstanding at the time.
- A future entry that cites a moving target should prefer the stable name —
  the chapter, not the heading inside it — since headings move more often
  than the documents holding them.

## Related

- Chapter 9 gains a row per this record.
- **Upstream:** candidate — `base/core/docs.md`, whose development journal
  section defines the entry format but not whether an entry may be amended,
  while its writing-style rule on outdated documentation implies one answer
  and the surrounding treatment of historical records implies the other.
