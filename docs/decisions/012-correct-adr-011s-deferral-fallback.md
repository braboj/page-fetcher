# ADR-012: Correct ADR-011's deferral fallback

**Status:** Accepted
**Date:** 2026-08-02

## Context

[ADR-011](011-retire-the-p4-deferral-label.md) retired the `P4` label
earlier today. It rested on four claims, and the submodule bump in #81 —
the same session, hours later — refuted one of them.

Its third decision named a fallback: where deferral needs to be
filterable, reach for `[ID: base-issues-defer]`'s Backlog-milestoned
issue with explicitly named trigger conditions. Upstream `5a73dc0`,
inside the bumped range `a835374..244d3ff`, deleted that mechanism.

```text
  base-issues-defer

  at a835374 (what ADR-011 read)     at 244d3ff (the new pin)
  ------------------------------     ------------------------
  the right home is a                the right home is an open
  Backlog-milestoned issue with      issue carrying the P4 deferral
  explicitly named trigger           marker and explicitly named
  conditions ... distinct from       trigger conditions ... Do NOT
  a P4 "someday" issue               park the work in a named
                                     holding milestone instead
```

`platform/github.md` moved with it: the `Backlog` and `Expedite` lanes
are gone, replaced by "Deferral is carried by the `P4` label and urgency
by the severity label."

So ADR-011 points at a mechanism the chain now forbids. Three things are
worth separating, because they do not all fail together.

**What upstream refuted.** The fallback, and only the fallback. There is
no milestone route to filterable deferral at the new pin.

**What upstream inverted.** ADR-011 argued a label is a view that does
not travel; upstream argues the opposite way round — "a lane's meaning is
lost the moment the milestone is closed or deleted, while a label travels
with the issue." Both are correct about different failure modes. Against
a milestone, a label is the more durable of the two.

**What still stands.** ADR-011's actual claim was narrower than that
inversion touches: a label records *that* something is deferred and
cannot record *why*. Upstream does not dispute it — `base-issues-defer`
pairs the label with named trigger conditions in the issue body, which is
where its reasoning lives. This repository kept the reasoning, in ADR-008
for #59 and in the README and `ARCHITECTURE.md` for #9, and dropped the
marker. The delta is filterability, which ADR-011 accepted in writing.

The arithmetic behind that acceptance has not moved. Eight open issues,
two deferrals, both durably recorded.

## Decision

**1. The deletion stands.** `P4` stays retired. Nothing about the two
deferred issues or their records changes.

**2. ADR-011's third decision is withdrawn.** There is no milestone
fallback. A future deferral that needs to be filterable does not get one
by standing up a lane, because the chain forbids it at this pin.

**3. The divergence is restated accurately.** ADR-011 described declining
an optional label. That was true of the chain it read and understates the
chain at the new pin: `P4` is still filed under "Deferral label
(optional)" and `issues.md` still calls it "optional and additional", but
`base-issues-defer` now names it as the carrier of deferral and offers no
alternative. This repository declines a named mechanism, not an unused
option.

**4. The route back is the label, not a lane.** If deferral needs to
become filterable here, recreate `P4` and follow `base-issues-defer` as
written — the label plus named trigger conditions in the body. The ADR
that does so supersedes this one.

## Alternatives considered

| Alternative | Why rejected |
| -- | -- |
| Restore `P4` now | The bump changed the fallback, not the facts ADR-011 decided on: still eight open issues, still two deferrals, both still recorded where their reasoning is. Reversing a decision because a neighbouring rule moved — while the ground under it did not — is churn, and it would relabel the same two issues twice in one day. |
| Leave ADR-011 as written and note the correction in CLAUDE.md | `docs.md` makes merged ADRs immutable and asks for supersession. ADR-011 rejected this exact shape when it declined to record its own reasoning as a CLAUDE.md deviation note, and ADR-010 rejected it before that. |
| Adopt `base-issues-defer` as written | That is restoring `P4`, reached by a different sentence. Same rejection. |
| Treat the inversion as refuting ADR-011 entirely | Overreads it. Upstream's durability argument is about a label versus a milestone; ADR-011's is about a label versus a decision record. Both can hold, and the second is the one this repository acted on. |

## Consequences

| Consequence | Detail |
| -- | -- |
| ADR-011's status flips to superseded | Done in the PR that lands this ADR, per `docs.md`. Its decision to delete the label survives; this ADR is the one to read for what the chain now says around it. |
| The repository has no filterable deferral marker and no sanctioned substitute | Stated plainly because ADR-011's fallback made it sound like there was one in reserve. Deferral lives in ADR-008 and in the README and `ARCHITECTURE.md`, and is found by reading, not filtering. |
| A conformance audit will find the divergence | It should — and it should land here rather than treat a missing `P4` as drift. CLAUDE.md §2.1 and `PLAYBOOK.md` §1.4 both point at this ADR for the reason. |
| The next bump touching `base-issues-defer` needs this ADR re-read | The rule moved twice in one upstream range's worth of history. A third move is not unlikely, and this record is what makes the next reconciliation cheap. |

**Upstream:** none filed. The chain's letter still permits what this
repository does — `P4` is optional in both places that define it. That it
is simultaneously optional and the only sanctioned mechanism is a tension
worth recording, and it is recorded here rather than raised.

## Related

- [ADR-011](011-retire-the-p4-deferral-label.md) — superseded by this
- [ADR-008](008-defer-a-third-party-licensing-document.md) — where #59's
  deferral actually lives
- [ADR-004](004-adopt-solid-ai-templates.md) — the chain this reconciles
  against
