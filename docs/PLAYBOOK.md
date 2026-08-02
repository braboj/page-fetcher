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

The rules are in `base/core/git.md` — `Squash-merge safety`,
`De-stacking a dependent branch` and `Merging a stack`. Read them there.
What follows is only what this repository does differently, plus the
commands.

**De-stacking deviates from the template.** Upstream requires branching
fresh off the updated `main` and cherry-picking the dependent branch's own
commits into a new PR. This repository merges `main` in instead:

```bash
gh pr edit <next> --base main
git fetch origin --prune
git checkout <next-branch>
git merge origin/main            # resolve in favour of the branch
git push
```

Both routes avoid the force-push, which is the rule that matters, and
under squash merge both leave `main` byte-identical. The difference is
that opening a new PR discards the review history on the old one, and a
merge commit the squash deletes is not much of a cost against that.
Proposed upstream as `solid-ai-templates#919`; if that lands, this stops
being a deviation.

The same step is needed for PRs that were never stacked. Branch protection
requires the head to be up to date, so the second of any two PRs merged
back to back needs `main` merged in first — even when the two touch
disjoint files.

If the base branch gets deleted while a stacked PR points at it:

```bash
git push origin origin/main:refs/heads/<deleted-branch>   # recreate the ref
gh pr reopen <N>
gh pr edit <N> --base main
git push origin --delete <deleted-branch>
gh pr update-branch <N> --rebase
```

`gh pr update-branch` rewrites the head on GitHub and leaves your clone
on the commit it replaced. Resync before the PR merges, or the cleanup
check in §1.5 has nothing valid to compare against:

```bash
git fetch origin <branch>
git reset --hard origin/<branch>
```

### 1.4 Issues

Every issue carries exactly one type label (`bug`, `task`, `spike`) and one
severity label (`P0`–`P3`), applied at creation.

```bash
gh issue create --title "<imperative sentence-case title>" \
                --label bug --label P1 --body "..."
```

`P4` is a deferral marker rather than a severity, so it joins a severity
instead of replacing one — a deferred issue carries both, as #59 and #9
do. Titles are sentence case with an imperative verb and no type prefix —
the label carries the type.

### 1.5 After merge

`platform/github.md` `[ID: platform-github-branch-cleanup]` carries the
rule and the reasoning: verify against the PR record, never against
`git branch --merged`, and inspect a `headRefOid` mismatch by content
before deleting. The remote head branch is deleted automatically here, so
only the local one needs cleaning up.

```bash
git checkout main && git pull
gh pr view <N> --json state,headRefOid --jq '"\(.state) \(.headRefOid)"'
git rev-parse <branch>
git branch -D <branch>   # only when state is MERGED and the SHAs match
```

The mismatch case is routine in this repository rather than exceptional,
because branch protection requires the head to be up to date: any PR that
needed `main` merged in, or that `gh pr update-branch` rewrote, leaves the
clone behind the head that was squashed. Resyncing before the PR merges
(§1.3) means the question never arises.

Then close the tracker ticket by hand, until the automation is configured.
BRA-595, BRA-596 and BRA-600 each sat in `In Progress` with their merged PR
already linked, and were moved afterwards in a separate pass.

This is a gap in this workspace's setup, not a limit of the integration.
`platform/linear.md` already requires configuring the automation to move an
issue to a `started` state on PR open and a `completed` state on merge, and
that has not been done. Its issue-sync rule also only closes a tracker
issue when the code host closes *its counterpart*, so a ticket with no
GitHub issue behind it has nothing to close it — which is what these three
were. Configure both and this step goes away.

The GitHub issue is the half that closes itself, and only when the PR body
carries `Closes #N`. Write the keyword or expect to close that by hand too.

ADR-007 also keeps the tracker replaceable, which is why the step is
recorded as the action rather than as a path through one vendor's UI: move
the ticket to its terminal state, in whichever tracker is in use.

## 2. Domain operations

### 2.1 Add a transport tier

Tiers live in `network.py` as `_fetch_<name>` methods. A new tier must:

- import its library inside the method, so the package still installs
  without it
- print `[<name>] Not installed` to stderr and return `None` on
  `ImportError` — a missing optional dependency is never an error
- run its result through `looks_like_real_content` before returning it
- be placed in `_escalate` at the point on the ladder its cost justifies
- be added to the `Transport` enum, the CLI flag set, and the tier table in
  `docs/ARCHITECTURE.md`
- be named for what it requires of the caller, not for its library. The
  `_fetch_<name>` method may name the library it drives; the enum member,
  the flag, the `tier_used` value and the stderr prefix must not (ADR-006)

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

### 2.4 Change what gets cleaned up after a browser tier

`ChromeReaper` kills OS processes, so read
[ADR-005](decisions/005-chrome-ownership-by-ancestry.md) before touching
it. Two rules it must keep: only Chrome descended from this interpreter
may be killed, and when ownership cannot be established nothing is
tracked. Widening either has already cost a real browser process once.

Tests must not reach the host. A `conftest` fixture stubs both process
queries for every test but `test_chrome_reaper.py`; a new test file that
exercises the reaper has to stub them itself.

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

The pip strategy is `increase-if-necessary`, so a floor moves only when a
new version is genuinely required. Every version in `pyproject.toml` is a
lower bound and raising one narrows what a consumer may install — most of
all on the `browsers` extra. The default `increase` strategy lifts every
floor to the newest release regardless, which is not what a library wants.

Bumping floors does not widen what gets tested: CI installs `-e ".[dev]"`
and resolves to the newest release satisfying each floor, so the toolchain
already runs at current versions whatever the floors say.

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

Bump before reconciling anything against the templates, and keep the two in
separate commits. A pointer bump that also edits `CLAUDE.md` hides the
reconciliation inside the submodule's diff.

### 4.5 Read the templates at the right revision

Two questions, two revisions. Getting them the wrong way round has cost a
mistake in each direction.

**"Has this already been raised?" — read upstream HEAD.**

```bash
gh issue list --repo braboj/solid-ai-templates --state all --search "<terms>"
```

The pin can be dozens of commits behind the answer. Three duplicates were
filed in one session against issues that were not only already open but
already fixed upstream. Search closed issues too — a rule that was
proposed and rejected is worth knowing about before proposing it again,
and a closed issue is often the one that introduced the text being
questioned.

**"What does our chain require?" — read the pin.**

```bash
git -C docs/solid-ai-templates show HEAD:templates/<file>
```

Never `origin/main`, and never the working tree after a bare `fetch`.
A rule quoted from HEAD that has not been bumped into the pin does not
apply here, and citing it makes a local document look conformant when it
is not. #76 quotes a sentence that reached upstream eight commits after
the revision this repository pins.

The distinction only disappears when the pin equals HEAD, which is
briefly and rarely.

### 4.6 Move a path the tooling knows about

`pyproject.toml` is not the only file pinning a path. The move to `src/`
(ADR-010) touched three excludes outside it, and the ticket that planned
the move listed none of them:

| File | What it pins |
| -- | -- |
| `.gitattributes` | the fixture directory, held binary |
| `.github/codeql-config.yml` | the same directory, in `paths-ignore` |
| `.pre-commit-config.yaml` | the same directory, in three hooks |

Enumerate them from the tree, not from the plan:

```bash
grep -rn "<old/path>" --include="*.toml" --include="*.yml" \
     --include="*.yaml" --include="*.md" --include="*.py" . \
  | grep -v docs/solid-ai-templates
```

`.gitattributes` is the one that fails quietly: it holds the captured
HTML fixtures byte-for-byte, and line-ending normalization would rewrite
them into a test failure that reads as a detection bug.

Then compare counts before and after. `python-lib.md` requires this
because a colliding exclude drops a whole directory from a scan while CI
stays green:

```bash
py -m ruff format --check .   # file count
py -m mypy                    # source count
py -m pytest --cov=pagefetch  # tests, statements, coverage
```

Identical counts are the pass condition — a drop means a pattern started
matching, not that code changed.

Finally, re-run the commands the documents claim. A path move can break a
documented workflow without breaking the gate: the move to `src/` left the
README telling readers to clone and immediately run `py -m pagefetch`,
which had only ever worked because the package sat at the root.

Building the wheel to check it leaves `build/` and `*.egg-info` in the
tree. Both are gitignored, so `git status` stays clean and nothing flags
them — build into a scratch directory, or delete them in the same step.

## 5. Releases

Not published to PyPI. Consumers clone the repository or add it as a
submodule, so `main` is the release surface: it must stay green, and the
README must describe what is actually on it.

Version lives in `pyproject.toml` and follows SemVer. Bump it in its own
commit when the public API changes — the exported names in
`src/pagefetch/__init__.py`, the CLI flags, or the exit codes.
