# ADR-007: Make GitHub the system of record and keep the tracker replaceable

**Status:** Accepted
**Date:** 2026-08-02

## Context

This repository uses two systems. GitHub holds the code, the pull requests
and the CI gate. Linear holds the backlog, and is used because its UI makes
planning easier than GitHub issues do.

Nothing said which of the two is authoritative. That question only matters
on the day the tracker changes, which is exactly when it is too late to
answer it — so the answer has to be written down while the cost of acting
on it is still zero.

The tracker's own data is portable. Linear exports through its API and Jira
imports it. The lock-in is elsewhere, in two forms that accumulate through
ordinary use:

**Identifiers in permanent artefacts.** `Refs BRA-596` in a commit message
is immutable. After a migration it names nothing. The same applies to a PR
title. A branch name is different: branches are deleted after merge, so a
tracker identifier there costs nothing and buys the in-flight status
transitions the integration provides.

**Rationale that exists only in a ticket.** A well-written ticket
description explaining why something was deferred, and what would change the
answer, is real content. Left in the tracker it survives a migration only as
a row in an export nobody reads.

Nine commits already carry `Refs BRA-…`, and CLAUDE.md mandated the Linear
identifier in PR titles as well as branch names. The exposure was small only
because the convention was two days old.

## Decision

**1. GitHub is the system of record. Linear is a view over it.**

Linear is kept for its UI and may be replaced with Jira or anything else.
The replacement must cost nothing beyond the migration itself.

**2. Nothing durable lives only in the tracker.**

Decisions go in `docs/decisions/`. Rationale and specifications go in
`docs/`. A ticket description MUST NOT be the only copy of anything that
outlives the ticket. What the tracker carries — status, ordering,
assignment, who is working on what — is worthless after a migration anyway,
so losing it costs nothing.

**3. A tracker identifier belongs in a branch name and nowhere else
permanent.**

Branch names are ephemeral. PR titles carry the GitHub issue number, which
lives with the repository and survives any tracker change. Commit messages
follow the same rule.

**4. Existing commits stay as they are; unmerged titles do not.**

Nine commits carry `Refs BRA-…`. Rewriting merged history to remove them
would cost more than the dead references are worth.

Pull request titles are different. This repository squash-merges, so a PR
title becomes a commit subject on `main` — permanent, and reached by anyone
reading the log. The three open PRs were retitled to drop their `(BRA-…)`
suffix before merging, because the cost of doing so was one command each
and the cost of not doing so was three more dead references in the history
this record exists to protect.

## Alternatives considered

**Drop Linear and use GitHub issues alone.** No lock-in at all, and one
place to look. Rejected: the tracker earns its place on planning ergonomics,
which is a real benefit, and the rules above reduce the switching cost to
near zero without giving that up.

**Mirror everything into GitHub issues automatically.** Two-way sync keeps
both sides complete. Rejected as insufficient rather than wrong — sync
copies issues, but it does nothing about an identifier already written into
a commit message, which is the part that actually cannot be undone. Sync is
worth enabling; it is not the answer to this question.

**Say nothing and deal with it at migration time.** Rejected: every commit
and PR title written before the rule exists is permanent. The cost of the
rule is one paragraph now against an unbounded cleanup later.

## Consequences

- CLAUDE.md section 2.1 changes: PR titles carry the GitHub issue number,
  not the Linear identifier. Branch names are unchanged.
- A ticket that records a decision has to be accompanied by an ADR. The
  ticket becomes a pointer rather than the record — as this one does for
  the licensing-document deferral.
- Whether Linear's two-way sync is enabled for this repository needs
  checking before anyone creates an issue on either side by hand, or the
  same work ends up filed twice.
- Nine commits and two PR titles keep dead-reference identifiers. Accepted.

## Related

- [ADR-004](004-adopt-solid-ai-templates.md) — adoption of the template
  chain whose issue conventions this modifies
