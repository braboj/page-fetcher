# ADR-018: Land the arc42 documents and retire the interim architecture file

**Status:** Accepted
**Date:** 2026-08-05

## Context

Two accepted records defer to documents that do not exist. ADR-009 created
`docs/ARCHITECTURE.md` as a holding pen and said in its own header that the
file would be restructured as arc42 rather than grown. ADR-008 named
Architecture Constraints as the destination for the AGPL note once arc42
landed, and left a standalone `docs/licensing.md` as the alternative.

`base/core/docs.md` `[ID: docs-arc42]` already specifies the parts that are
easy to get wrong: the boundary between givens and decisions, the `FR01` /
`QG01` ID scheme, black-box context diagrams, and the rule that chapter
bodies cite no decision records because section 9 is the single index.

What it does not specify is the part that only matters in a repository that
already has documentation. It says nothing about where the chapters live
beside `docs/ONBOARDING.md` and `docs/PLAYBOOK.md`, nothing about what
section 9 holds when the records are already a directory of their own, and
nothing about what happens to the file the chapters replace. Those three
are this record.

```text
docs/ARCHITECTURE.md (interim)          docs/arc42/
+-- escalation ladder + tier table  --> 04 strategy, 06 runtime
+-- detection rules                 --> 08 crosscutting
+-- response decoding               --> 08 crosscutting
+-- event-driven waits              --> 08 crosscutting
+-- cache behaviour                 --> 08 crosscutting
+-- configuration rationale         --> 08 crosscutting
+-- URL-scheme boundary             --> 02 constraints, 08 crosscutting
+-- nodriver and the AGPL           --> 02 constraints          (closes #59)
+-- performance history             --> 11 risks and debt
+-- sites tested                    --> 11 risks and debt
```

## Decision

**1. The chapters live in `docs/arc42/`, one file per chapter.**

Thirteen files named `NN_lower_snake_case.md`, numbered 01 to 13, plus a
`README.md` indexing them — which is not a chapter and holds no content of
its own. A flat `docs/` would bury `ONBOARDING.md` and `PLAYBOOK.md` among
thirteen numbered siblings, and the numbering is only meaningful as a set.

**2. Section 9 indexes `docs/decisions/`; it does not restate it.**

One row per record, linking to the file. Copying the reasoning into the
chapter would produce a second copy of an immutable document, and the two
would disagree the first time a record was superseded.

**3. `docs/ARCHITECTURE.md` is deleted, and live references are retargeted.**

The README, `docs/ONBOARDING.md`, `docs/PLAYBOOK.md` and `CLAUDE.md` point
at the chapters instead. Eight merged records cite the old path and are not
edited: an accepted record describes the repository as it stood on its own
date, and the map above is what resolves the path for a reader who follows
one.

**4. The AGPL note lands in Architecture Constraints. There is no
`docs/licensing.md`.**

This is ADR-008 decision 3 carried out rather than reopened. None of its
three triggers has fired: nothing is published to an index, nothing is
vendored or bundled, and the dependency table is still four rows.

## Alternatives considered

| Alternative | Why rejected |
| -- | -- |
| Chapters flat in `docs/` | Matches the reference layout this project was asked to follow, where `docs/` holds nothing else. Here it holds four guide documents and three directories, and thirteen numbered files would make the guides harder to find than they are now. |
| One `docs/arc42.md` holding all twelve chapters | One file to search, no directory. Rejected: the chapters are edited independently and at different rates, and a single file makes every unrelated change collide in review. |
| Section 9 as the ADRs themselves, `docs/decisions/` deleted | Removes the split between a chapter and a record. Rejected: the records are immutable and dated, and folding them into a chapter that is expected to change would destroy that property. |
| Keep `docs/ARCHITECTURE.md` as a pointer to the chapters | Leaves every existing reference valid, including the ones in merged records. Rejected: it keeps a file whose own header says it will be replaced, and it puts a hop between a reader and the content for as long as it survives. |
| Write `docs/licensing.md` as well | Gives licensing a file named for it. Rejected: ADR-008 makes the two options exclusive, and picking both would need a record superseding it rather than one carrying it out. |

## Consequences

| Consequence | Detail |
| -- | -- |
| ADR-008 and ADR-009 are discharged | Both named work that had no home. Neither is superseded — the destinations they specified now exist. |
| A new chapter rule arrives with the chapters | No chapter body cites a decision record, and no chapter refers forward to a higher-numbered one. Both are template rules that are expensive to retrofit and cheap to hold from the start. |
| The redistribution is one-way | The interim file is gone, so the next piece of technical prose is placed by asking which chapter owns it rather than by appending. That is the property ADR-009 wanted and could not have while one file held everything. |
| Eight merged records now cite a path that does not exist | Stated plainly rather than repaired. The map in Context is the resolution; editing the records to fix a link would be editing accepted decision prose. |
| Section 9 has to be extended when a record is added | One row per record, and the PLAYBOOK's ADR procedure gains the step. |

**Upstream:** none yet. The three gaps in Context are candidates —
`[ID: docs-arc42]` specifies chapter content thoroughly and placement not at
all — but one repository landing arc42 once is not enough evidence that the
placement should be a rule rather than a project's choice.

## Related

- [ADR-008](008-defer-a-third-party-licensing-document.md) — named
  Architecture Constraints as the AGPL note's destination
- [ADR-009](009-split-technical-depth-out-of-the-readme.md) — created the
  interim file this record retires
- [ADR-016](016-gate-the-comment-layout-convention.md) — the precedent for
  stating a convention's carve-outs where they are enforced
