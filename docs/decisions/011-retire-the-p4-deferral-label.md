# ADR-011: Retire the P4 deferral label

**Status:** Superseded by [ADR-012](012-correct-adr-011s-deferral-fallback.md)
**Date:** 2026-08-02

## Context

The chain defines `P4` as a deferral marker rather than a severity, and
defines it as optional. `platform/github.md` files it under a heading that
says so — "Deferral label (optional)" — and `base/workflow/issues.md`
states the rule directly: every issue MUST carry exactly one of `P0`–`P3`;
`P4` is "optional and additional". Carrying the label is therefore a
project's choice, not a requirement it inherits.

This repository chose to carry it, and used it twice. Both uses duplicate
a record the repository already holds:

- **#59** — "Give third-party licensing its own document", labelled
  `task, P3, P4`. Its deferral is
  [ADR-008](008-defer-a-third-party-licensing-document.md), a decision
  record whose entire subject is that deferral and why.
- **#9** — "Can the PerimeterX Press & Hold challenge be automated?",
  labelled `spike, P3, P4`. The README's limitations list states that
  Press & Hold blocks every tier, and `ARCHITECTURE.md`'s blocked-site
  table records adorama.com as "manual only".

```text
  the label says          the repository already says
  ----------------        ---------------------------
  #59  P4  "someday"  <-- ADR-008: deferred, with the reasoning
                          and the condition that would revive it
  #9   P4  "someday"  <-- README limitations + ARCHITECTURE blocked
                          sites: every tier fails, manual only

  P4 carries the fact. Neither copy carries the reason.
```

That asymmetry is the problem. A label records *that* something is
deferred and can record nothing about *why*, and ADR-007 settled how this
repository treats that class of thing: GitHub is the system of record
precisely so that nothing which outlives a ticket exists only in a view.
A label is a view. It does not survive a migration, it is invisible to a
clone, and it is not where a reader looks for reasoning.

The chain also offers a stronger mechanism for work that is genuinely
deferred. `base/workflow/issues.md` `[ID: base-issues-defer]` prescribes a
Backlog-milestoned issue with explicitly named trigger conditions, and
marks it as distinct from "a P4 'someday' issue" — the distinction being
that the deferral is deliberate, the trigger is named, and the work is
sized. Where deferral needs to be visible in the issue list, that is the
mechanism the chain points at.

## Decision

**1. The `P4` label is deleted from the repository and not recreated.**

Deleting it removes it from #59 and #9. Both keep `P3`, which is the
severity they already carried — nothing is inferred or reassigned, because
`P4` never encoded a severity.

**2. A deferral is recorded where its reasoning is.**

An ADR when the deferral is a decision, as with ADR-008. The README or
`ARCHITECTURE.md` when it is a standing limitation, as with #9. Both
outlive the ticket, both survive a tracker migration, and both have room
for the reason.

**3. Where deferral needs to be filterable, the mechanism is
`[ID: base-issues-defer]`, not a label.**

A Backlog milestone with named trigger conditions. This ADR does not adopt
one — see the alternatives — but it names what to reach for rather than
leaving the next deferral to reinvent the question.

**4. Severity is untouched.**

Every issue still carries exactly one of `P0`–`P3`, applied at creation.
This ADR changes what the repository does with the optional fifth label
and nothing else.

## Alternatives considered

| Alternative | Why rejected |
| -- | -- |
| Keep `P4` and keep using it | The filterability it buys is the whole case for it, and at eight open issues it buys nothing — "which are deferred" is answered by reading the list. Both existing uses duplicated a durable record, so the label's two data points are both arguments against it. |
| Keep the label, drop it from #59 and #9 | Leaves an unused label sitting in the repository, and the next deferral reopens the same question with no record of how it was answered. Deciding once is the point. |
| Adopt a Backlog milestone with trigger conditions now | Premature. Neither issue needs it: ADR-008 already names what would revive #59, and #9's trigger is "PerimeterX changes its challenge", which is not an observable event anyone will watch for. Standing up milestone machinery for two issues that are already documented is process without a reader. Adopt it when a deferral actually needs a named trigger. |
| Record the divergence in CLAUDE.md instead of an ADR | ADR-010 rejected exactly this shape — a deviation note in CLAUDE.md is where reasoning goes to be forgotten, and that one survived long enough to be wrong. `docs.md` wants the decision at the moment it is made. |

## Consequences

| Consequence | Detail |
| -- | -- |
| Deferral stops being filterable in the issue list | The cost upstream ADR-021 named when it rejected dropping `P4` at template level: "removing it pushes the information into prose, where it stops being filterable". Accepted knowingly, at this repository's size, and reversible — recreating a label is a one-line command. |
| The repository diverges from the chain's label set | Divergence from an option, not from a MUST. `platform/github.md` files `P4` under "(optional)", and `base/workflow/issues.md` makes only `P0`–`P3` mandatory. Nothing in the chain requires the label to exist. |
| CLAUDE.md §2.1 and `PLAYBOOK.md` §1.4 lose their `P4` clauses | Both currently explain that `P4` accompanies a severity rather than replacing one. With no label, there is nothing to explain. |
| The dev journal keeps its `P4` entries | The journal records what happened, including creating the label and reconciling it against the chain. It is not corrected when a decision changes. |
| #59 and #9 read as ordinary `P3` issues | Their deferred status now lives only in ADR-008 and in the README and `ARCHITECTURE.md` respectively — which is the decision, not a side effect of it. |

**Upstream:** none. The chain already makes `P4` optional, so a project
declining it is the template working as written rather than a defect in
it. Upstream ADR-021's rejection of "drop `P4` entirely" was a decision
about the template's vocabulary, not a requirement that every project
populate it.

## Related

- [ADR-004](004-adopt-solid-ai-templates.md) — the chain whose optional
  label this declines
- [ADR-007](007-github-is-the-system-of-record.md) — why durable
  information does not live in a view
- [ADR-008](008-defer-a-third-party-licensing-document.md) — the record
  #59's label duplicated
