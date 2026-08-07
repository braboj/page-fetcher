# Architecture Decisions

Decision records live in `docs/decisions/`, one file per record, immutable
once merged. A decision is changed by superseding it, never by editing it,
so a superseded record stays in place with its status pointing at the one
that replaced it. This chapter is the index; the reasoning, the
alternatives that were rejected and the consequences are in the records
themselves. No other chapter cites one.

Adding a record adds a row here.

| ID | Decision | Status | Date |
| ---- | ---------- | -------- | ------ |
| [ADR-001](../decisions/001-extract-pagefetch-into-standalone-repo.md) | Extract pagefetch into a standalone repository | Accepted | 2026-07-26 |
| [ADR-002](../decisions/002-python-toolchain-and-ci.md) | Python toolchain and CI | Accepted | 2026-07-26 |
| [ADR-003](../decisions/003-url-scheme-allowlist.md) | Allowlist URL schemes; leave private-range blocking to the caller | Accepted | 2026-07-26 |
| [ADR-004](../decisions/004-adopt-solid-ai-templates.md) | Vendor solid-ai-templates as the source of project conventions | Accepted | 2026-07-30 |
| [ADR-005](../decisions/005-chrome-ownership-by-ancestry.md) | Decide Chrome ownership by process ancestry, and kill nothing otherwise | Accepted | 2026-07-30 |
| [ADR-006](../decisions/006-two-bot-bypass-tiers.md) | Keep two bot-bypass tiers, ordered by cost and split by display | Accepted | 2026-08-02 |
| [ADR-007](../decisions/007-github-is-the-system-of-record.md) | Make GitHub the system of record and keep the tracker replaceable | Accepted | 2026-08-02 |
| [ADR-008](../decisions/008-defer-a-third-party-licensing-document.md) | Defer a third-party licensing document, and name the triggers | Accepted | 2026-08-02 |
| [ADR-009](../decisions/009-split-technical-depth-out-of-the-readme.md) | Split technical depth out of the README into an architecture document | Accepted | 2026-08-02 |
| [ADR-010](../decisions/010-move-the-package-to-a-src-layout.md) | Move the package to a src/ layout | Accepted | 2026-08-02 |
| [ADR-011](../decisions/011-retire-the-p4-deferral-label.md) | Retire the P4 deferral label | Superseded by ADR-012 | 2026-08-02 |
| [ADR-012](../decisions/012-correct-adr-011s-deferral-fallback.md) | Correct ADR-011's deferral fallback | Superseded by ADR-013 | 2026-08-02 |
| [ADR-013](../decisions/013-deferral-after-p4-is-retired-upstream.md) | Deferral after P4 is retired upstream | Accepted | 2026-08-03 |
| [ADR-014](../decisions/014-keep-network-as-one-module.md) | Keep network.py as one module | Accepted | 2026-08-04 |
| [ADR-015](../decisions/015-examples-that-cannot-fetch.md) | Examples that cannot fetch | Accepted | 2026-08-04 |
| [ADR-016](../decisions/016-gate-the-comment-layout-convention.md) | Gate the comment-layout convention | Accepted | 2026-08-05 |
| [ADR-017](../decisions/017-decline-under-render-detection-at-tier-1.md) | Decline under-render detection at tier 1 | Accepted | 2026-08-05 |
| [ADR-018](../decisions/018-land-the-arc42-documents.md) | Land the arc42 documents and retire the interim architecture file | Accepted | 2026-08-05 |
| [ADR-019](../decisions/019-what-chapter-11-holds.md) | What chapter 11 holds and its format | Accepted | 2026-08-06 |
| [ADR-020](../decisions/020-where-chapter-diagrams-live.md) | Where chapter diagrams live, and in which format | Accepted | 2026-08-07 |
| [ADR-021](../decisions/021-what-a-quality-goal-is.md) | What a quality goal is, and how the register is keyed | Accepted | 2026-08-07 |
| [ADR-022](../decisions/022-what-in-a-journal-entry-may-be-edited.md) | What in a dev journal entry may be edited | Accepted | 2026-08-07 |
| [ADR-023](../decisions/023-bound-a-destructive-sweep-by-proof-of-ownership.md) | Bound a destructive sweep by proof of ownership | Accepted | 2026-08-07 |
| [ADR-024](../decisions/024-conflicting-transport-flags-resolve-to-the-most-escalated-tier.md) | Conflicting transport flags resolve to the most escalated tier | Accepted | 2026-08-07 |
| [ADR-025](../decisions/025-a-building-block-names-its-module.md) | A building block names the module that implements it | Accepted | 2026-08-07 |

Two records predate this repository and still govern the package. They sit
in the repository it was extracted from, and ADR-001 explains why they were
not copied here:
[ADR-035](https://github.com/Imbra-Ltd/wuseria/blob/main/docs/decisions/035-pagefetch-package-and-brandkit.md)
on the extraction and the standard-library-only contract, and
[ADR-037](https://github.com/Imbra-Ltd/wuseria/blob/main/docs/decisions/037-pagefetch-cache-validity-no-ttl.md)
on deciding stored-content validity by content rather than by age.
