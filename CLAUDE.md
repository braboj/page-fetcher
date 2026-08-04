# pagefetch

Auto-escalating web page fetcher: plain HTTP first, browsers only when
the response is a bot wall, an error, or implausibly short.

Quality conventions defined in `docs/solid-ai-templates/` (submodule).
Key references — the resolved `stack-python-lib` chain:

- `templates/base/core/quality.md`
- `templates/base/core/git.md`
- `templates/base/core/docs.md`
- `templates/base/core/readme.md`
- `templates/base/core/testing.md`
- `templates/base/core/review.md`
- `templates/base/core/config.md`
- `templates/base/workflow/quality-gates.md`
- `templates/stack/python-lib.md`

Platform templates are orthogonal to the stack chain and are declared
here rather than resolved through it:

- `templates/platform/github.md` — CI, SAST, secret detection,
  dependency management, and the `Gate` status check
- A tracker platform template is declared alongside it and governs the
  tracker only. Where a rule appears in both, GitHub governs the
  repository. ADR-007 names the tracker currently in use

Also applied, outside the chain: `templates/base/workflow/scope.md`
(session protocol) and `templates/base/workflow/360.md` (audits).

Project-specific overrides and additions follow below.

## 1. Project

### 1.1 Overview

- **Model**: hybrid
- **Owner**: Branimir Georgiev
- **Repo**: github.com/braboj/page-fetcher
- **Stack**: Python 3.10+, standard library only for tier 1
- **Package manager**: pip; build backend setuptools
- **Linter / formatter**: ruff; **type checker**: mypy;
  **tests**: pytest
- **Distribution**: not published — consumed as a clone or submodule

### 1.2 Project structure

See the README's "Project structure" section — it is the single source
of truth. Agent-specific placement rules:

- New transport tiers go in `network.py`; new pure predicates in
  `detection.py`. A predicate needing I/O does not belong in
  `detection.py`
- `network.py` stays one module and keeps its `# --- section ---`
  comments; re-read ADR-014 before splitting it or adding a fifth tier
- Anything Windows-specific or side-effectful on the host goes in
  `chrome.py` and nowhere else
- Never widen what `ChromeReaper` is willing to kill without re-reading
  ADR-005 — it may only kill Chrome descended from this interpreter, and
  must kill nothing when ownership cannot be established
- `source.py` MUST NOT import from any other package module — it is the
  contract every other module depends on
- New tests go in `tests/`, one file per concern, named
  `test_<concern>.py`
- New examples go in `examples/`, one file per pattern, indexed in
  `examples/README.md` with the exact command and its real output. An
  example MUST NOT construct a `NetworkFetcher` (ADR-015)
- Technical explanation goes in `docs/ARCHITECTURE.md`, not the README —
  the README covers what the package does and how to run it. Decisions go
  in `docs/decisions/` (ADR-009)
- The package is `src/pagefetch/` and the suite is `tests/`, per
  `python-lib.md` (ADR-010). A checkout with nothing installed cannot
  import the package — that is the layout working, not a broken clone.
  Run the editable install in §1.3 first

### 1.3 Commands

```bash
py -m pip install -e ".[dev]"   # install with the dev toolchain
pre-commit install              # wire the local gate

py -m ruff check .              # lint
py -m ruff format --check .     # formatting, incl. Python in the README
py -m mypy                      # type check
py -m pytest                    # tests
py -m pytest --cov=pagefetch    # tests with the coverage floor enforced
```

## 2. Code conventions

### 2.1 Git

GitHub as the system of record, and where a tracker identifier may and
may not appear, were an override here until upstream adopted them. They
now come from `base-issues-record` in
`templates/base/workflow/issues.md`, reached through
`templates/platform/github.md` — do not restate the rule or its
reasoning. ADR-007 remains the local record of the decision. What is
project-specific:

- `main` is protected — never commit directly
- Branch naming: `<type>/<TICKET>-<scope>` — e.g.
  `feat/BRA-42-cache-key`. Types: feat, fix, docs, chore. The ticket goes
  in upper case, as the tracker displays it. Omit it when there is no
  ticket
- Commits: `<type>(<scope>): <summary>` — feat, fix, chore, docs,
  refactor
- PR titles: same format with the GitHub issue number(s) at the end,
  never a tracker identifier
- Issue titles: sentence case, imperative verb, no type prefix
- Every issue gets exactly one type label (`bug`, `task`, `spike`) and
  one severity label (`P0`–`P3`), applied at creation. There is no
  deferral label and no milestone — a deferral is recorded where its
  reasoning is, and the chain's empty-milestone carrier is inert in a
  repository that has never created one (ADR-013, superseding ADR-012)
- One concern per PR
- De-stack by merging `main` in, never by cherry-picking fresh. `git.md`
  leaves the two routes to a SHOULD; this repository takes the one that
  keeps the PR and its review history every time, and squash merge
  discards the extra merge commit. PLAYBOOK §1.3 has the commands

### 2.2 Python

- Line length 88, enforced on code and on Python inside the README
- Every public symbol has a docstring
- Public functions and class members are annotated
- Fix the code rather than widening a ruff rule; per-file exemptions
  live in `pyproject.toml` with the reason

### 2.3 Comments

- A block comment sits directly above the item it documents — never
  trailing to the right of code (`# noqa` / `# nosec` excepted), never
  separated from it by a blank line
- Separate each comment-plus-item group from the next with one blank
  line
- Wrap comment prose to 88 characters, including in `pyproject.toml`,
  YAML and CI workflows
- Comments explain why, not what — a comment recording the failure that
  motivated the code is the point

### 2.4 Optional dependencies

- Tier 1 is standard library only — `dependencies` in `pyproject.toml`
  MUST stay empty; adding one needs an ADR first
- Import browser libraries inside the tier method that uses them, so the
  package installs and runs with none of them present
- A missing optional dependency skips its tier with a stderr message —
  never an error
- `nodriver` is AGPL-3.0 and stays optional and un-vendored
- `quality.md`'s rule on naming a pluggable tier for its requirement was
  an override here until upstream adopted it — do not restate it. What it
  governs in this repository: `Transport` members, the transport flags,
  `tier_used` values and the stderr prefixes (ADR-006)

### 2.5 Detection patterns

- Never add a pattern that matches ordinary body copy — both lists are
  scanned over 20 KB of de-tagged text, so a bare phrase like "rate
  limit" or "no longer available" will hit real pages
- Put ambiguous phrasing in `AMBIGUOUS_ERROR_PAGE_PATTERNS`, which counts
  only below the size floor. An error verdict is terminal in AUTO mode —
  no escalation, no cache — so a false positive loses a page silently
- Every new pattern needs a positive case in the parametrized test AND a
  negative case proving it does not fire on real content
- Update all three count assertions in `test_detection.py` —
  `BOT_DETECTION_PATTERNS`, `ERROR_PAGE_PATTERNS` and
  `AMBIGUOUS_ERROR_PAGE_PATTERNS`

### 2.6 Cache

- The key scheme (`sha256(url)[:16]` plus `.txt`/`.html`) is fixed —
  changing it silently invalidates every existing cache
- Keep the junk definition in `is_cacheable_junk` alone; never duplicate
  it at a call site

### 2.7 README

The title block order, the `## Features` heading, the ban on citing a
decision record and the ban on a figure that moves (coverage, byte
counts) were overrides here until upstream adopted all four. They now
come from `templates/base/core/readme.md` — do not restate them.

## 3. Quality

Follow `templates/base/core/testing.md` and
`templates/base/workflow/quality-gates.md`. Project-specific rules only:

- The suite runs with no network and no browser — escalation is tested
  by stubbing the four tier methods
- No test may enumerate or signal host processes. A `conftest` fixture
  stubs both reaper queries; it exempts `test_chrome_reaper.py`, so a new
  test file that exercises the reaper has to stub them itself
- Browser-tier method bodies need a headed Chrome and are validated by
  hand; they are the bulk of what is uncovered
- The coverage floor in `pyproject.toml` is a ratchet — raise it against
  the measured figure, never lower it to make a change pass (ADR-002)
- Leave the floor a few points under the measured figure: it is enforced
  on every matrix leg, and Linux and Windows cover different branches of
  `chrome.py`
- `Gate` is the single required status check — a job added to `ci.yml` is
  covered by it automatically

## 4. Identity

Not applicable — no design system or brand voice.

## 5. Review process

### 5.1 Code review

Follow `templates/base/core/review.md` priority order, applying
`templates/base/core/quality.md` as the standard. Project-specific
additions:

- Treat a silent terminal verdict as a correctness defect, not a
  usability one: returning `ok=False` for a page that exists is the
  worst failure this package has

### 5.2 Structure audit

Verify the MUSTs from `templates/base/core/docs.md`,
`templates/base/core/readme.md`, `templates/base/core/git.md` and
`templates/stack/python-lib.md`. Run after a new layer, a migration, or
before a release milestone.

Confirm every documented command still produces the output the document
claims — the ONBOARDING verify steps are measured values, not prose. The
README carries no such figure and MUST NOT gain one.

Run the label conformance check from `templates/platform/github.md`. It
is the required pairing for the label-at-creation rule in §2.1, and an
unlabeled issue is invisible without it. Output MUST be `[]`. The
project's type taxonomy is `bug`, `task`, `spike` — the query's `epic`
and `incident` alternatives are inert here.

360-degree audits follow `templates/base/workflow/360.md`. This project
is headless, so apply its `[ID: 360-headless]` rule and re-project
Quality into engineering dimensions rather than forcing the four-way
split. Reports go to `docs/audits/YYYY-MM-DD-360.md` and nowhere else.

## 6. Session protocol

Follow `docs/solid-ai-templates/templates/base/workflow/scope.md` for
the scope guard and the end-of-session audit.

### 6.1 Start of session

1. Read this file
2. Run `git branch --no-merged main` and flag unmerged branches — they
   may hold lost work
3. Confirm the scope before making changes

### 6.2 During the session

- Run `py -m pytest` after any change to the package
- Run the full gate before opening a PR
- When a path-based shell query returns an unexpected empty result,
  verify the working directory first — the shell's cwd persists across
  commands
- Do not drift from the agreed scope without checking

### 6.3 End of session

Read `docs/solid-ai-templates/templates/base/workflow/scope.md` (End of
session audit), print the full checklist, and execute each item
sequentially. Do not summarize or skip.
