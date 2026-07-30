# Playbook

Operational reference for recurring tasks. First-time setup is in
[ONBOARDING.md](ONBOARDING.md); the rules themselves are in
[CLAUDE.md](../CLAUDE.md).

## 1. Git workflow

### 1.1 Branch and commit

`main` is protected. Every change goes through a pull request.

```bash
git checkout main && git pull
git checkout -b fix/<scope>
```

Branch prefixes are `feat/`, `fix/`, `docs/`, `chore/`. Commits follow
`<type>(<scope>): <summary>`, and PR titles add the issue number:
`fix: reject unknown CLI flags (#14)`.

### 1.2 Open a pull request

```bash
gh pr create --base main --title "fix: <summary> (#N)" --body "..."
```

One concern per PR. The body should state what broke, how it was
reproduced, and what the fix changes — a reviewer should not have to run
the code to understand the failure.

### 1.3 Stacked pull requests

When a change depends on an unmerged branch, base the PR on that branch
rather than `main`. Merge bottom-up, and **do not pass `--delete-branch`
while a stacked PR still points at the branch** — that closes the stacked
PR instead of retargeting it.

If it happens anyway:

```bash
git push origin origin/main:refs/heads/<deleted-branch>   # recreate the ref
gh pr reopen <N>
gh pr edit <N> --base main
git push origin --delete <deleted-branch>
gh pr update-branch <N> --rebase
```

### 1.4 Issues

Every issue carries exactly one type label (`bug`, `task`, `spike`) and one
priority label (`P0`–`P3`), applied at creation.

```bash
gh issue create --title "<imperative sentence-case title>" \
                --label bug --label P1 --body "..."
```

Titles are sentence case with an imperative verb and no type prefix — the
label carries the type.

### 1.5 After merge

```bash
git checkout main && git pull
git branch --merged main | grep -v main | xargs git branch -d
```

## 2. Domain operations

### 2.1 Add a transport tier

Tiers live in `network.py` as `_fetch_<name>` methods. A new tier must:

- import its library inside the method, so the package still installs
  without it
- print `[<name>] Not installed` to stderr and return `None` on
  `ImportError` — a missing optional dependency is never an error
- run its result through `looks_like_real_content` before returning it
- be placed in `_escalate` at the point on the ladder its cost justifies
- be added to the `Transport` enum, the CLI flag set, and the README's tier
  table

### 2.2 Add a detection pattern

Patterns live in `detection.py`. Before adding one, check it against real
content — a bare phrase scanned over 20 KB of de-tagged text will match
ordinary body copy.

- Unambiguous markers go in `BOT_DETECTION_PATTERNS` or
  `ERROR_PAGE_PATTERNS`
- Phrasing that also occurs in real copy goes in
  `AMBIGUOUS_ERROR_PAGE_PATTERNS`, which only counts below the size floor
- Add both a positive case to the parametrized test and a negative case
  proving it does not fire on a real page
- Update the count assertion in `test_detection.py`

An error verdict is terminal in AUTO mode — no escalation, no cache — so a
false positive loses a page silently.

### 2.3 Change cache behavior

The key scheme (`sha256(url)[:16]` plus a `.txt`/`.html` suffix) is fixed;
changing it invalidates every existing cache. The junk definition lives
once in `is_cacheable_junk` and is shared by the read-time scrub and the
`--clean-cache` sweep — keep it there rather than duplicating it at a call
site.

## 3. Quality

Three layers: the editor, `pre-commit`, and CI. CI repeats every hook,
because hooks can be skipped with `--no-verify`.

### 3.1 Linting and formatting (ruff)

```bash
py -m ruff check .            # lint
py -m ruff check . --fix      # apply the fixable ones
py -m ruff format .           # format, including Python inside the README
py -m ruff format --check .   # what CI runs
```

Per-file rule exemptions live in `pyproject.toml` with a comment giving the
reason. Fix the code rather than widening a rule.

### 3.2 Type checking (mypy)

```bash
py -m mypy
```

Scoped to `pagefetch` via `files` in `pyproject.toml`. Browser libraries
are absent in a plain checkout, so `ignore_missing_imports` is on.

### 3.3 Tests and coverage (pytest)

```bash
py -m pytest                          # fast
py -m pytest --cov=pagefetch          # with the floor enforced
py -m pytest -k detection             # one area
```

The suite needs no network and no browser. The coverage floor is a ratchet:
raise it against the measured figure when the testable surface grows, never
lower it to make a change pass (ADR-002). Leave a few points of headroom:
the floor is enforced on every matrix leg, and Linux and Windows cover
different branches of `chrome.py`, so they do not report the same figure.

### 3.4 Secret scanning (gitleaks)

Runs in pre-commit and in CI with full history (`fetch-depth: 0`).

### 3.5 Static analysis (CodeQL)

Runs on every PR, on push to `main`, and weekly so a newly published query
reaches the repo without waiting for a PR. Test fixtures are excluded in
`.github/codeql-config.yml` — they are captured third-party HTML, not
project code.

### 3.6 Manual verification of the browser tiers

Tier 2–4 method bodies need a headed Chrome and cannot run in CI. Before
changing one, verify by hand against a site known to need it — the README's
"Sites tested" table lists which site exercises which tier.

## 4. Maintenance

### 4.1 Dependencies

Dependabot opens grouped PRs weekly for GitHub Actions and for the dev
extra. Actions are pinned to a commit SHA with the version in a trailing
comment; Dependabot reads that comment, so keep the format when editing a
workflow by hand.

Runtime dependencies stay empty. Anything that would add one to
`dependencies` in `pyproject.toml` needs an ADR first.

### 4.2 Architecture decisions

Significant structural decisions go in `docs/decisions/` as
`NNN-<kebab-title>.md`, one concern per record, covering context, decision,
alternatives considered, and consequences. ADRs are immutable once merged —
supersede rather than edit.

### 4.3 360-degree audits

Run before a release, after a major feature, or quarterly. The template is
at `docs/solid-ai-templates/templates/base/workflow/360.md`; because this
project is headless, follow its `[ID: 360-headless]` rule and re-project
Quality into engineering dimensions rather than forcing the four-way split.

Reports go to `docs/audits/YYYY-MM-DD-360.md` and nowhere else. Reproduce
every behavioural finding before writing it up.

### 4.4 Update the templates submodule

```bash
git -C docs/solid-ai-templates fetch origin
git -C docs/solid-ai-templates checkout origin/main
git add docs/solid-ai-templates
```

Commit the moved pointer on its own branch, with the upstream range in the
message.

## 5. Release and deploy

Not published to PyPI. Consumers clone the repository or add it as a
submodule, so `main` is the release surface: it must stay green, and the
README must describe what is actually on it.

Version lives in `pyproject.toml` and follows SemVer. Bump it in its own
commit when the public API changes — the exported names in
`pagefetch/__init__.py`, the CLI flags, or the exit codes.
