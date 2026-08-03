# ADR-013: Deferral after P4 is retired upstream

**Status:** Accepted
**Date:** 2026-08-03

## Context

[ADR-012](012-correct-adr-011s-deferral-fallback.md) closed by predicting
its own next reading: "The next bump touching `base-issues-defer` needs
this ADR re-read. The rule moved twice in one upstream range's worth of
history. A third move is not unlikely."

The third move is this bump, `v2.42.0` → `v2.44.0`. Upstream `8cda540`
retires `P4` outright and moves deferral onto the milestone field, and
`99f7e01` sweeps the surfaces that still instructed it.

```text
  base-issues-defer, three readings

  ADR-011 read              ADR-012 read              this pin
  (a835374)                 (244d3ff .. v2.42.0)      (v2.44.0)
  ------------------        ---------------------     -----------------
  Backlog-milestoned        open issue carrying       open, UNmilestoned
  issue + named trigger     the P4 marker + named     issue + named
  conditions                trigger conditions        trigger conditions
                            Do NOT park it in a       Do NOT add a label
  distinct from a P4        named holding lane        or a holding lane
  "someday" issue

  a lane                    a label                   the absence of a
                                                      field
```

The label is not merely un-named now; it is forbidden.
`platform/github.md` deletes its "Deferral label (optional)" table and
replaces it with "There MUST NOT be a fifth priority label."
`issues.md` states "Priority is severity and nothing else."
`platform/linear.md` narrows its prohibition to `P0`–`P3`.

`docs.md` gained a rule in the same range requiring a reconciliation that
touches a recorded divergence to say whether it still holds, and to
separate what the range refuted from what it merely moved nearby. The
three paragraphs below are that separation.

**What the range refuted.** Two of ADR-012's four decisions, both about
where deferral could go rather than about where this repository put it.

- Decision 2, "there is no milestone fallback", is false at this pin.
  There is one, and it is the only sanctioned mechanism.
- Decision 4, "the route back is the label, not a lane", is closed. The
  route ADR-012 held in reserve — recreate `P4`, follow
  `base-issues-defer` as written — would now create a label the chain
  forbids.

**What it moved nearby without refuting.** ADR-011's load-bearing claim:
a label records *that* something is deferred and can record nothing about
*why*. Upstream did not dispute it and has now acted on it, arriving at
the same place by a different route — it deleted the label and kept the
named trigger conditions, which are the half that carries reasoning. The
durability argument ADR-012 recorded as an inversion (a label travels, a
lane does not) is moot: neither carrier survived.

**Whether the divergence still holds.** It does not. It closed, and not
by this repository moving. `P4` was deleted here on 2026-08-02 and
forbidden upstream on 2026-08-03, so the label set is conformant for the
first time since ADR-011 — the absence a conformance audit would have
flagged as drift is now the required state.

What replaces it is not a new divergence but an inert mechanism. This
repository has never created a milestone. All six open issues are
unmilestoned, so "unmilestoned means backlog" is true of every one of
them and distinguishes none. The rule is satisfied vacuously rather than
followed, which is a different thing from being declined, and neither
`issues.md` nor `github.md` addresses it — `github.md` makes milestones
optional in the same breath that `issues.md` makes the field carry
deferral.

One more correction, to this repository's own record rather than to the
chain. ADR-011 named two deferrals, #59 and #9, because both carried
`P4`. Re-read against `base-issues-defer`, only one is:

- **#59** is trigger-gated. Its body already carries three concrete,
  observable trigger conditions under "Do it when one of these happens",
  and [ADR-008](008-defer-a-third-party-licensing-document.md) carries
  the reasoning. This is `base-issues-defer` in substance, written
  before the rule required it.
- **#9** is not deferred. It is an open `P3` spike with an ordered,
  cheapest-first next step — test whether challenge frequency tracks
  request velocity — and nothing gating it but severity. Its `P4` was
  recording low priority twice.

## Decision

**1. `P4` stays retired, and stops being a divergence.**

ADR-011's first decision outlives both corrections to it. Nothing about
the label, the two issues, or their records changes; what changes is that
the chain now requires the state this repository already had.

**2. ADR-012's decisions 2 and 4 are withdrawn.**

Decision 2 was a statement about the chain that the chain has since
falsified. Decision 4 named a route that is now forbidden. Decisions 1
and 3 are absorbed above: the deletion stands, and the divergence it
described no longer exists to restate.

**3. Milestones are not adopted, and the milestone field is not a
deferral carrier here.**

Deferral continues to be recorded where its reasoning is — an ADR when it
is a decision, the README or `ARCHITECTURE.md` when it is a standing
limitation. This is not declining the chain's mechanism: `github.md`
makes milestones optional, and a repository with none satisfies
"unmilestoned means backlog" for every issue it has. It is recorded so
that a future audit reading six unmilestoned issues against that sentence
finds out why the field says nothing, instead of concluding that
everything is deferred or that nothing is tracked.

**4. Named trigger conditions in the issue body are the discipline this
repository takes from `base-issues-defer`.**

It is the half that works at six open issues, it costs nothing, and #59
already satisfies it. #9 is reclassified as an ordinary `P3` spike rather
than a deferral, so it needs no trigger conditions and gets none.

## Alternatives considered

| Alternative | Why rejected |
| -- | -- |
| Adopt milestones so deferral becomes filterable | Standing up release-planning machinery to give six issues a field that would distinguish one of them. ADR-011 rejected this exact shape for the `Backlog` lane — "process without a reader" — and the arithmetic has moved in the same direction since: six open issues now, and one deferral rather than two. |
| Recreate `P4` under ADR-012's decision 4 | Not available. `github.md` now states a fifth priority label MUST NOT exist, so following ADR-012's reserved route would break the label conformance check it was meant to survive. |
| Read the retirement as vindicating ADR-011's decision 3 and reinstate it | Overreads it. ADR-011's fallback was a `Backlog` **lane**, which `github.md` still forbids by name. Upstream moved to the *absence* of a milestone, which is the opposite of a named one. |
| Leave ADR-012 standing and note the correction in CLAUDE.md | `docs.md` makes merged ADRs immutable and asks for supersession. ADR-010, ADR-011 and ADR-012 each rejected this shape in turn; a fourth rejection is not a new judgement. |
| Treat #9 as still deferred and give it a deferral note | Would manufacture a gate that does not exist. Its cheapest acceptance criterion is a measurement anyone could run today, and writing "do not pick up before a trigger fires" over it would suppress the one step the issue is asking for. |

## Consequences

| Consequence | Detail |
| -- | -- |
| ADR-012's status flips to superseded | Done in the PR that lands this ADR, per `docs.md`. ADR-011 stays superseded by ADR-012 — supersession is a chain, not a re-pointing, and ADR-012 is still the record of why the fallback went away. |
| Three live surfaces lose their `P4` clauses | CLAUDE.md §2.1 and §5.2 and `PLAYBOOK.md` §1.4 each explain a label that no longer exists in either the repository or the chain. `quality.md` gained a rule in this same range making that sweep mandatory rather than tidy: a retirement is done when a search returns only historical records. |
| ADR-011, ADR-012 and the dev journal keep every `P4` mention | They are the historical records that rule exempts. Correcting them would destroy the record of a rule that moved three times in four bumps, which is the most useful thing this sequence produced. |
| Deferral is still found by reading, not filtering | Unchanged since ADR-011, and now the chain's position too rather than a cost accepted against it. |
| The next bump touching `base-issues-defer` needs this ADR re-read | Kept from ADR-012 verbatim, because the reason is stronger than when it was written: three movements across four bumps, two of them inside a single day. |

**Upstream:** one gap worth filing, and it is the one decision 3 works
around. `issues.md` makes the milestone field the carrier of deferral
while `github.md` makes milestones optional, so a project that uses none
has a rule it cannot violate and cannot use. Upstream #960, which drove
the retirement, assumes milestones are in use throughout; #866 made them
optional and did not revisit it. Searched upstream first per PLAYBOOK
§4.5 — no open or closed issue covers the combination.

## Related

- [ADR-012](012-correct-adr-011s-deferral-fallback.md) — superseded by
  this
- [ADR-011](011-retire-the-p4-deferral-label.md) — the retirement that
  survives both corrections
- [ADR-008](008-defer-a-third-party-licensing-document.md) — where #59's
  deferral actually lives, and the only trigger-gated one left
- [ADR-004](004-adopt-solid-ai-templates.md) — the chain this reconciles
  against
