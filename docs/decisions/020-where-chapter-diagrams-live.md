# ADR-020: Where chapter diagrams live, and in which format

**Status:** Accepted
**Date:** 2026-08-07

## Context

The arc42 chapters carried their diagrams inline: seven Mermaid blocks and
three ASCII trees. Two of those went past what either form holds. Chapter
6's escalation ladder needed an edge that skips a rung, drawn in ASCII as a
pipe running down the left margin with a comment explaining where it lands.
Chapter 10's quality tree grew a third level when the ISO 25010
sub-characteristics arrived, and a leaf long enough to wrap broke the
column it sat in — the continuation line carries its own pipes, and the
indent has to be counted by eye.

`base/core/docs.md` already answers the format question: Mermaid for
flowcharts and sequence diagrams, draw.io for complex visual diagrams, raw
editable sources committed alongside rendered outputs. What it does not say
is where the sources go, and a repository with no diagram directory has no
obvious answer.

## Decision

**1. Chapter diagrams live in `docs/assets/`, named for the chapter that
embeds them.**

`03_business_context_diagram`, `10_quality_tree`, and so on. The chapter
number in the filename is what makes an orphaned asset visible.

**2. Each diagram is a `.drawio` source and a `.png` export, both
committed.**

The source is the editable artefact; the export is what the chapter embeds,
because a `.drawio` does not render on the code host. Committing only the
PNG makes the diagram unmaintainable, which `docs.md` already forbids.

**3. Sequence diagrams stay inline as Mermaid.**

Chapter 6's five fetch scenarios are sequence diagrams, which is the case
`docs.md` names for Mermaid. They are legible as text in a diff, and
nothing about them needs a layout decision.

**4. A generator that emits a `.drawio` is not committed.**

The quality tree's 38 nodes were laid out by a script, because centring a
parent on the span of its children is arithmetic rather than judgement.
That script stays out of the repository. Committing it would create a
second source for one diagram, and the next person to open the file in
draw.io would have their work overwritten by a re-run.

**5. The export is read before it is committed.**

An `mxCell` carrying `edge="1"` and no `<mxGeometry>` child is dropped from
the render silently: no warning, no error, exit status zero, and the arrow
simply absent from the PNG. Eleven edges vanished that way before the first
export was looked at. Diffing the XML does not catch it, and neither does
any check that could reasonably be written.

## Alternatives considered

**Keep everything inline.** Free to diff, no export step, no binary in the
tree. Rejected on the two diagrams that motivated this: the ladder and the
quality tree are the two most load-bearing figures in the set, and both had
outgrown the form.

**Commit only the source and render on the code host.** No host in use
renders `.drawio`. Mermaid would qualify, which is why sequence diagrams
stay in it.

**Put the assets under each chapter.** `docs/arc42/assets/` scopes them to
arc42 and would need a sibling the first time the README or a decision
record wants a figure. `docs/assets/` costs nothing now and does not have
to move later.

## Consequences

- Seven diagrams to keep current, each needing a manual export. The command
  is in PLAYBOOK 4.7 along with the `mxGeometry` trap.
- A binary artefact per diagram in the history. Accepted: the PNGs are tens
  to hundreds of kilobytes and change only when the source does.
- A stale export cannot be detected automatically. Nothing compares the PNG
  against its source, so a committed source with an unexported change is
  invisible until someone looks at the chapter.
- `.gitignore` gains `.$*.drawio.bkp` — draw.io writes a backup beside the
  file being edited, and it is churn.

## Related

- Supersedes nothing.
- `base/core/docs.md` governs the format split and the
  sources-alongside-outputs rule; this record answers only the placement
  and the local conventions around it.
- **Upstream:** candidate — `base/core/docs.md`, "Diagrams and assets", for
  decision 4 only. Stripped of the diagram framing it reads: an artefact
  committed as a hand-editable source has exactly one authority, so a
  generator that produced it is scaffolding and is not committed. Filed as
  `solid-ai-templates#998`. The rest stays here: the format split is
  already upstream, and chapter-numbered filenames and reading the export
  are specific to a repository that hand-authors draw.io XML.
