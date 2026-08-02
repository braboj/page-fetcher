# ADR-009: Split technical depth out of the README into an architecture document

**Status:** Accepted
**Date:** 2026-08-02

## Context

The README had grown to carry the package's entire technical reference
inline: the escalation ladder diagram and tier table, the detection rules
and why two phrases are held to a higher bar, the event-driven wait
strategy, cache behaviour, the configuration rationale, the URL-scheme
boundary, the AGPL analysis, a nine-version performance history, and a
table of sites tested.

`base/core/readme.md` already forbids this — "SHOULD NOT exceed what a
reader needs to evaluate or use the project — move deep reference content to
`docs/`" — and names the two audiences it was serving badly. Someone
deciding whether to use the package was reading why "no longer available"
counts only below the size floor.

The complication is that arc42 documents are planned but do not exist. Doing
nothing until they do would have left the README wrong for however long that
takes; inventing a partial arc42 structure now would have committed to a
shape before anyone had designed it.

## Decision

**1. Technical explanation moves to `docs/ARCHITECTURE.md`.**

The README keeps what the package does, how to run it, its structure, its
setup, its configuration surface and its limitations. Everything explaining
*how it works internally* moves.

**2. That document is explicitly interim.**

It carries a note at the top saying so. It is a holding pen with a coherent
order, not a designed structure, and it will be restructured as arc42 rather
than grown further.

**3. The README links to it; it links to the ADRs.**

This is the layering ADR-007 and the README template both want: a reader
evaluating the package meets no internal argument, a reader who wants the
reasoning follows one link, and a reader who wants the decision follows a
second. It is also what makes "never cite an ADR from the README"
(`CLAUDE.md` §2.7) possible to obey without losing anything.

## Alternatives considered

**Wait for arc42 and leave the README as it was.** Rejected: the README was
already violating a MUST-adjacent rule in its own template chain, and the
arc42 work has no date. A document that is wrong now does not become less
wrong by being wrong on purpose.

**Create the arc42 skeleton now and file the content into it.** Rejected as
premature. arc42 has twelve sections; filling three and stubbing nine
produces a document that looks abandoned, and it commits to a structure
before anyone has decided which sections this project actually needs.

**Split into several small documents — detection, caching, transports.**
Rejected for now. Three documents of a few hundred words each cost more in
navigation than they save in focus, and arc42 will redistribute the content
anyway. Splitting twice is worse than splitting once.

## Consequences

- `CLAUDE.md` §1.2 gains a placement rule, so the next agent explaining the
  cache does not put it back in the README.
- The AGPL section landed in an architecture document, where licensing does
  not belong. [ADR-008](008-defer-a-third-party-licensing-document.md)
  records where it goes when arc42 lands.
- The performance history and sites-tested table are now further from the
  reader, which is correct — both are measurements about the past, not
  claims about the package.
- Whoever writes the arc42 documents inherits a single file to redistribute
  rather than a README to excavate.

**Upstream:** none. The rule this implements already exists in
`base/core/readme.md`; what was missing was this project obeying it. The two
README conventions that *were* missing upstream are filed separately as
`solid-ai-templates#884` and `#885`.

## Related

- [ADR-007](007-github-is-the-system-of-record.md) — the layering that keeps
  decisions out of user-facing documents
- [ADR-008](008-defer-a-third-party-licensing-document.md) — where the AGPL
  section goes when arc42 exists
