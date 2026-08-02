# ADR-008: Defer a third-party licensing document, and name the triggers

**Status:** Accepted
**Date:** 2026-08-02

## Context

Third-party licensing is recorded in three places: the Dependencies table in
the README, the AGPL paragraph under the README's License section, and the
"nodriver and the AGPL" section in `docs/ARCHITECTURE.md`.

That raised the question of whether a dedicated document — a `NOTICE`, a
`LICENSES` file, or `docs/licensing.md` — should hold it instead.

Two facts decide it. Nothing here is redistributed: `dependencies` in
`pyproject.toml` is empty and every browser import is lazy, so installing
`pagefetch` pulls in no third-party code at all. Apache-2.0's NOTICE
requirement attaches to redistribution, which does not happen. And the AGPL
material is advice to a consumer — "if you install `nodriver` and run a
service on the headed tier, section 13 applies to you" — rather than a
compliance artefact.

The counter-argument is real, though: licensing is not architecture.
`docs/ARCHITECTURE.md` holds it only because that file is the interim
catch-all until arc42 documents exist.

## Decision

**1. No licensing document for now.**

A fourth location would spread a four-row table thinner and raise the
question of which copy is authoritative when they drift.

**2. Add one when any of these becomes true.**

- The package is published to PyPI, where reviewers expect a `LICENSES` or
  `NOTICE` file by convention
- Anything is vendored, bundled or shipped rather than imported lazily
- The dependency list outgrows a readable table

**3. When arc42 lands, the AGPL section moves to Architecture Constraints.**

Not because licensing is architecture, but because this particular fact is a
constraint on it: the AGPL limits how a consumer may distribute a service
built on the headed tier. A standalone `docs/licensing.md` is the
alternative. Pick one — do not keep both.

## Alternatives considered

**Write `docs/licensing.md` now.** Puts licensing in a file named for it,
and gives the arc42 migration a destination that already exists. Rejected as
premature: with nothing redistributed the document would say "MIT, nothing
bundled, one optional AGPL dependency you may choose to install", which the
Dependencies table already says in less space.

**Fold the material into `LICENSE`.** One file, unambiguous. Rejected:
`LICENSE` is the MIT text, and editorialising inside a licence file makes it
harder to verify as the standard text.

**Say nothing and revisit if it comes up.** Rejected because it comes up
repeatedly and gets re-reasoned each time. The triggers above are the point
of this record.

## Consequences

- The three existing locations stay. The README table is the summary,
  `docs/ARCHITECTURE.md` carries the explanation.
- Publishing to PyPI now has a documentation prerequisite attached to it.
- Whoever writes the arc42 documents inherits a decision about where the
  AGPL section lands, rather than an open question.

## Related

- [ADR-006](006-two-bot-bypass-tiers.md) — the tier model the AGPL note
  attaches to
- [ADR-007](007-github-is-the-system-of-record.md) — why this reasoning is
  here rather than only in the tracker
