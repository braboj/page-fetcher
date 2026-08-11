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
`De-stacking a dependent branch`, `Merging a batch of PRs` and
`Merging a stack`. Read them there. What follows is only what this
repository does differently, plus the commands.

**De-stacking takes one of the template's two routes.** `git.md` leaves
the choice to a SHOULD; this repository always merges `main` in and never
cherry-picks fresh:

```bash
gh pr edit <next> --base main
git fetch origin --prune
git checkout <next-branch>
git merge origin/main            # resolve in favour of the branch
git push
```

The standing choice is about review history: opening a new PR discards it,
and a merge commit the squash deletes is not much of a cost against that.
This was a deviation until `solid-ai-templates#919` landed in v2.43.0,
which is why the template now describes both routes rather than one.

`gh pr update-branch` refuses this case rather than doing it for you: the
branch carries the base PR's original commit while `main` carries its
squash, so the shared file reads as modified on both sides. That refusal is
the expected path into the commands above, not a sign anything is wrong.

Verify the resolution rather than reading the merge output, which counts the
base arriving on the branch and not what the squash will land:

```bash
git diff <branch-tip-before-merge> -- <resolved-file>   # must be empty
git diff origin/main --stat                             # must match the PR
```

Resolving in favour of the branch is only safe while the branch is a strict
superset of the base — true when the base PR is the one that just merged,
false as soon as anything else lands on `main` in between. Check the second
diff before trusting the first.

The same step is needed for PRs that were never stacked — `Merging a batch
of PRs` carries the reasoning. There is no retarget in that case, so one
command does it:

```bash
gh pr update-branch <N>          # merges the base in; --rebase force-pushes
gh pr checks <N> --watch         # the Gate reruns from scratch
gh pr merge <N> --squash --delete-branch
```

Budget for it when planning a session's end. They serialize, because a PR
cannot be brought up to date with a merge that has not happened yet, so
three PRs reported as ready to merge cost three CI cycles here.

The cycle is not only bookkeeping. Where two PRs in the batch touch the
same module, each was measured against a base the other had not landed on,
and the re-run is the first and only test of the combination — `git` still
reports MERGEABLE, which claims the texts combine, not that the result
passes. Read a green tick as naming the base it ran against.

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

There is no deferral label — the chain forbids a fifth priority band, and
this repository had already deleted its own before that landed. There is
no milestone either, so the empty milestone field the chain uses as the
deferral carrier is the state of every issue here and marks none of them.
A deferral goes in an ADR when it is a decision, or in the README or the
arc42 chapter on risks and technical debt when it is a standing
limitation, with named trigger
conditions in the issue body, and it is found by reading rather than
filtering.
[ADR-013](decisions/013-deferral-after-p4-is-retired-upstream.md) has the
reasoning. Titles are sentence case with an imperative verb and no type
prefix — the label carries the type.

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
  `docs/arc42/06_runtime_view.md`
- be named for what it requires of the caller, not for its library. The
  `_fetch_<name>` method may name the library it drives; the enum member,
  the flag, the `tier_used` value and the stderr prefix must not (ADR-006)
- carry its own `# --- tier N: <name> ---` section comment, which is what
  keeps a single-module `network.py` navigable (ADR-014)

A fifth tier is one of ADR-014's named conditions for reopening the
question of splitting `network.py` into a package. Read it before
starting: it also fixes what the submodules would have to be called.

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

Every pattern here answers "did this response fail?". None answers "is this
response complete?", and
[ADR-017](decisions/017-decline-under-render-detection-at-tier-1.md) is why:
each candidate signal for an under-rendered page false-positives on a
complete one, and a false positive costs more than a browser launch. Tier 1
returns a sentinel rather than the body when it signals escalation, so the
HTML is gone before a browser tier is tried — and the browser tiers are
optional extras a default install does not have. Read the ADR before
proposing a completeness signal: it fixes the corpus that would have to
exist first, and the constraint that any such detector must preserve the
tier 1 body.

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

### 2.5 Add a CLI flag

Flags are parsed by hand in `__main__.py` — no argparse. Add the name to
`_VALUE_FLAGS` if it takes a value, `_BARE_FLAGS` if it does not. That one
line is enough for `_unknown_flags` and `_collect_urls`, which both branch
on `_VALUE_FLAGS` to skip the value that follows.

A flag carrying a value gets a `_parse_*` function that returns the parsed
type and raises `ValueError` on bad input. `main` already wraps the
parsers in one `try/except ValueError`, so adding the call there is what
makes a bad value report like every other bad argument instead of
tracebacking. Name the accepted set in the message.

`_flag_value` rejects a flag that arrives with no usable value, in both
of its shapes: trailing the argument list with nothing after it, and
carrying the empty string. It returns `None` only for a flag the user
did not pass, so a parser may test its return directly. Do not re-test
the value for truthiness at the call site — `""` and `None` becoming the
same thing again is the whole defect, and it has now been fixed twice
(#98 at the parser, #107 at three call sites).

No library name reaches a flag (ADR-006). A flag is named for what it
gives the caller.

### 2.6 Add an example

One file per pattern in `examples/`, a section in `examples/README.md`,
and nothing else — the `Examples` CI job globs the directory, so a new
file is covered without touching `ci.yml`.

The example may not construct a `NetworkFetcher` (ADR-015). Reach for
`FakeFetcher`, `FileCache` against a temporary directory, or the pure
predicates over `tests/fixtures/`. The job installs with `pip install -e .`
and no extras, so an import the dev toolchain happens to supply is a
failure there and not here.

Run the file, then paste what it printed into the index. Never type the
output by hand — that is the one rule the whole directory exists to keep:

```bash
py examples/<name>.py
```

Read the output before pasting it. It lands in a Markdown file that
gitleaks scans, so a line pairing a keyword with a high-entropy token —
`key: <16 hex chars>` is the one that caught this repository — fails the
secret scan on a document containing no secret. Rename the label in the
example; do not reach for an allowlist (§3.4).

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

Fix the code rather than widening a rule. Where the code is right and the
rule is still wrong about it, the exemption goes at the **narrowest scope
that covers it**:

- a `# noqa: <code>` on the line, when a rule fires at a few known sites
- a per-file entry in `pyproject.toml`, only when a rule fires across the
  file for one structural reason

The distinction is not tidiness. A per-file entry keeps suppressing a rule
after the code that earned it is gone, and nothing reports that it has
become dead — `RUF100` catches a stale `# noqa`, and has nothing to say
about a stale per-file ignore. Prefer the form the linter can audit.

**The per-file entries.** Three files carry one.

`network.py` — `BLE001` and `S110` fire across the ladder, which catches
broad exceptions on purpose: any failure inside a tier, a missing browser
binary, a CDP disconnect, a driver crash, must fall through to the next
tier rather than abort the fetch, and a failure while closing a browser
must not mask the result already fetched. Narrowing either would couple
the fetcher to each engine's exception hierarchy, which is the coupling
the `PageSource` ABC exists to avoid.

`tests/**` — pytest's assert-based style trips `S101` at every assertion,
and `D` would buy a docstring on every test named after its own assertion.
`PLR2004` stays for a subtler reason: a test that imports the constant it
compares against asserts that a value equals itself, so the literal in the
assertion is the test.

`examples/**` — `S101`: the `FakeFetcher` example is a consumer's test
pattern made executable, and the assertions are what it demonstrates.
Printing PASS/FAIL instead would show a way nobody writes tests.

**The inline ones.** `PLC0415` on the six browser imports — `playwright`,
`nodriver` and `seleniumbase`, twice each — which stay inside the tier
methods so the package installs and runs with none of them present. This
was a per-file entry until it was read: of the thirteen sites it covered,
four re-imported a module the file already imports at the top and three
were `urllib` submodules that belonged there too. The rule's stated reason
covered six of them, which is the failure mode a per-file entry cannot
report about itself.

`PLR0911` on `_fetch_urllib` and `_escalate`, which
return from each tier as it succeeds; collapsing that into one exit would
thread a result variable through every branch. `S607` on the two
`subprocess.run` calls in `chrome.py`, where `powershell` and `tasklist`
resolve through `PATH` because a hardcoded System32 path breaks on
non-default Windows installs, and both calls are already best-effort —
as are the two `except Exception: pass` blocks around them, carrying
`BLE001` and `S110`. In the suite, `PLR0913` and `PLR0917` on the tier-stub
helper, which takes one argument per tier by design, and `S311` on the
seeded generator that builds a deterministic incompressible fixture — the
non-cryptographic randomness being exactly the point.

Docstrings are part of the lint: the `D` rules run with the Google
convention, so a public symbol without one fails `ruff check`. The suite is
exempt — a docstring on a test named after its assertion restates the name,
and the naming convention already carries the intent.

### 3.2 Type checking (mypy)

```bash
py -m mypy
```

Scoped by `files` in `pyproject.toml` — four roots: `src`, `tests`,
`examples` and `tools`. Browser libraries are absent in a plain checkout,
so `ignore_missing_imports` is on. `tools/` is a directory of scripts
rather than an installed package, so `mypy_path` puts it where both mypy
and the suite can import it.

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

**Where the floor came from.** Sized from the measured baseline, never from
a target picked by feel. It went 45 to 63 when the batch path was brought
under test, 63 to 70 when the CLI first came under test, and 70 to 76 when
the remaining argument parsing did, at which point `__main__` reached 99% —
all but its own guard. The measured figure is around 79%, and the gap to
the floor stays as headroom rather than being spent: the legs sit within a
fraction of a point of each other now that `chrome.py` no longer queries
the host, but the floor tracks the lowest of them.

What is left uncovered is the browser-tier method bodies, which need a
headed Chrome and are validated by hand (§3.7). The floor is not a quality
claim about them — it is a ratchet that must not regress.

### 3.4 Secret scanning (gitleaks)

Runs in pre-commit and in CI with full history (`fetch-depth: 0`).

The two do not scan the same thing. The hook reads the working tree; CI
reads every commit in the branch. So a finding fixed in a follow-up commit
still fails CI — the branch has to stop containing it, which means
squashing or rebranching, not another commit on top. #113 was closed and
reopened as #114 for exactly this.

The fix belongs in whatever produced the string, not in an allowlist. A
fingerprint-scoped entry names a commit that disappears at squash-merge
and leaves dead config; a path-scoped one exempts a file permanently.
Neither is worth it for output that only looked like a credential (§2.6).

### 3.5 Static analysis (CodeQL)

Runs on every PR, on push to `main`, and weekly so a newly published query
reaches the repo without waiting for a PR. Test fixtures are excluded in
`.github/codeql-config.yml` — they are captured third-party HTML, not
project code.

### 3.6 Comment layout

```bash
py tools/check_comment_layout.py src tests examples tools
```

Silent on success; one line per violation otherwise, with the file, line
and rule. Enforces the two structural rules from CLAUDE.md §2.3 that no
ruff rule expresses — a comment block jammed against the code above it,
and an aside to the right of code. Comment width is `E501`'s job and is
deliberately not re-implemented here.

It runs in three places: the `comment-layout` pre-commit hook, a step in
the `Lint and format` job, and `test_comment_layout.py`, so a checkout
that never ran `pre-commit install` still fails locally rather than in CI.

Adding a root means editing two places — the hook's `args` and the CI
step. They are listed rather than globbed so a new top-level directory is
a deliberate addition, not silently unchecked.

Before adding a carve-out, check it is not really a conflict with another
tool. Two of the five exist because the rule contradicts something else:
`ruff format` deletes blank lines inside collection literals, and `D202`
forbids one after a docstring. ADR-016 has the full table; a sixth
carve-out needs its reasoning recorded there first.

### 3.7 Manual verification of the browser tiers

Tier 2–4 method bodies need a headed Chrome and cannot run in CI. Before
changing one, verify by hand against a site known to need it — "Sites
Exercised by Hand", under Test Coverage in `docs/arc42/`
`10_quality_requirements.md`, lists which site exercises which tier.

### 3.8 Journal order

```bash
py tools/check_journal_order.py docs/dev-journal.md
```

Same output contract as §3.6, and the same three places: the
`journal-order` pre-commit hook, a step in `Lint and format`, and
`test_journal_order.py`. Two codes — `ORDER` for an entry dated before the
one above it, `UNDATED` for a level-two heading with no date.

`base/core/docs.md` requires session entries oldest first, newest at the
bottom. It also tells each session to copy the prior entry's skeleton
exactly, which is why the wrong order survived twenty sessions here and
why the right one needs a gate rather than care.

An undated heading fails rather than being skipped, so the checker has no
silent branch. A legitimate non-session heading is therefore a carve-out
with its reasoning recorded, the way ADR-016 handles the comment-layout
five — not a case to quietly admit.

This section is numbered after the browser-tier one rather than beside
§3.6 where it belongs by subject. ADR-019 cites "PLAYBOOK 3.7" for the
browser tiers, and a merged record cannot be edited to follow a renumber.

### 3.9 Diagram exports

```bash
py tools/check_diagram_exports.py docs/assets
```

Same output contract as §3.6, and the same three places: the
`diagram-exports` pre-commit hook, a step in `Lint and format`, and
`test_diagram_exports.py`. Four codes — `SCALE` for an export not taken at
`--scale 2`, `EDGE` for an edge with no `<mxGeometry>`, `UNPAIRED` for a
source or an export missing its counterpart, and `UNREADABLE` for a source
whose geometry cannot be recovered.

It reads the PNG's IHDR header rather than the image, so it needs neither
draw.io nor a display and runs anywhere the other two do.

The scale rule exists because reading the render cannot catch what it
gates. Two of seven diagrams shipped at the default scale, both found by
accident during unrelated work — the failure is invisible in the image and
reads in the diffstat as a compression win (#151). ADR-020 already required
reading the export before committing and caught neither, because reading a
render proves the arrows are there and the arrows are there at any scale.

**Why the rule is a band.** The export crops to the drawing's content box
rather than the page box, so `2 * pageWidth` is not the expected width —
chapter 3's business context is a 1440x680 page exporting to 2695x1077.
What the source does yield is the box enclosing every vertex and edge
waypoint, which is close to what draw.io renders without matching it:
labels and shadows push the rendered bounds outward, while a shape's
painted extent can sit just inside its geometry. Closing that gap would
mean reimplementing text metrics.

**Where its edges come from.** Divided by that box, the seven committed
exports run 2.026 to 2.112. The same sources at scale 1 land at half that
— the two committed that way measured 1.009 and 1.026 — so the floor
separates two populations a factor of two apart and can sit anywhere
between them. It is at 1.75 rather than 2.0 because the box is not a
strict lower bound: measured against `2 * (box + 20)` the seven run 0.994
to 1.016, the deployment view coming in 0.56% under. A floor resting on an
inequality that does not quite hold would fail a good export to catch
nothing a looser one misses. The ceiling at 3.0 rejects scale 3 and 4; it
assumes a content box much larger than the border, which adds `40 / box`
to the ratio and matters only below about 100px.

A vertex nested in a group is reported rather than measured. Its geometry
is relative to the group, and a wrong box would fail a good export as
readily as pass a bad one.

### 3.10 Code citations

```bash
py tools/check_code_citations.py src tests examples tools \
   .github pyproject.toml .pre-commit-config.yaml
```

Same output contract as §3.6, and the same three places: the
`code-citations` pre-commit hook, a step in `Lint and format`, and
`test_code_citations.py`. Two codes — `ISSUE` for a `#` followed by
digits, `RECORD` for an `ADR` followed by digits.

The roots are listed in four places — the hook's `args`, the CI step, the
command above and `ROOTS` in the test. A root added to some and not the
others fails the test, which compares the list against what it reaches.

`base/core/quality.md` bans citing an issue, PR or decision record by
number in a code comment or docstring, and asks for exactly this check.
Code outlives the tracker: a reader who follows a stale number lands on a
dead thread instead of on whatever superseded it. State the substance —
name the descriptor, the source or the derivation. A durable source
(author, year, method) is explicitly allowed and matches neither pattern.

Markdown is the opposite and is never scanned. The README, the decision
records, the journal and this file cite numbers because that is their job.

In Python, comments come from `tokenize` and docstrings from `ast`, so a
citation inside an ordinary string literal is left alone — test data
describing a violation is not one. There are no carve-outs; a case needing
one should be recorded before it is added.

Commented configuration is scanned as code, because a workflow, a hook
list and the project file all carry reasoning and a number rots there the
same way. Those are read line by line rather than parsed: a `#` outside a
quote opens a comment. That is enough for these files and would not
survive an escaped quote or a block scalar carrying a lone `#`.

One limit remains. It matches the two shapes above, so a bare "issue 151"
in prose passes — the rule is wider than what a regex can hold, and the
gate is a floor under review rather than a replacement for it.

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

Adding a record also adds a row to `docs/arc42/09_architecture_decisions.md`,
in the same PR. That chapter is the only index, and no other chapter cites a
record — so a record missing from it is a record nothing points at.

### 4.3 360-degree audits

Run before a release, after a major feature, or quarterly. The template is
at `docs/solid-ai-templates/templates/base/workflow/360.md`; because this
project is headless, follow its `[ID: 360-headless]` rule and re-project
Quality into engineering dimensions rather than forcing the four-way split.

Reports go to `docs/audits/YYYY-MM-DD-360.md` and nowhere else. Reproduce
every behavioural finding before writing it up.

### 4.4 Update the templates submodule

```bash
git -C docs/solid-ai-templates fetch --tags origin
git -C docs/solid-ai-templates tag --sort=-v:refname | head -3
git -C docs/solid-ai-templates checkout <latest tag>
git add docs/solid-ai-templates
```

Pin a tag, never `origin/main`. Upstream keeps working past a release, so
`origin/main` is a mid-flight revision carrying rules that are not in any
cut yet — pinning it imports them and dates the commit message against a
range nobody else can name. This instruction disagreed with §4.5 below for
several sessions and never produced a wrong pin, because every bump until
`v2.42.0` ran while the tag happened to be HEAD. The session that bumped
to `v2.42.0` found `origin/main` four commits ahead, and #99 had already
been written against those four.

Commit the moved pointer on its own branch, with the upstream range in the
message.

Once the PR merges, pull `main` and move the working tree onto the pin:

```bash
git checkout main && git pull
git submodule update --init --recursive
```

A fast-forward moves the recorded pointer and leaves the submodule checkout
where it was, so the clone reads at the version the bump just replaced —
`git status` shows the submodule modified and `git submodule status` prefixes
a `+`. §4.5 covers reading at the wrong revision on the way in; this is the
same error on the way out, and it lands at the moment the templates are most
likely to be consulted.

Bump before reconciling anything against the templates, and keep the two in
separate commits. A pointer bump that also edits `CLAUDE.md` hides the
reconciliation inside the submodule's diff.

`docs.md` requires re-reading a divergence record before deciding what a
bumped range means, and requires the reconciliation to state whether the
divergence still holds. The local instance is `base-issues-defer`: three
movements across four bumps, two of them inside one day. It refuted
ADR-011's fallback hours after that ADR merged, and the bump after next
closed ADR-012's divergence outright by forbidding the label this
repository had already dropped.
[ADR-013](decisions/013-deferral-after-p4-is-retired-upstream.md) is the
current reading.

Decide what a changed file governs from the dependency graph, not from the
chain list in `CLAUDE.md`. That list is a convenience copy, and a platform
template pulls in files it does not name — `platform/github.md`
`DEPENDS ON` `workflow/issues.md`, so everything in `issues.md` governs
here even though CLAUDE.md lists neither. Resolve it per file:

```bash
git -C docs/solid-ai-templates show HEAD:templates/<file> | grep "DEPENDS ON"
```

A file reachable from nothing declared does not govern, however applicable
it reads — `agents.md` and `security/devsecops.md` both changed in the
`v2.42.0` range and neither reaches this repository. Scoping from the list
rather than the graph errs in both directions at once: it imports rules
that do not apply and misses ones that do.

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

A stale `*.egg-info` is worse than untidy when it sits in the repository
root: the root is on `sys.path` ahead of `site-packages`, so the leftover
shadows the freshly written `dist-info` and the version stays stale even
after a clean `pip install -e .`. Under `src/` the directory is written to
`src/`, which is not on `sys.path`, so ADR-010 closed that path here — the
fix (`rm -rf ./*.egg-info` before reinstalling) is for a flat layout.

The layout itself has a proof, and it is the only check that catches a
suite still importing from the tree:

```bash
py -m pip uninstall -y pagefetch
py -m pytest --collect-only   # MUST fail: ModuleNotFoundError
py -m pip install -e ".[dev]"
```

A suite that still collects has not adopted the layout, it has only moved
files. Nothing else detects this — lint, types and coverage all pass either
way.

### 4.7 Regenerate an arc42 diagram

Sources and exports both live in `docs/assets/`, named for the chapter that
embeds them. Edit the `.drawio`, re-export, and commit both files — a PNG
regenerated from an uncommitted source is a diagram nobody else can change.

```bash
"/c/Program Files/draw.io/draw.io.exe" --export --format png \
  --scale 2 --border 10 --output docs/assets/<name>.png \
  docs/assets/<name>.drawio
```

Which format to reach for follows `base/core/docs.md`: Mermaid for sequence
diagrams, which is why chapter 6's five scenarios stay inline; draw.io for
the structural ones, where the layout carries meaning a generated graph
will not hold still.

Hand-authoring the XML has one trap that costs an afternoon. An `mxCell`
with `edge="1"` and no `<mxGeometry>` child is dropped from the render
silently — no warning, no error, exit status zero, and the export simply
comes back missing that arrow. Give every edge a geometry element even when
it has no waypoints:

```xml
<mxCell id="e1" edge="1" parent="1" source="a" target="b" style="...">
  <mxGeometry relative="1" as="geometry" />
</mxCell>
```

Read the exported PNG before committing. Labels are placed at the midpoint
of the path, so two edges sharing a channel put their labels on top of each
other, and the XML gives no sign of it.

Reading it does not cover its dimensions, and those are gated rather than
inspected (§3.9). An export taken at the default scale renders every arrow
and every label correctly at half the resolution, so nothing about the
image says it is wrong — and being a smaller file, it reads in the diffstat
as a compression win. Two of the seven were committed this way and both
were found by accident, which is why the check exists:

```bash
py tools/check_diagram_exports.py docs/assets
```

It recovers the scale by dividing the PNG by the box enclosing the
source's vertices and edge waypoints, and accepts a band around the
nominal scale rather than one figure. §3.9 has the reasoning and the
measurements; a scale-1 export misses the floor by a factor of two, so the
tolerance costs nothing against the defect it exists for.

A diagram whose layout is arithmetic rather than judgement — the quality
tree centres each parent on the span of its children across 38 nodes — can
be laid out by a throwaway script. Do not commit that script. The `.drawio`
is the editable source, and a generator that rewrites it takes that role
away from anyone who opens the file in draw.io. ADR-020 records the
reasoning.

## 5. Releases

Not published to PyPI. Consumers clone the repository or add it as a
submodule, so `main` is the release surface: it must stay green, and the
README must describe what is actually on it.

Version lives in `pyproject.toml` and follows SemVer. Bump it in its own
commit when the public API changes — the exported names in
`src/pagefetch/__init__.py`, the CLI flags, or the exit codes.
