# Dev journal

One entry per working session, newest first. Records what changed and why
the decision went the way it did — not a changelog of every commit, which
git already holds.

---

## 2026-08-02 (fifth session) — A rule nobody had switched on

**Tool**: Claude Code (Opus 5)

Bumped the templates submodule to v2.41.0 and reconciled. Nine commits,
three files in the resolved chain. The interesting find was not in the
diff: a rule the chain had carried since the toolchain was set up had
never been enabled, and it took a *new* rule to make that visible.

**Changes**

- Bumped the submodule `244d3ff` → v2.41.0 (#90, #93).
- Enabled the Ruff `D` rules with the Google convention and exempted
  `tests/**`. Wrote seventeen missing docstrings and reflowed sixteen
  that ran their summary into the description.
- CLAUDE.md §2.4 stopped restating the tier-naming rule, which
  `quality.md` now carries upstream.
- Added the `src/` layout proof to PLAYBOOK §4.6 and recorded why the
  stale-egg-info failure mode cannot happen here.
- Spiked #92: `network.py` at 897 lines against the new module-split
  rule.

**PRs merged**: #93

**Issues created**: #92. **Closed**: #90

`python-lib.md`'s tooling table has listed Ruff `D` rules as the
docstring gate from the beginning, and CLAUDE.md §2.2 has claimed every
public symbol has a docstring for just as long. Both were true as
statements and false as facts: `D` was never in `select`, so nothing
checked. Turning it on found 260 violations — 211 of them in the suite,
where a docstring on `test_undecompressable_body_is_not_cached` would
restate the name and nothing else. That is exactly why the exemption
`9937d11` added is the enabling change and not a loosening: without it,
adopting the rule means 209 lines of restatement, and the honest response
to that bill is to keep not adopting it.

Two of the nine commits reconciled to nothing because this repository had
already made the argument — `increase-if-necessary` on the pip ecosystem,
and naming a tier for its requirement rather than its library. Both landed
here first. That is the second bump in a row where part of the diff was
this project's own reasoning arriving back from upstream, which changes
what reconciliation means: the question is not only "what must change
here" but "what did we already answer, and does the upstream phrasing say
it better".

One rule was declined on its literal terms. `python-lib.md` wants
`grep -rn "sys.path" tests/` to return nothing; here it returns
`conftest.py`'s docstring, which records that the manipulation was removed
and how the suite came to pass against unpackaged source. Satisfying the
grep means deleting the account of the defect the rule exists to prevent.
The check is a proxy; the layout proof — uninstall, then collection must
fail — is the real test, and that one passes.

---

## 2026-08-02 (fourth session) — A decision refuted by its own reconciliation

**Tool**: Claude Code (Opus 5)

Two asks, and the second one broke the first. Retired the `P4` deferral
label in the morning; bumped the templates submodule in the afternoon and
found that upstream had spent the same range making `P4` load-bearing.
The gap between the two was about three hours.

**Changes**

- ADR-011 retired `P4` (#87, #88). The argument was that both issues
  carrying it — #59 and #9 — duplicated a record the repository already
  held, in ADR-008 and in the README and `ARCHITECTURE.md` respectively,
  and that a label records *that* something is deferred while carrying
  nothing about *why*.
- Bumped the submodule `a835374` → `244d3ff`, v2.37.0-3 to v2.40.0-2
  (#81, #89). Nineteen commits, not the eight the ticket listed.
- ADR-012 superseded ADR-011 after the bump refuted its third decision.
- Dropped CLAUDE.md §5.1's reproduce-before-reporting bullet, which
  `review.md` now carries upstream.
- Added the first tracked `.vscode` config — Pylance's type evaluation
  off so mypy is the only type checker, and `.gitignore` turned from a
  wholesale ignore into the allowlist `git.md` now prescribes.

**PRs merged**: #88, #89

**Issues created**: #87. **Closed**: #87, #81

ADR-011 named `[ID: base-issues-defer]`'s Backlog-milestoned issue as the
fallback for when deferral needs to be filterable. Upstream `5a73dc0`,
inside the range the bump crossed, deleted that mechanism and named `P4`
in its place: "Do NOT park the work in a named holding milestone
instead." So the fallback was gone within hours of being written down.

The interesting part is what did *not* fail. Upstream's reasoning is the
inverse of ADR-011's — it argues a label is the durable half of the pair,
because a lane's meaning dies when the milestone is closed. That is true
against a milestone and says nothing about a label against a decision
record, which was ADR-011's actual comparison. So the deletion survived
and only the fallback was withdrawn. The temptation was to treat a nearby
rule moving as the ground moving, and reverse a decision whose facts were
unchanged: still eight open issues, still two deferrals, both still
recorded where their reasoning is.

Worth keeping in view: `base-issues-defer` moved twice inside one bumped
range. ADR-012 says to re-read it on the next bump rather than assume the
reconciliation holds.

The editor-config item was the session's one genuine conformance gap.
`quality-gates.md` Layer 1 has required editor config that enables the
checks since long before this bump — the repository had no `.vscode` at
all and ignored the directory. The new rules in `22cbb8e` and `df59dca`
did not create the gap, they made it visible.

---

## 2026-08-02 (third session) — The suite was never testing the package

**Tool**: Claude Code (Opus 5)

Asked for a restructure, ran the spike, and the spike found something
worse than the layout question it was sent to answer: `pagefetch` is not
installed in this development checkout at all, and all 304 tests pass
anyway. Every green run in this clone has exercised the working
directory. The `src/` move went from a template-conformance chore to a
correctness fix.

**Changes**

- Spiked the layout question against a throwaway copy of `HEAD` (#83),
  measuring the move end-to-end rather than reasoning about it.
- ADR-010 decided the move; #84 landed it before any file moved, per
  `docs.md`'s rule that relocating content is an architectural decision.
- Executed the move (#85): `pagefetch/` to `src/pagefetch/`,
  `pagefetch/tests/` to `tests/`, all 22 files tracked as pure renames.
- Repointed seven `pyproject.toml` settings, plus three path-based
  excludes the ticket had not listed, plus four documents.

**PRs merged**: #82, #84, #85

**Issues created**: #83 — `solid-ai-templates#938`, `#939`

ADR-010 recorded `Upstream: none`, correctly: adopting `src/` needs
nothing upstream, since the chain already prescribes it. Both upstream
issues came out of *executing* the move rather than deciding it — the
suite's own `sys.path` insert (#938), and the fact that a path move
breaks documented commands while every gate check stays green (#939).
A decision-time verdict cannot anticipate those; the end-of-session
harvest is what catches them.

**Issues closed**: #71, #83. #82 referenced #81 without closing it —
the submodule bump it tracks has not happened.

**Decisions**

- *The layout deviation had no argument behind it.* CLAUDE.md §1.2 kept
  the flat layout on two grounds: the package predates this repository,
  and the cache key scheme is path-independent. The first is history. The
  second argues the move is *safe* — an argument for moving, filed as an
  argument against it. Neither survived being asked directly.
- *A CI job would have been the wrong fix.* The strongest alternative was
  to keep the layout and add a job that installs the wheel and imports it
  from a neutral directory. It catches the bug, but only after a
  contributor has already seen green locally against unpackaged source.
  A layout that cannot express the failure beats a job that reports it.
  Recorded in ADR-010 rather than dismissed.
- *Identical measurements were the evidence, not a disappointment.*
  `python-lib.md` asks for scanned-file counts compared before and after
  precisely because a colliding exclude drops a package silently while CI
  stays green. Tests, coverage, statement counts, ruff's file count,
  mypy's source count and the built wheel's contents all came out
  unchanged, which is what proves no pattern started matching.

**What went wrong**

- *The suite carried the bug it was supposed to catch.* `conftest.py`
  inserted the repository root into `sys.path` so `import pagefetch`
  resolved without an install — the actual mechanism behind 304 tests
  passing against an uninstalled package. Nothing in ADR-010 or the
  ticket predicted it; it surfaced from grepping the tree for stale paths
  after the move. Repointing it would have quietly reinstated exactly
  what the ADR decided to end, and the move would have achieved nothing.
- *The ticket's config table was incomplete, and trusting it would have
  failed silently.* #71 listed seven `pyproject.toml` settings and one CI
  line. It missed `.gitattributes`, `.github/codeql-config.yml` and three
  `.pre-commit-config.yaml` hooks, all pinning the fixture directory. The
  `.gitattributes` one is the dangerous one: line-ending normalization
  would have rewritten the frozen HTML snapshots into a failure that
  reads as a detection bug. Enumerate excludes by grepping the tree, not
  by reading the ticket that enumerated them once.
- *Two build artifacts were left in the working tree.* Running
  `pip wheel .` from the repository root created `build/` and
  `pagefetch.egg-info/`. Both gitignored, so `git status` stayed clean and
  nothing flagged them; found by checking directory timestamps against
  the session. Build into a scratch directory, or clean up in the same
  step.
- *A markdown table broke on a column widened in isolation.* Repointing
  the README's project-structure paths widened column one for nine rows
  and left eleven behind. `ruff format` does not check markdown tables, so
  the gate stayed green — the editor's linter caught it.

## 2026-08-02 (second session) — Retiring the template debt

**Tool**: Claude Code (Opus 5)

Started as a status check and became a bill for eighteen commits of
unpaid submodule debt. The pin was not sitting idle — it was producing
wrong work, and three of the four README rules CLAUDE.md carried as
project overrides had been adopted upstream weeks ago.

**Changes**

- Bumped `solid-ai-templates` from `v2.35.0-18-g87493e2` to
  `v2.37.0-3-ga835374` (#73), then reconciled against it in three
  changes: CLAUDE.md §2.7 lost the three rules the template now carries
  (#74), PLAYBOOK §1.3 and §1.5 lost 33 lines of reasoning that
  `platform-github-branch-cleanup` and the new `git.md` sections now hold
  (#75), and §1.4's label rule was corrected (#77).
- Finished the README Features trim (#69), cutting nine bullets to six.
- Added the tracker-close step to the after-merge routine (#68).
- Dropped the deep link from the SSRF limitation bullet (#80).

**PRs merged**: #68, #69, #73, #74, #75, #77, #80

**Issues created**: #67, #70, #71, #72, #76, #78, #79 —
`solid-ai-templates#916`, `#917`, `#919`, `#923`

**Issues closed**: #64, #67, #72, #76, #79

**Decisions**

- *De-stacking stays a deviation.* Upstream requires branching fresh off
  `main` and cherry-picking the dependent branch's commits into a new PR.
  This repository merges `main` in. Both avoid the force-push and both
  leave `main` byte-identical under squash merge; the difference is that
  a new PR discards the review history on the old one, which the template
  does not price. Recorded as a deviation rather than silently kept, and
  filed upstream as `#919`.
- *The label rule was wrong in the playbook, not the issues.* §1.4
  required one priority label from `P0`–`P4`, which #59 and #9 both
  violate by carrying `P3` and `P4` together. CLAUDE.md §2.1 and
  `platform-github-labels` agree that `P4` is a deferral marker
  accompanying a severity. `54e42ec` introduced the error while fixing a
  different one.
- *Compression moved rather than being deleted.* #64 said to cut the
  bullet and keep the detail in the architecture document. That document
  had no compression section, so cutting alone would have lost the
  undeclared-gzip case — mojibake clears `MIN_REAL_CONTENT_BYTES` and
  gets cached as though it were a page. It now has one.

**What went wrong**

- *Two merge rules turned out to be unwritten, and both were found by
  hitting them.* The tracker integration links a merged PR to its ticket
  but never transitions state, so BRA-595/596/600 sat in `In Progress`
  with their merged PRs attached — the open question ADR-007 recorded,
  answered by observation rather than by checking. Then #69 was refused
  because branch protection wants the head up to date, which applies to
  independent PRs merged back to back and not only to stacks. §1.3 framed
  that as a consequence of stacking, so it did not reach the case.
- *The plan called for cutting PLAYBOOK §1.5 down to a pointer, and the
  first attempt duplicated the resync block into §1.3 instead.* Caught on
  re-reading the rendered section. Deleting prose and adding prose in the
  same edit hides the addition inside the deletion's diff.

**Template feedback**

Four filed, none duplicates. The upstream issue list was searched before
each one — the check that was skipped last session, when three duplicates
went in against already-closed issues.

`#916` is content loss: the Branch cleanup section replaced the
`## GitHub Pages` heading instead of being inserted above it, so
`[ID: platform-github-pages]` no longer exists and its two HTTPS rules
now read as branch rules. It is a regression against `#310`, which
delivered them, and exactly what `#303` proposes smoke checks for.
`#917` is a garbled clause in the same section — the bullet that decides
whether a `headRefOid` mismatch is safe to delete through. `#919` argues
merging `main` in should be a permitted de-stacking route. `#923` records
that under required-up-to-date branch protection a batch of N ready PRs
costs N merges plus N-1 update-and-CI cycles.

**Pending**: `solid-ai-templates#907` and `#908`, contributed last
session, are still open — CLAUDE.md §2.7's surviving bullet is annotated
to be deleted if `#907` lands. #78 (`examples/`) is sequenced behind #71
(`src/` layout) so the path-based config audit happens once.

---

## 2026-08-02 — Transport modes named off their libraries; the tracker demoted

**Tool**: Claude Code (Opus 5)

Started as a README conformance check against the template chain and
turned into three things: a breaking rename of the transport API, a
decision about which of GitHub and Linear is authoritative, and four
template gaps filed upstream.

**Changes**

- Restructured the README and moved its technical half to a new
  `docs/ARCHITECTURE.md` (#56). The coverage figures it quoted were
  stale — 65% against a floor of 63% where the measured pair was 79 and
  76 — so the paragraph now points at `fail_under` rather than restating
  a number that ratchets.
- Renamed the transport modes off their libraries (#57): `PLAYWRIGHT`,
  `NODRIVER` and `UC` became `JS`, `HEADED` and `HEADLESS`, with
  `Transport.HTTP` and `--http` added because tier 1 could not be forced
  before. Forcing it does not escalate.
- Made GitHub the system of record and moved two rationales out of the
  tracker into ADR-007 and ADR-008 (#58), then recorded how to merge a
  stack under squash-merge (#61).
- Fixed corrosim's DOI badge (`braboj/corrosim#335`), which is a
  different repository but the same session.

**PRs merged**: #56, #57, #58, #61

**Issues created**: #59, #60, #62, #63, #64, #65 —
`solid-ai-templates#884`, `#885`, `#886`

**Issues closed**: #60

**Decisions**

- *ADR-006 — two bot-bypass tiers.* Nobody had recorded why tiers 3 and
  4 both exist. Neither this repository nor wuseria ADR-035, which
  preserved the ladder "byte-for-byte" without arguing for it. They are
  not redundant: tier 3 is roughly three times faster and tier 4 is the
  only one that runs without a display. That is also why the names are
  `HEADED` and `HEADLESS` — the display requirement is the constraint a
  caller cannot change, whereas which fingerprints each library hides
  changes without notice.
- *ADR-007 — GitHub is the system of record.* Tracker data is portable;
  the lock-in is identifiers written into commit messages and PR titles,
  and rationale that exists only in a ticket description. A branch name
  is the one place a tracker identifier belongs, because branches are
  deleted after merge.
- *ADR-008 — no licensing document yet.* Nothing is redistributed, so
  Apache-2.0's NOTICE requirement does not attach. Three named triggers
  would change that.

**What went wrong**

- *Squash-merging a stack breaks the next PR.* `main` gained one commit
  holding #56's changes while #57's branch still carried the originals —
  identical content, divergent history, reported as a conflict. Rebasing
  was the first instinct and the wrong one: it needs a force-push for no
  benefit, since the squash discards a merge commit anyway. Now a rule in
  `CLAUDE.md` §2.1.
- *The CLAUDE.md audit checked the file against the code but not against
  the template chain it declares.* It missed that neither platform
  template was declared, which is why `platform-linear.md`'s composition
  rule — the code host governs the repository — had never applied here.
  The user caught it.

**Template feedback**

Three duplicates filed and withdrawn, two genuine rules contributed.

`#884`, `#885` and `#886` restate `#881`, `#882` and `#883`. All three
originals were already closed, and two were already fixed upstream in
`bd8f186` and `3a2b7dc`. `#886` was closed as a duplicate with the
reason recorded; the other two were already closed.

The submodule pointer is what hid it. This repository is pinned at
`v2.35.0-18-g87493e2`, fifteen commits behind `origin/main`, and the
fixes are inside those fifteen. Reading the template file in the pinned
submodule answers "does this rule exist here", which is not the question
— the question is "has this already been raised", and that needs
upstream HEAD and the upstream issue list. The same check found that
`git.md` at HEAD already covers squash-merge safety, de-stacking and
merging a stack, which would have been a fourth duplicate.

Filed after checking both: `solid-ai-templates#907` (a README MUST NOT
state a measured figure that moves — coverage, test counts, byte sizes;
name the file that holds it) and `#908` (name a pluggable tier for what
it requires of the caller, not for its library, which is ADR-006
genericized).

**Pending**: #62–#65 are an unstarted README backlog. Whether Linear's
sync is one-way GitHub → Linear was confirmed by the user, but
BRA-595/596/600 were left open to close themselves on merge and have not
been verified. `docs/ARCHITECTURE.md` is an interim home until arc42
documents exist; ADR-008 names where its licensing section lands then.

## 2026-07-31 — Getting the post-merge branch check right

**Tool**: Claude Code (Opus 5)

Housekeeping again, and mostly a session about one paragraph of
`PLAYBOOK.md` that took three PRs to get correct. No package code
changed.

**Changes**

- Merged #42, left open and green at the end of the previous session.
- Rewrote the post-merge cleanup check in §1.5 twice — first from
  `git branch --merged` to a content diff (#43), then from the content
  diff to the PR record (#45).
- Corrected the `P0`–`P3` straggler in §1.4 (#44), the instance #42
  missed in `CLAUDE.md`.
- Cross-referenced the local resync from §1.3, where the remote rewrite
  is issued (#46).

**PRs merged**: #42, #43, #44, #45, #46

**Issues created and closed**: none

**Decisions**

- *ADR-004 keeps its `P0`–`P3`.* The same slip is at line 62, but the
  decision the ADR records is "adopt the template's label scheme", which
  is correct — the range was a mis-transcribed parenthetical, not a
  different decision. ADRs are immutable once merged, and superseding
  ADR-004 would retire four other decisions that are still current. The
  reasoning lives in #44's body so the next reader who hits the line
  finds it.

**Learned**

- A "safe to delete" check has to be exercised against a branch whose
  history was rewritten, not just a clean one. Both broken versions
  passed on the happy path — cut a branch, push it, merge it — and
  neither failure is visible there. `--merged` fails under squash;
  the content diff that replaced it fails whenever `main` moves ahead,
  which a rebase or any intervening merge guarantees.
- The two fallbacks that look authoritative are not. Ancestry
  (`git log <merged-head>..<branch>`) and `refs/pull/<N>/head` both fail
  the same way, because a rebase gives the same work a new SHA on each
  side. Only the PR record survives: `state: MERGED` plus a `headRefOid`
  equal to the local tip.
- Branch protection requires branches be up to date, so any second PR
  queued behind a first needs `gh pr update-branch`. That is what
  creates the stale clone, so the rebase case is the normal case here,
  not an edge one.
- The upstream `scope.md` ships the same broken `--merged` cleanup in
  its session-startup list, so every project generated from it inherits
  the defect.

---

## 2026-07-30 — Branch hygiene and the priority label range

**Tool**: Claude Code (Opus 5)

A short housekeeping session following the audit. No package code changed.

**Changes**

- Deleted `origin/fix/detection-anchoring`, left behind when PR #27
  squash-merged. Its commit `7c82ccd` had a diff identical to main's
  `015dc66`, so nothing was lost.
- Enabled `delete_branch_on_merge` on the repository. The branch above
  existed only because the setting was off; every merged PR was leaving its
  head branch behind.
- Corrected the priority label range in `CLAUDE.md` from `P0`–`P3` to
  `P0`–`P4`.

**PRs merged**: none — #42 was open and green at session end

**Issues created and closed**: none

**Decisions**

- *The template is the authority on the label taxonomy, not CLAUDE.md.*
  The mismatch first read as issue #9 carrying an out-of-convention `P4`.
  It was the reverse: `base/workflow/issues.md` and `platform/github.md`
  both define P0–P4, and the repo's labels already matched. The document
  had drifted from the template it inherits from, so the document was what
  changed.
- *Type labels stay the `bug` / `task` / `spike` subset.* `issues.md` also
  lists `epic` and `incident`, but states the taxonomy is project-specific.
  A single headless library has no production incidents to log and no
  initiatives large enough to warrant epics.

**Learned**

- `delete_branch_on_merge` fires on merge only, not on close — an abandoned
  branch still lingers. It also skips the delete while another open PR
  targets that branch as its base, so it does not remove the need for the
  stacked-PR rule in `CLAUDE.md`.

---

## 2026-07-30 — 360 audit and full remediation

**Tool**: Claude Code (Opus 5)

Vendored the shared template system, audited the package against it, and
closed every finding. 33 findings, 14 tickets, 14 PRs.

**Changes**

- Vendored `solid-ai-templates` as a submodule at
  `docs/solid-ai-templates` (ADR-004), matching the path and URL used by
  `corrosim_repo` and `randomgen`.
- Ran a 360-degree audit and stored it at `docs/audits/2026-07-30-360.md`.
  Perspectives re-projected per the template's headless rule. Overall
  grade C-, weakest dimension Correctness.
- Fixed every finding. The three that mattered: detection predicates that
  discarded real pages, a CLI that could not signal failure, and a reaper
  that killed browsers it had not launched.
- Added the standard documents — `CLAUDE.md` (hybrid model),
  `ONBOARDING.md`, `PLAYBOOK.md`, and this file.
- CI grew a Windows leg; the coverage floor ratcheted 63 → 70 → 76 against
  ~79% measured. `__main__.py` 39% → 99%, `chrome.py` 72% → 100%,
  `fake.py` → 100%. Suite 178 → 299 tests, and faster than it started.

**PRs merged**: #26 through #39 (fourteen)

**Issues created and closed**: #12 through #25

**Decisions**

- *Ambiguous detection phrases are size-gated rather than dropped.* "No
  longer available" and "has been discontinued" are genuine soft-404
  markers on a stub and ordinary body copy on a real product page. Deleting
  them would lose real soft-404 detection; keeping them unanchored was
  losing real pages. They now count only below `MIN_REAL_CONTENT_BYTES`.
- *Batch failure exits 2, not 1.* "Some pages are missing" and "nothing
  came back" call for different handling in a pipeline, and collapsing them
  would force the caller to count output files to tell them apart.
- *Chrome ownership is decided by process ancestry, not PID sampling.*
  Two `tasklist` samples cannot establish that a PID belongs to this
  process. Where ancestry cannot be established, nothing is tracked —
  leaving a browser behind is a nuisance, killing someone's tabs is not.
- *`use_cache=False` stays a refresh, not a bypass.* The audit called the
  write a defect; it is deliberate and was already pinned by a test. The
  README's "bypass cache" wording was what was wrong.
- *Dependency floors were raised anyway.* `increase-if-necessary` is now
  the Dependabot strategy, but the pending bumps were taken first at the
  maintainer's direction, against the recommendation to close them. The
  `browsers` extra and `setuptools` floors now exceed what the code needs.

**Learned**

- *A test suite must not touch the host.* `pytest` killed a real Chrome
  process on the development machine: no test launches a browser, but
  `_start_nodriver_session` sampled the live process list for real even
  behind a fake engine. A conftest fixture now stubs both queries. This is
  what raised #21 from P2 to P0 mid-session.
- *Read the tests before calling something a bug.* Audit finding C5 was
  wrong — the behaviour it flagged was documented in a test written
  precisely to stop a future tidy-up from changing it. The change was made
  anyway and that test caught it.
- *`gh pr merge --delete-branch` closes stacked PRs* pointing at the
  deleted branch rather than retargeting them. Recovery: recreate the ref,
  reopen, retarget. Recorded in CLAUDE.md 2.1. The same class of mistake
  cost Dependabot PR #7, which closed itself when `dependabot.yml` changed
  in an earlier-merged PR.
- *ruff walks the filesystem, not the git index*, so a submodule is linted
  even when untracked here. CI never saw it — `actions/checkout` does not
  fetch submodules by default — so only the documented local gate broke.
- *Linux and Windows cover different branches of `chrome.py`*, so the
  coverage floor has to track the lowest matrix leg rather than any single
  measurement.

**Cross-repo: the PerimeterX spike**

Checked `Imbra-Ltd/wuseria` for tickets this package inherited. Only
wuseria#865 is PerimeterX and it had already been carried over as #9 — but
the carry-over took the body only. Six of its seven comments were left
behind, including a screenshot of the Press & Hold challenge that existed
nowhere else. Archived onto #9 verbatim with original authors and
timestamps. #9 was also missing a priority label; wuseria#865 had P4, so
the `P4` label was created here and applied.

Also retested wuseria#556, which lists ePHOTOzine, Digital Camera World
and CineD as sites that block automated fetches and proposes five manual
workarounds. All three now fetch on tier 1 — plain urllib, ~1s each, no
browser, 15/15 content markers present including the lab figures the issue
depends on. Reported there rather than transferring the issue: it is
scoped to a human workflow and to wuseria's PLAYBOOK, not to this package.
The retest is three articles from one residential IP and does not settle
the batch case.

**Not done**

- #9 (PerimeterX spike) remains open; it predates the audit and none of
  its acceptance criteria were attempted. The cheapest one — testing
  whether challenge frequency tracks request velocity — is still the
  right next step.
- wuseria#556 left open pending a retest against the real scoring batch.
- ADR-002's coverage rationale is still accurate, but the floor has moved
  three times since it was written.
- `--js --uc --nodriver` together resolves to UC. That was undefined by
  test before #36 and is now pinned as-is; whether it should instead be
  an error is an open question, not a decision.

---

## 2026-07-26 — Standalone repository and the toolchain

**Changes**

- Extracted the package from `Imbra-Ltd/wuseria`, where it had grown as
  `tools/pagefetch/`, into this repository (ADR-001).
- Added the Python toolchain and the three-layer gate: editor, pre-commit,
  CI (ADR-002). Coverage floor set to 45 against the measured baseline.
- Fixed `Content-Encoding` handling in the urllib tier — the tier asked for
  gzip and deflate without decoding them.
- Allowlisted `http` and `https` at every entry point (ADR-003). `urllib`
  would otherwise read `file://` URLs and return them as page content. The
  ADR records why blocking private address ranges is deliberately out of
  scope: it would break ordinary intranet and localhost fetching while
  offering a guarantee this layer cannot honestly make.
- Extracted the batch session lifecycle into `_BatchSession` and brought it
  under test; coverage floor raised 45 → 63.

**PRs merged**: #5, #8, #10, #11

---

## 2026-05-20 to 2026-05-30 — Upstream history

The package grew inside `Imbra-Ltd/wuseria` before this repository existed.
Summarized here because the commits are not in this history; the README's
"Performance history" section carries the per-version detail.

- Three-tier engine (urllib, Playwright, UC), then Nodriver added as tier 3
  via CDP, which cut a three-page bot-protected batch from 27s to 16s.
- Refactored from a single 748-line script into a package with a
  `PageSource` ABC, `NetworkFetcher` and `FakeFetcher`.
- Cache correctness work across several sessions: throttle pages stopped
  poisoning the cache, 404/gone bodies became terminal and self-healing,
  passive delete on read plus `--clean-cache`, and the cache directory
  unified behind `PAGEFETCH_CACHE_DIR` with a `--cache-dir` flag.
- Tightened the Cloudflare "checking your browser" pattern after it
  false-matched ad-blocker help text on a real DPReview page — the same
  class of defect the 2026-07-30 session found twice more.

Two decision records from that period still cover this package:
[ADR-035](https://github.com/Imbra-Ltd/wuseria/blob/main/docs/decisions/035-pagefetch-package-and-brandkit.md)
on the extraction and the standard-library-only contract, and
[ADR-037](https://github.com/Imbra-Ltd/wuseria/blob/main/docs/decisions/037-pagefetch-cache-validity-no-ttl.md)
on content-based cache validity.
