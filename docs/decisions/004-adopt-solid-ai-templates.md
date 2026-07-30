# ADR-004: Vendor solid-ai-templates as the source of project conventions

**Status:** Accepted
**Date:** 2026-07-30

## Context

Conventions in this repository were carried in people's heads and in the
shape of existing files. There was no `CLAUDE.md`, no onboarding or
operational guide, and no record of sessions — four of the six documents
`base/core/docs.md` marks MUST were simply absent. Every commit here is
agent-assisted, so an agent began each session with the code and the git
log and nothing else.

`solid-ai-templates` already existed as a shared template system and was
already mounted the same way in two sibling repositories (`corrosim_repo`,
`randomgen`). It supplies what was missing: a documented structure for
agent context files, a review priority order, a structure-audit checklist,
and a 360-degree assessment method.

The alternative was writing those conventions by hand here. That is how
the same `CLAUDE.md` gets written three times a quarter, each copy
slightly different and none of them right.

## Decision

**1. Vendor the templates as a git submodule at `docs/solid-ai-templates`.**

Path and URL match the sibling repositories. Nothing in the package
imports it, so a checkout without the submodule still builds, installs and
tests.

**2. Generate `CLAUDE.md` against the `stack-python-lib` chain, hybrid model.**

`base/core/agents.md` recommends hybrid when a project vendors the
templates, which this one now does. Sections 3 and 5 reference the
resolved chain; git conventions, structure placement rules, language and
safety rules, and the session protocol are inlined, because those cause
the most damage when missed.

Section 6.3 hard-delegates the end-of-session checklist to
`base/workflow/scope.md` rather than restating it. The template forbids
paraphrasing it — a condensed checklist silently drops steps, which is
exactly what the first draft here did, losing five including the one whose
job is to catch that.

**3. Store 360-degree audits at `docs/audits/YYYY-MM-DD-360.md` only.**

Per the submodule's ADR-018. This creates `docs/audits/` as a new
directory with one dated report per run and no rollup index.

**4. Apply the headless rule when auditing.**

`base/workflow/360.md` `[ID: 360-headless]` — this package has no
user-facing surface, so the Discovery perspective does not apply, Value
reduces to the README contract, and Quality is re-projected into
engineering dimensions rather than forcing the four-way split.

**5. Adopt the issue label scheme.**

Exactly one type label (`bug`, `task`, `spike`) and one priority label
(`P0`–`P3`) at creation. The labels were created to match the template's
names and colours; `spike` already existed with the template's colour, so
the scheme was half-adopted before this.

## Alternatives considered

- **Write the conventions directly in this repository.** Rejected: it
  duplicates work already done, and drifts from the sibling repositories
  that use the same system.
- **Reference the templates from GitHub without vendoring.** Rejected:
  an agent cannot be relied on to fetch a URL mid-session, and the
  conventions would change under the repository without a commit.
- **Copy the template files in rather than submodule them.** Rejected:
  updates become a manual diff, and the provenance of each rule is lost.
- **Inline model for `CLAUDE.md`.** Rejected once the templates were
  vendored — `agents.md` names that condition as the one where hybrid
  wins, and inlining the full quality framework makes the file long enough
  that its own rules compete for attention.

## Consequences

- `CLAUDE.md`, `docs/ONBOARDING.md`, `docs/PLAYBOOK.md` and
  `docs/dev-journal.md` exist and are maintained; the README remains the
  single source of truth for project structure and is referenced rather
  than duplicated.
- A checkout needs `--recurse-submodules`, or `git submodule update
  --init`, to see the templates. The package does not need them.
- Tooling that walks the filesystem sees the submodule. `ruff` did, and
  reported 85 errors that no commit here can fix, so `pyproject.toml`
  excludes `docs/solid-ai-templates`. Anything added later that walks the
  tree needs the same treatment; `mypy` was already scoped by `files`.
- The submodule pin is a commit, not a branch. Upstream changes reach this
  repository only when the pointer is deliberately bumped.
