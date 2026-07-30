# pagefetch

Auto-escalating web page fetcher: plain HTTP first, browsers only when the
response is a bot wall, an error, or implausibly short.

## 1. Project

### 1.1 Overview

- **Name**: pagefetch
- **Owner**: Branimir Georgiev
- **Repo**: github.com/braboj/page-fetcher
- **Stack**: Python 3.10+, standard library only for tier 1
- **Distribution**: not published to PyPI; consumed as a clone or submodule
- **Templates**: `docs/solid-ai-templates` (submodule) — chain
  `stack-python-lib`

### 1.2 Project structure

See the README's "Project structure" section — it is the single source of
truth. Agent-specific placement rules:

- New transport tiers go in `network.py`; new pure predicates in
  `detection.py`. A predicate that needs I/O does not belong in
  `detection.py`.
- Anything Windows-specific or side-effectful on the host goes in
  `chrome.py` and nowhere else.
- `source.py` MUST NOT import from any other package module — it is the
  contract every other module depends on.
- New tests go in `pagefetch/tests/`, one file per concern, named
  `test_<concern>.py`.

### 1.3 Commands

```bash
py -m pip install -e ".[dev]"   # install with the dev toolchain
pre-commit install              # wire the local gate

py -m ruff check .              # lint
py -m ruff format --check .     # formatting, including Python in the README
py -m mypy                      # type check
py -m pytest                    # tests
py -m pytest --cov=pagefetch    # tests with the coverage floor enforced
```

## 2. Code conventions

### 2.1 Git

- Branch: `main` (protected) — never commit directly
- Branch naming: `feat/<scope>`, `fix/<scope>`, `docs/<scope>`,
  `chore/<scope>`
- Commits: `<type>(<scope>): <summary>` — feat, fix, chore, docs, refactor
- PR titles: same format with the issue number(s) at the end
- Issue titles: sentence case, imperative verb, no type prefix — labels
  carry the type
- Every issue gets exactly one type label (`bug`, `task`, `spike`) and one
  priority label (`P0`–`P3`), applied at creation
- One concern per PR
- Never delete a base branch while a stacked PR still points at it — that
  closes the stacked PR instead of retargeting it

### 2.2 Python

- PEP 8 via ruff; fix the code rather than widening a ruff rule
- Every public symbol has a docstring
- Public functions and class members are annotated
- Line length 88, enforced on code and on Python inside the README

### 2.3 Comments

- A block comment sits directly above the item it documents — never
  trailing to the right of code (`# noqa` / `# nosec` excepted), never
  separated from it by a blank line
- Separate each comment-plus-item group from the next with one blank line
- Wrap comment prose to 88 characters, including in `pyproject.toml`, YAML
  and CI workflows
- Comments explain why, not what. A comment that restates the code is
  noise; a comment recording a failure that motivated the code is the
  point

### 2.4 Optional dependencies

- Tier 1 is standard library only. This is a contract, not a preference —
  `dependencies = []` in `pyproject.toml` must stay empty
- Browser libraries are imported inside the tier method that uses them, so
  the package installs and runs with none of them present
- A missing optional dependency skips its tier with a stderr message; it is
  never an error
- `nodriver` is AGPL-3.0 and stays optional and un-vendored — see the
  README's Dependencies section before changing how it is imported

### 2.5 Detection patterns

- A pattern added to `BOT_DETECTION_PATTERNS` or `ERROR_PAGE_PATTERNS` must
  not match ordinary body copy. Both lists are scanned over 20 KB of
  de-tagged text, so a bare phrase like "rate limit" or "no longer
  available" will hit real pages
- An error verdict is terminal in AUTO mode — no escalation, no cache — so
  a false positive there loses a page silently. Ambiguous phrasing belongs
  in `AMBIGUOUS_ERROR_PAGE_PATTERNS`, which only counts below the size floor
- Every new pattern needs both a positive case in the parametrized detection
  test and a negative case proving it does not fire on real content

### 2.6 Cache

- The key scheme (`sha256(url)[:16]` plus a `.txt`/`.html` suffix) is fixed
  — changing it silently invalidates every existing cache
- Junk is defined once in `is_cacheable_junk` and shared by the read-time
  scrub and the `--clean-cache` sweep; do not duplicate the definition at a
  call site

## 3. Quality

### 3.1 Testing

- The suite runs with no network and no browser. Escalation is tested by
  stubbing the four tier methods
- Browser-tier method bodies need a headed Chrome and are validated by
  hand — they are the bulk of what is uncovered
- Coverage has a ratchet floor in `pyproject.toml` that must not regress.
  Raise it against the measured figure when the testable surface grows;
  never lower it to make a change pass. See ADR-002
- The floor is measured on Windows and enforced on Linux runners — leave a
  few points of headroom

### 3.2 The gate

Three layers. Layer 1 is the editor, layer 2 is `pre-commit`, layer 3 is
CI, which repeats every hook because hooks can be skipped with
`--no-verify`. CI additionally runs the Python matrix, coverage, CodeQL and
gitleaks.

`Gate` is the single required status check — a job added to `ci.yml` is
covered by it automatically.

## 4. Identity

Not applicable — no design system or brand voice.

## 5. Review process

### 5.1 Code review

Priority order, highest first:

1. **Security exposure** — anything exploitable, any credential or license
   problem
2. **Functional correctness** — paths that produce wrong results, unhandled
   failures, silent terminal verdicts
3. **Clarity** — obscure names, deep nesting, boolean flag parameters
4. **Convention compliance** — deviation from the patterns above

Reproduce a claimed defect before reporting it. A finding asserted from
reading alone is a hypothesis.

### 5.2 Structure audit

Run before a release milestone or after adding a major layer. Verify the
README's eight required sections, the standard documents listed in
`docs/solid-ai-templates/templates/base/core/docs.md`, and that every
documented command still produces what the document claims.

360-degree audits are stored at `docs/audits/YYYY-MM-DD-360.md` and nowhere
else, per ADR-018 of the templates submodule.

## 6. Session protocol

### 6.1 Start of session

1. Read this file
2. Run `git branch --no-merged main` and flag unmerged branches — they may
   hold lost work
3. Confirm the scope before making changes

### 6.2 During the session

- Run `py -m pytest` after any change to the package
- Run the full gate before opening a PR
- When a path-based shell query returns an unexpected empty result, verify
  the working directory first — the shell's cwd persists across commands
- Do not drift from the agreed scope without checking

### 6.3 End of session

When the user signals the end of a session, execute each item in order and
report the result of each before moving on. Do not batch or summarize.

1. **Commits and push** — everything committed and pushed via PR
2. **Close issues** — verify auto-close worked
3. **Dev journal** — add an entry to `docs/dev-journal.md`
4. **ADRs** — record architectural decisions in `docs/decisions/`
5. **Gate** — run lint, format, types and tests; confirm green
6. **CLAUDE.md** — add any new rule the agent must apply on every turn.
   Rules only, one line each; if it needs a paragraph, write an ADR and
   leave a pointer
7. **README.md** — reflect new commands, flags, dependencies, behavior
8. **docs/PLAYBOOK.md** — reflect new workflows
9. **docs/ONBOARDING.md** — reflect new prerequisites or setup steps
10. **Branch cleanup** — delete branches merged via PR
11. **Flag gaps** — say what could not be completed
