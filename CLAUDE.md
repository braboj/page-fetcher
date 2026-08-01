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
- Anything Windows-specific or side-effectful on the host goes in
  `chrome.py` and nowhere else
- Never widen what `ChromeReaper` is willing to kill without re-reading
  ADR-005 — it may only kill Chrome descended from this interpreter, and
  must kill nothing when ownership cannot be established
- `source.py` MUST NOT import from any other package module — it is the
  contract every other module depends on
- New tests go in `pagefetch/tests/`, one file per concern, named
  `test_<concern>.py`
- The package layout is flat, not `src/` — deviation from
  `python-lib.md`, kept because the package predates this repository
  and the key scheme in `cache.py` is path-independent

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

- `main` is protected — never commit directly
- Branch naming: `feat/<scope>`, `fix/<scope>`, `docs/<scope>`,
  `chore/<scope>`
- Commits: `<type>(<scope>): <summary>` — feat, fix, chore, docs,
  refactor
- PR titles: same format with the issue number(s) at the end
- Issue titles: sentence case, imperative verb, no type prefix
- Every issue gets exactly one type label (`bug`, `task`, `spike`) and
  one severity label (`P0`–`P3`), applied at creation. `P4` is a
  deferral marker, not a severity — it accompanies a severity rather
  than replacing one (ADR-021 upstream)
- One concern per PR
- Never delete a base branch while a stacked PR points at it — that
  closes the stacked PR instead of retargeting it

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

### 2.5 Detection patterns

- Never add a pattern that matches ordinary body copy — both lists are
  scanned over 20 KB of de-tagged text, so a bare phrase like "rate
  limit" or "no longer available" will hit real pages
- Put ambiguous phrasing in `AMBIGUOUS_ERROR_PAGE_PATTERNS`, which counts
  only below the size floor. An error verdict is terminal in AUTO mode —
  no escalation, no cache — so a false positive loses a page silently
- Every new pattern needs a positive case in the parametrized test AND a
  negative case proving it does not fire on real content
- Update the count assertion in `test_detection.py`

### 2.6 Cache

- The key scheme (`sha256(url)[:16]` plus `.txt`/`.html`) is fixed —
  changing it silently invalidates every existing cache
- Keep the junk definition in `is_cacheable_junk` alone; never duplicate
  it at a call site

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

- Reproduce a claimed defect before reporting it — a finding asserted
  from reading alone is a hypothesis
- Treat a silent terminal verdict as a correctness defect, not a
  usability one: returning `ok=False` for a page that exists is the
  worst failure this package has

### 5.2 Structure audit

Verify the MUSTs from `templates/base/core/docs.md`,
`templates/base/core/readme.md`, `templates/base/core/git.md` and
`templates/stack/python-lib.md`. Run after a new layer, a migration, or
before a release milestone.

Confirm every documented command still produces the output the document
claims — the README gate figures and the ONBOARDING verify steps are
measured values, not prose.

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
