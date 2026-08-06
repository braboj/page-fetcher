# ADR-019: What chapter 11 holds, and why it is not shaped like chapter 9

**Status:** Accepted
**Date:** 2026-08-06

## Context

ADR-018 made chapter 9 an index: one row per record, linking to
`docs/decisions/`, with the reasoning left in the records themselves. The
question this record answers is whether chapter 11 should follow — one file
per risk, the chapter as an index — and, having answered no, what the
chapter holds instead.

The question arrived with evidence. Chapter 11's risk table held eight rows
whose Risk and Mitigation cells ran to three sentences each, which is a
paragraph in a grid. Every rule in `[ID: docs-arc42]` was followed. None of
them is about what a table cell may hold: the template governs chapter
content for 2, 3, 8 and 9, and its `IDs and register` subsection names
`FR01`, `QG01` and `Q1` and stops. The register named in its own heading is
the one chapter it never reaches.

The `R-n` / `TD-n` scheme was not from the template either. It came from the
reference arc42 set these chapters were modelled on — the same set that
forward-references its risk IDs from chapters 4 and 8, breaking a rule the
template does state because the neighbouring one is missing.

## Decision

**1. Chapter 11 holds its content. It does not index files.**

ADR-018's reasoning for chapter 9 is about immutability: a decision record
is fixed once merged, and folding one into a chapter that changes would
destroy that property. A register is the opposite kind of artifact. A
probability is edited in place, a mitigated risk is deleted, and the value
of the table is comparing eight rows of probability against impact on one
screen. Applying either shape to both destroys one of them.

The asymmetry is stated in the chapter rather than left to be inferred,
because from outside it looks arbitrary and invites being repaired for
symmetry in either direction.

**2. The table rates; prose explains.**

A cell holds an ID, a one-sentence statement and a rating, plus a mitigation
short enough to scan. An entry needing evidence, a trigger or a
qualification gets a subsection keyed by its ID. An entry with nothing more
to say gets none — one of six risks has no subsection, which is the rule
working rather than being skipped.

**3. An entry rated `Certain` is not a risk.**

Nothing is being predicted. It is debt, or a limitation another chapter
owns. Both entries this removed turned out to be the latter and were
deleted rather than moved: under-rendering was already in the README, in
Crosscutting Concepts and as `Q3` in Quality Requirements, and the
human-gesture challenge was already in System Scope and Context under Out
of scope.

**4. Register IDs are `R01` and `TD01`, and numbers retire.**

Matching `FR01` and `QG01`. Nothing outside the chapter cites a register ID,
so the rename touched one file. A resolved entry is removed and its number
goes with it, stated in the chapter so the next editor does not renumber the
rest. Chapter 10's `Q1…Q16` is left alone: the template writes `Q1…` itself,
so that scheme is upstream's to settle rather than a local deviation.

**5. The Evidence Base leaves chapter 11.**

It was two records of measurement held together by one framing sentence.
Neither is a risk or a debt item, neither carries an ID or a rating, and
neither ever leaves the way a register entry does.

The sites table goes to Quality Requirements under Test Coverage, which
already claims browser transport bodies are validated by hand — the table is
the record of that validation, and its caveat now qualifies the coverage
claim it sits beneath. The ladder history goes to Solution Strategy, whose
Architecture Approach bullets are its conclusions with the measurements
stripped out.

It stays a dated block rather than dissolving into the concepts it
evidences. Four of its nine versions map to Crosscutting Concepts and five
to Solution Strategy and the Runtime View, so no chapter is its home; and
`16s` and `27s` are moving figures, honest as a record of which direction a
change moved things and misleading inside present-tense concept prose.

## Alternatives considered

| Alternative | Why rejected |
| -- | -- |
| One file per risk, chapter 11 as an index | Symmetry with chapter 9. Rejected: that shape exists to protect immutability, which a register does not have. It would also cost a second sole-pointer coupling of the kind PLAYBOOK 4.2 had to be written for, for content that never needed it. |
| A third table in Solution Strategy for the Architecture Approach | The chapter's other two sections are tables, so it would read as consistent. Rejected: their cells already run to ninety words, which is the density this record removes elsewhere. Shorter bullets fix the verbosity without adding to it. |
| Subsections per principle in Solution Strategy | Rejected: seven headings for seven three-line ideas is heavier than what it replaces. A strategy chapter should read at a glance. |
| Dissolve the ladder history into the concepts it evidences | Most faithful to where each conclusion lives. Rejected: it scatters moving figures into present-tense prose, where they read as current performance and rot silently. |
| Keep the Evidence Base in chapter 11 as ADR-018 mapped it | Leaves an accepted record undisturbed. Rejected: the map is in that record's Context, describing the redistribution, not among its four numbered decisions — so this refines a placement rather than superseding one. |
| Wait for `solid-ai-templates#995` to land before changing anything | Rejected: the defect is present now, and the rules were derived from it. This is the same footing #983's rules had while these chapters were written. |

## Consequences

| Consequence | Detail |
| -- | -- |
| Chapter 11 conforms to a proposal, not a rule | `solid-ai-templates#995` is open. None of the six rules governs here until it lands and the pin moves. |
| Two chapters gained content they did not have | Solution Strategy has a fourth section and Quality Requirements a subsection under Test Coverage. Both are back-references from where the content was, so no chapter refers forward. |
| A dangling pointer was found and fixed | PLAYBOOK 3.7 named a "Sites tested" table in the README, which stopped being true when ADR-009 split technical depth out. It was already broken before this change. |
| Four merged records cite the old locations | ADR-006, 009, 017 and 018. Not edited, per ADR-018: fixing a link in a merged record is editing accepted decision prose. |
| Applying a rule changed the rule | Rule 1 read literally deletes the mitigation column; rule 2 was expected to relocate entries and instead deleted them. Both findings went back to #995, because a rule that has never been applied is a proposal about writing. |
| Register entries still schedule nothing | `TD01` and `R03` have no issue behind them. Whether a row may carry one is the open question on #995, not a gap this record closes. |

**Upstream:** filed —
[`solid-ai-templates#995`](https://github.com/braboj/solid-ai-templates/issues/995),
`templates/base/core/docs.md` `[ID: docs-arc42]`. Domain skin stripped, the
generic finding is: *where a document set holds both immutable records and
mutable registers, the container shape has to follow which one it is, and
stating why prevents the wrong migration in either direction.* Decisions 2,
3 and 4 are the same filing; decision 5 is not, being a placement question
of the kind ADR-018 already declined to propose from one repository.

## Related

- [ADR-018](018-land-the-arc42-documents.md) — made chapter 9 an index, and
  mapped the Evidence Base into chapter 11 in its Context
- [ADR-017](017-decline-under-render-detection-at-tier-1.md) — the decline
  that gave under-rendering the homes making its risk row a fourth copy
- [ADR-009](009-split-technical-depth-out-of-the-readme.md) — split
  technical depth out of the README, which is when PLAYBOOK 3.7's pointer
  started dangling
