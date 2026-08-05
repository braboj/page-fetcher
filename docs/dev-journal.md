# Dev journal

One entry per working session, newest first. Records what changed and why
the decision went the way it did — not a changelog of every commit, which
git already holds.

---

## 2026-08-05 (fourteenth session) — The offline rule, and what it almost cost

**Tool**: Claude Code (Opus 5)

Started as a question about the offline rule — what it is and why it stops
this package demonstrating its own escalation ladder. Ended four PRs later,
almost all of them upstream.

**Changes**

- `base/core/examples.md` extracted upstream, with per-section IDs for
  contents, index, offline and the smoke job. ADR-025 there records it.
  `base/core/readme.md` §5 keeps a pointer; `stack/python-lib.md` keeps
  the Python residue.
- `go-lib` and `nodejs-lib` wired, each with the residue its language
  needs — Go's `Example` functions with `// Output:` comments are
  verified by `go test`, which machine-checks the real-output rule.
- Submodule bumped `cf244d9` → `00fd16b`. CLAUDE.md's chain list gains
  `examples.md`, and §1.2 drops the two rules that now come from
  upstream, keeping only the `NetworkFetcher` ban.

**PRs merged**: #121, #119 (the thirteenth session's close-out).
Upstream: solid-ai-templates#990, #992

**Closed**: #120. Upstream: solid-ai-templates#988, #991

The rules governing `examples/` were split between the stack template
that prescribed the directory and the README template that prescribed
its contents, reached through a conditional bullet under Project
structure. That split is why the two gaps found in the twelfth session
went unfixed: neither owner was the obvious place for them.

The part worth remembering is what the first draft of the extracted rule
said. "Examples MUST run offline" — undefined, and absolute. Undefined,
it bans an example that starts the project's own service on localhost,
which is reproducible forever. Absolute, it tells a project whose entire
surface is a vendor's API to build a fake of that API before it may ship
an example, where the real alternative is no example. Both were caught by
the reader, not the author, and the fix was to define offline as no host
outside the project and add a bounded exception — name the service, say
why no seam, date the output, quarantine it from the gating CI leg.

That mattered more than it looked, because service stacks inherit library
stacks. `base-examples` resolves in 11 of 17 chains, and 6 of those the
moment #990 merged, via the `stack-python-service` → `stack-python-lib`
edge. The absolute version would have handed every FastAPI and Go service
project a rule it could not satisfy. Declaration is not reach, and the
check is `py tools/resolve.py`, not the manifest.

The bump broke PLAYBOOK §4.4 twice, found in the close-out rather than
before the commit. It pins `00fd16b`, which is `v2.44.0-3` — the
mid-flight revision the section forbids, for reasons this repository
learned at `v2.42.0`. And #121 moved the pointer and reconciled
CLAUDE.md in one commit, where §4.4 asks for two so the reconciliation
is not hidden inside the submodule's diff. The rules that motivated the
bump are in no released tag, so the honest fix is a `v2.45.0` upstream
and a re-pin, not a quieter pin. Read the playbook section before the
operation, not during the audit that catches it.

A pre-defined cache was considered for demonstrating escalation offline
and rejected on reading the code: `_fetch_single` reads the cache before
`_escalate` is ever called, so a bundled cache demonstrates the one path
that skips the ladder, and `tier_used` would read `cache` rather than any
tier. ADR-015 stands. Extracting the ladder's decision as a pure state
machine would work, but that is a refactor of the riskiest module in the
package for a documentation payoff — the exact trade the upstream
exception exists to refuse.

---

## 2026-08-05 (thirteenth session) — A convention nobody was enforcing

**Tool**: Claude Code (Opus 5)

Started as a reader's complaint about eleven lines in
`examples/cache_lifecycle.py` and ended as a gate. The complaint was
correct and the cause was not the file.

**Changes**

- 26 comment-layout sites fixed — 22 blank lines, 4 asides moved above
  the code they explain. No behaviour changed.
- `tools/check_comment_layout.py`, a fourth Python root, wired into
  pre-commit, the `Lint and format` job and the suite.
- ADR-016 records the rule, the gate and five carve-outs. CLAUDE.md
  §1.2, §1.3 and §2.3, README "Project structure", ONBOARDING §3 and
  PLAYBOOK §3.2 and §3.6 follow it.

**PRs merged**: #116 (the twelfth session's close-out, opened last
session), #118

**Closed**: #117. **Filed upstream**: solid-ai-templates#989

`quality.md` states three comment-layout rules as MUSTs. Next to them
sits the rule about ticket numbers in comments, which tells projects to
enforce it with a grep test. These three name no mechanism at all, so
enforcement here was review — and review had passed 26 violations since
the first commit while every other gate stayed green. The one that
surfaced them was caught by a person reading an example.

The useful part was how much of the first sweep was wrong. A naive
implementation flagged 42 sites, and three rounds of false positives each
changed the design. The 41 `# --- section ---` banners were dividers, not
comments on the line below. A commented `elif` in `cache.py` got a blank
line while the `else` below it kept none, which is worse than the defect.
And three insertions into `detection.py`'s pattern list were deleted
again by `ruff format --check` — ruff owns whitespace inside collection
literals, so a gate demanding a blank line there would have fought the
formatter on every commit forever.

That last one is why the carve-outs are in the ADR rather than in a
comment. Four of the five are not exceptions to the rule; they are places
where obeying it contradicts `ruff format`, `D202`, or the shape of the
syntax. A style rule another tool undoes is a loop, not a rule.

Two things came out on the way. The width rule was implemented and then
removed: `E501` already measures comment lines, so it was a second
implementation that would drift the moment `line-length` moved. And the
hook was written `language: system`, which resolves `python` from `PATH`
— it failed on the machine that wrote it, because the documented Windows
workflow uses the `py` launcher and `PATH` has no `python` on it. Both
were found by running the thing rather than by reasoning about it.

The ten value tables in `source.py` and `detection.py` keep their
trailing comments, deferred deliberately: moving five enum members above
their values costs fourteen lines and turns a legend a reader scans into
a list they reassemble. They are matched by shape — constant assignment,
annotated field, literal collection element — not by a path allowlist,
which would exempt the files rather than the construct and go on
exempting them after the construct was gone. That is the same objection
ADR-015 raised against a path-scoped gitleaks allowlist, arriving from a
different direction.

---

## 2026-08-04 (twelfth session) — Examples for a package that fetches

**Tool**: Claude Code (Opus 5)

The chain has asked for `examples/` since the v2.41.0 bump (#78) and this
repository had none. The interesting part was never the four files.

**Changes**

- `examples/` with four patterns and an index pairing each command with
  its real output. #78 closed by #114.
- An `Examples` CI job, in `Gate` via `needs`.
- ADR-015 records the shape. CLAUDE.md §1.2, PLAYBOOK §2.6 and §3.4, and
  ONBOARDING §3 and §4 follow it.

**PRs merged**: #112 (the eleventh session's close-out, opened last
session), #114

**Closed**: #78. **Closed unmerged**: #113

The requirement collides with what the package is. Every other rule in
`[ID: python-lib-structure]` is satisfiable by a library that computes;
this one wants runnable examples that are also offline, from a package
whose entire job is fetching web pages. An example that shows the ladder
working needs a network, and with one it is neither offline nor
reproducible — the output in the index stops being a fact and becomes a
claim about what a server returned that day.

So the rule went further than "avoid the network": no example constructs
a `NetworkFetcher` at all. The weaker version fails in a way the stronger
one cannot, by inviting an example that forces `HTTP` transport at a URL
that obviously resolves, which is offline until it is not. The cost is
real and is recorded rather than hidden — the escalation ladder is what
this package is for, and no example demonstrates it.

**The trap that cost the most**

The cache example labelled its output `key:` followed by the cache
filename. That stem is `sha256(url)` truncated, public and reproducible
by anyone who runs the file. It is also a keyword followed by a 16-hex
token, which is gitleaks' `generic-api-key` shape, so the secret scan
failed on a documentation file containing no secret.

Writing this entry failed the same scan twice more, because the first
draft of both this paragraph and ADR-015 quoted the string in full. The
rule generalises further than the examples index: any document that
explains the finding is a document that reproduces it.

Two rules in the chain produced it together and neither mentions the
other: `readme.md` requires examples to paste real output, and the
platform template requires a secret scanner. An examples index is the one
document in a repository whose content is machine-generated prose —
every other document is written by someone not trying to print an
identifier. Filed upstream as solid-ai-templates#987.

Renaming the label fixed it. An allowlist would have been faster and is
wrong twice: a fingerprint-scoped entry names a commit that disappears at
squash-merge, and a path-scoped one permanently exempts the single file
whose contents are pasted program output.

**Then it failed again, for a different reason**

The fix landed and the scan still failed. The pre-commit hook reads the
working tree; the CI action reads every commit in the branch. A finding
fixed in a follow-up commit is still in the branch, so the check cannot
pass — the branch has to stop containing the string. Squashing and
force-pushing was declined, so #113 was closed and reopened as #114 with
one commit that never held it. PLAYBOOK §3.4 now says all of this, and it
is the second half of #987.

**Smaller things**

- #78 scoped "a wheel exclusion alongside the existing
  `exclude = ["pagefetch.tests*"]`". That exclude has not existed since
  ADR-010, and under `src/` a root-level `examples/` cannot reach the
  wheel anyway. Verified by building one and listing it rather than by
  reasoning about it, which is how the assumption was caught.
- The smoke job installs with `pip install -e .` and no dev extra. Reusing
  the `test` job was one line cheaper and proves the wrong claim — that
  the examples run alongside pytest, which no reader has. Filed upstream
  as solid-ai-templates#988, since `python-lib.md` says "smoke-tested in
  CI" without saying how the package gets installed.
- The job globs `examples/*.py`. A listed job silently stops covering the
  file someone forgot to register, which is the failure the rule exists
  to prevent.
- solid-ai-templates#986, filed last session, had no labels — against that
  repository's own label-at-creation rule. Labelled this session.

**Not done**

- #9's velocity measurement. Four sessions now. It needs a headed Chrome
  and live requests, which no headless session can do — this is waiting
  on a working session at the machine, not on a decision.
- ADR-002's coverage rationale is still accurate and still describes a
  floor that has moved several times since.
- `--js --uc --nodriver` resolving to UC remains pinned by test and
  undecided.

---

## 2026-08-04 (eleventh session) — The rule that only applies to moves

**Tool**: Claude Code (Opus 5)

One spike, #92: should `network.py` become a package? The answer is no,
and the reason that decided it is not the reason the issue expected.

**Changes**

- ADR-014 declines the split. #92 closed by #111.
- CLAUDE.md §1.2 and PLAYBOOK §2.1 gained pointers, because the ADR makes
  the section comments structural and constrains what a future split's
  submodules may be called.

**PRs merged**: #111

**Closed**: #92

The issue asked three good questions and the first one was unanswerable
as posed: does the file meet the rule's threshold? `quality.md`'s rule
has no threshold. It sits under **High Cohesion** and prescribes a
"cohesive seam", so the size question is one the rule never asks.
Answering the question it does ask, `network.py` passes — four tiers are
four implementations of one operation.

But cohesion is not what settled it. This is:

The rule tells you to leave the test module alone, and explains why — the
untouched suite is the regression oracle. That property only exists for a
*mechanical* move. `NetworkFetcher` reads its three injected fields from
16 sites across all four tiers and both batch starters, and the tiers
cross-call each other, so any real seam needs dependency injection or a
strategy protocol. Do that and the suite is still green, but green now
means something weaker: it passes over rewritten call paths it was never
written to distinguish. The split would spend its own oracle on the change
the oracle exists to check. That weighs harder here than it would
elsewhere, because the tier bodies are hand-validated rather than covered
— the oracle was already thin.

So the rule is silent on the case this repository actually has. It
governs moves and does not say so. Filed upstream as
solid-ai-templates#986, which also proposes the route the rule is missing
— reshape first under verification that fits a reshape, then split
mechanically with the oracle intact for the second step.

The reusability verdict belongs on the ADR, per `scope.md` item 11, and
it is not there. ADR-014 merged without an `Upstream:` line, and it is
immutable now — `docs.md` allows a format-only migration, and adding a
paragraph is not one. Nothing is lost, because the verdict is here and
the issue is filed, but the record that should carry it does not. The
generic core has to be judged while the ADR is being written, not at
wrap-up.

Two smaller things the analysis turned up, both inversions of what #92
assumed:

- The line count is contaminated by the bump that raised the question.
  #92 measured 897; the file is 915. All 18 lines are docstrings from the
  `D`-rule adoption in the same v2.41.0 bump that introduced the split
  rule. The metric moved 2% on a change that added no logic, which is the
  argument against ever writing a threshold down.
- #92 listed the four ruff exemptions as a *cost* of splitting —
  "splitting scatters them across new files". It is a benefit. `PLR0911`
  is currently granted over all 915 lines to serve one function; a split
  would narrow each exemption to the file that earns it. It is the only
  real argument in favour, and the ADR records it as one rather than
  inheriting the issue's framing. It still does not pay for a new
  abstraction.

The verdict went to the user rather than being taken here. Three verdicts
were live — decline, decline-plus-sibling-extractions, full reshape — and
they are materially different amounts of work, which is the case where
asking beats assuming.

**Not done**

- `require_supported_scheme` → a sibling `urls.py` is defensible on its
  own merits: public API, its own ADR, its own test file, never touches
  the network, and needs no package at all. Left in ADR-014's
  alternatives table rather than done, because it is ordinary module
  placement dressed as an answer to a question about a 915-line file. 25
  lines against 915 is not what #92 was asking about. Available later for
  its own reason.
- #9's velocity measurement, still. Three sessions now.

---

## 2026-08-03 (tenth session) — The report was wrong about its own bug

**Tool**: Claude Code (Opus 5)

A continuation of the ninth, past its close-out. Two things came back:
the bug it filed, and the upstream issue it filed.

**Changes**

- #109 fixed #107. Empty values now fail at `_flag_value` and at
  `FileCache`, and `entries()` matches the key scheme.
- solid-ai-templates#982 withdrawn, closed as not planned.
- PLAYBOOK §2.5 was describing pre-#98 behaviour; README's configuration
  table gained a line.

**PRs merged**: #109

**Closed**: #107, solid-ai-templates#982

The issue named the wrong mechanism, and I found out by fixing it. #107
said `--cache-dir ""` made the working directory the cache. It did not —
`_make_cache` did `Path(cli_dir) if cli_dir else None`, so an empty value
became `None` and resolved to the *default*. A precedence violation with
no data loss in it. The working-directory outcome comes from the library
constructor, because `Path("")` is `.`.

The ninth session's entry congratulates itself for running both cases
rather than reasoning about them, and that was true of `FileCache` — the
probe that produced `<cwd>` was `FileCache(cache_dir=Path(''))`, a direct
library call. I then wrote up the CLI as if it did the same thing, having
never run it. One level of the stack verified, the level above it
assumed, and the assumption is what went in the issue title's blast
radius.

Two things fell out of correcting it, neither of which the issue would
have reached:

- `--output-dir ""` and `--batch ""` have the identical shape. Visible
  only once the fix moved to `_flag_value` instead of the call site #107
  named. An issue that names one call site produces a fix that repairs
  one call site.
- Acceptance criterion 4 — whether `entries()` should filter on the key
  scheme — was flagged as *not obviously yes* and put to the user.
  Writing the fix answered it. `Path("")` collapses to `.` before the
  constructor sees it, and `.` is indistinguishable from a legitimate
  explicit `Path(".")`, so the constructor cannot reject it. The filter
  is not defence in depth for that case; it is the only defence.

The upstream issue went the other way. #982 argued that deferral riding
on the milestone field is a gap for a project that uses no milestones.
The user's response was that no explicit deferral is needed at all, which
is correct and is ADR-011's own argument — at six open issues, "which are
deferred" is answered by reading the list. `github.md` makes milestones
optional deliberately, so a project carrying no deferral machinery is
using a supported configuration rather than falling through one. I had
re-derived, as a template defect, a question this repository settled two
ADRs ago.

Worth separating from the #107 mistake, because they fail differently.
That one was a verification gap — a claim I could have checked in one
command and did not. This one was reasoning from a diff without asking
whether the thing the diff describes was ever wanted here. The
reconciliation procedure has a rule for the first kind (`§4.5`, read at
the right revision) and now, upstream, for the second (`docs.md`,
re-read the divergence record). Neither catches "the rule is fine and we
don't need it".

**Not done**

- No ADR for the `entries()` narrowing. Judged a bug fix implementing a
  chain rule rather than an architectural decision — it changes what
  `clean()` may touch, which is arguable. Flagged rather than assumed.
- The coverage floor stayed at 76.0 against a measured 79.84. Two tenths
  of a point of movement is not a ratchet.
- #9's velocity measurement, still.

---

## 2026-08-03 (ninth session) — A documentation bump with a P1 in it

**Tool**: Claude Code (Opus 5)

Bumped the templates submodule v2.42.0 → v2.44.0 and reconciled, which
was #104 and the whole agreed scope. Two things came out of it that the
ticket did not predict: the divergence it was written to re-decide had
already closed, and the range contained a rule that turned out to be
about the source tree rather than the documents.

**Changes**

- Pinned v2.44.0, range `be29d59..cf244d9`. Twelve commits, two releases
  cut hours apart the same day.
- ADR-013 supersedes ADR-012; ADR-012's status flipped in the same PR.
- CLAUDE.md §2.1 and §5.2 and PLAYBOOK §1.3, §1.4 and §4.4 reconciled.
  Three overrides dropped that `git.md` now owns.
- Filed #107 here, and solid-ai-templates#982 upstream.

**PRs merged**: #106

**Closed**: #104

The deferral question resolved in the direction nobody was watching for.
Every previous reading of `base-issues-defer` had this repository holding
a position against the chain: ADR-011 declined the `P4` label, ADR-012
restated the decline more accurately after upstream made the label
load-bearing. This range retires `P4` outright. `github.md` now says a
fifth priority label MUST NOT exist, which is the state this repository
reached on its own the day before. The divergence closed without anything
moving here.

That is a shape worth naming, because the reconciliation habit is built
around the opposite one. #104 was written expecting decision 4 of ADR-012
— the route back, recreate `P4` — to need re-deciding. It did, but not by
being weighed again: it was deleted. A reserved fallback can stop existing
between the ticket being filed and the ticket being worked, and re-reading
the ADR is what catches that, exactly as `docs.md` gained a rule saying in
this same range.

What replaced it does not work here. Deferral now rides on the milestone
field, and this repository has never created a milestone, so every one of
its six open issues is unmilestoned and the rule marks none of them. Not
violated — satisfied vacuously, which is a different thing and reads
identically to conforming from the outside. ADR-013 records it so a later
audit reading six unmilestoned issues against that sentence does not have
to guess which of the two wrong conclusions to draw. `github.md` makes
milestones optional in the same breath `issues.md` makes the field carry
deferral, and that is solid-ai-templates#982.

Re-reading ADR-011 against the new text also corrected this repository's
own count. It named two deferrals, #59 and #9, on the evidence that both
carried `P4`. Only #59 is one: its body has three concrete triggers and
ADR-008 has the reasoning. #9 is an open `P3` spike with a cheapest-first
next step and nothing gating it but severity — its `P4` was recording low
priority a second time. Writing a deferral note over it would have
suppressed the one measurement the issue is asking for.

The part that nearly got missed: `config.md` gained a rule in this range,
and `config.md` governs code. Its second half — an empty environment
variable and an empty config key fall under the same rule as a trailing
CLI flag — pointed at `cache.py`, not at a document. `#98` had fixed the
flag case last session and it was tempting to file the whole rule as
already satisfied.

```text
  PAGEFETCH_CACHE_DIR=""     -> <cwd>/.cache/pagefetch   (same as unset)
  --cache-dir ""             -> <cwd>                     Path("") is "."
                                     |
                                     v
  entries() globs every .txt/.html in the cache dir. It does not filter
  on the sha256[:16] key scheme, because inside a real cache directory
  there is nothing else to match. --clean-cache then reads the working
  directory and unlinks whatever the junk classifier flags.
```

Both were run rather than reasoned about, which is the only reason the
second one was characterised correctly — reading `cache.py:52` finds a
truthiness test and looks like a precedence nit. It is #107 at `P1`, and
it stayed out of #106 because one concern per PR, not because it was
small.

Six templates bumps in, the reconciliation has been a prose exercise every
time. This one was a `docs:` commit and a `bug`/`P1` issue, from the same
range. A changed template is a claim about the repository, and which half
of the repository it lands in is not something the file path tells you.

**Not done**

- #107 is filed and unfixed. Its fourth acceptance criterion — whether
  `entries()` should filter on the key scheme as defence in depth — is a
  real question and not obviously yes; the key scheme is fixed by
  CLAUDE.md §2.6, so the filter costs nothing, but it also hides a
  mis-resolution rather than failing on it.
- solid-ai-templates#982 offers to raise the PR upstream. Not raised.
- #9's velocity measurement is still the cheapest open thing in the
  repository and still untouched, four sessions after it was first named
  as such.

---

## 2026-08-03 (eighth session) — The answer was already in the PLAYBOOK

**Tool**: Claude Code (Opus 5)

Merged the three PRs the previous session left green and unmerged. That
was the whole scope. The one thing worth recording is that I got a call
wrong that the repository had already answered in writing.

**Changes**

- Merged #101, #102 and #103 in that order. The last two each needed
  `gh pr update-branch` and a full Gate rerun first.
- CLAUDE.md §2.1 states the general case instead of only the stacked one.
- PLAYBOOK §1.3 gains the sibling commands, §4.4 the `git submodule
  update` that a merged bump needs.
- Filed upstream: solid-ai-templates#976 and #977.

**PRs merged**: #101, #102, #103

**Closed**: #98, #99

Asked for status, I reported the three as siblings rather than a stack —
all based on `main`, touching disjoint files — and concluded that merge
order did not matter and no conflict was possible. #101 landed and the
other two flipped to BEHIND. `mergeable` stayed MERGEABLE throughout, so
nothing about the content was wrong; what blocked them was `strict: true`
on `main`, which requires the head be up to date with its base and never
looks at whether the diffs overlap.

PLAYBOOK §1.3 says this already, in as many words: "The same step is
needed for PRs that were never stacked ... even when the two touch
disjoint files." The answer was sitting in the repository while I reasoned
my way past it, because I reasoned from CLAUDE.md §2.1 — the file that
loads on every turn, and which frames the entire subject as stacking and
squash-merging. A missing rule is the safer failure: it prompts a look
somewhere else. A rule that covers most of its subject reads as complete
and ends the search, which is why §2.1 now carries the general case in one
line and points at §1.3 for the rest. The always-loaded file does not have
to hold the procedure, but it does have to stop a wrong conclusion.

The submodule was the tail of the same day. `gh pr merge` fast-forwarded
the local `main` past #101's pin bump, and a fast-forward does not move a
submodule working tree: `git status` showed `docs/solid-ai-templates`
modified, `git submodule status` showed the `+`, and the checkout sat at
v2.41.0 while the pin said v2.42.0. §4.5 exists to stop exactly this —
reading the templates at a revision that is not the one under discussion —
and §4.4 walked through bumping the pin without saying what the merge
leaves behind. Landing the bump is the moment the clone is most likely to
be read and least likely to be right.

**Not done**

- #104 (P2, no milestone) is the next bump, past v2.42.0. Nothing has been
  read from upstream toward it.

---

## 2026-08-03 (seventh session) — What the pin says and what main says

**Tool**: Claude Code (Opus 5)

Two issues, one P2 and one P3. Each described its work accurately and got
a premise wrong, and the two mistakes point opposite ways: one read the
templates from too far ahead, the other scoped a fix too narrowly.

**Changes**

- Bumped the submodule v2.41.0 → v2.42.0 and reconciled (#99, #101).
  CLAUDE.md §2.7's filed-upstream bullet is dropped, §2.1's system-of-record
  restatement is trimmed to a pointer, and the new label conformance check
  is named in §5.2 and run — `[]` over seven open issues.
- Rejected a value flag that arrives with no value (#98, #102). The guard
  went into `_flag_value` rather than to the three call sites the ticket
  named.
- PLAYBOOK §4.4 now checks out the latest tag instead of `origin/main`.

**PRs**: #101, #102 — both green, both unmerged (see Not done).

**Closed**: none yet; #98 and #99 auto-close on merge.

The bump contains the rule that explains the mistake in the ticket
describing the bump. #99 attributed the `P4` retirement to the range,
citing `8cda540`. That commit is untagged and sits four commits past
`v2.42.0`, so the ticket was written against `origin/main` — and
`cdb66dc`, inside the very range being bumped, adds to `agents.md` the
two-questions-two-revisions split with the explicit bullet "never read
from `origin/main`, and never from the working tree after a bare fetch".

This repository already knew that; it is PLAYBOOK §4.5, written before
upstream adopted it. What nobody had noticed is that §4.4 — the bump
procedure two sections above it — says `git -C docs/solid-ai-templates
checkout origin/main` in a fenced block. The rule and the procedure that
breaks it have been sitting on the same page for several sessions. It
never produced a wrong pin because every previous bump ran while the tag
*was* HEAD, so following either one gave the same commit. This is the
first bump where main had moved on, and the contradiction surfaced as a
wrong ticket rather than as a wrong pin. A procedure and a principle that
agree by coincidence look identical to ones that agree by construction,
right up until the coincidence lapses.

Second finding, from deciding what the bump actually governs: what
governs is reachability, not the list. CLAUDE.md names nine chain files
and `workflow/issues.md` is not among them — but `platform/github.md`
`DEPENDS ON` it, so `base-issues-record` and `base-issues-duplicate` do
govern here, and §2.1 had been restating the first of them by hand.
`agents.md` and `devsecops.md` are reachable from nothing declared and do
not govern, however useful they read. The list in CLAUDE.md is a
convenience copy of a graph, and scoping from the copy gets it wrong in
both directions at once — pulling in rules that do not apply while
missing ones that do.

The value-flag fix is the smaller lesson and the more repeatable one.
Issue #98 said to copy `_parse_mode`'s guard to the three flags that
predate it. A ticket that says "apply this pattern at N call sites" is
usually evidence the pattern belongs one level down instead. Moving the
guard into `_flag_value` cost less than three copies would have, deleted
`_parse_mode`'s pre-check — the helper now carries the distinction that
check existed to make — and caught a fourth flag nobody had counted:
`--batch` with no value fell back to reading URLs from `argv`. The ticket
named three flags because three was what the reporter checked, which is
the ordinary way an enumeration goes stale.

**Not done**

- #101 and #102 are green and unmerged. The merge was refused by the
  local permission classifier, not by GitHub or by a failing check.
  Merging them, and confirming #98/#99 auto-closed, is the first thing
  next session.
- `8cda540` and three commits behind it retire `P4` upstream and sweep
  every surface that instructs it. ADR-012 is unaffected at this pin —
  `base-issues-defer` is byte-identical across v2.41.0 and v2.42.0 — and
  its standing requirement to re-read on every bump discharged here with
  no edit. The next bump is where it moves for the third time.
- `devsecops.md`'s redistribution-attribution rule does not reach this
  repository and did not this session, but it is the substance of #59 if
  the distribution model ever changes.

---

## 2026-08-02 (sixth session) — The README front matter and the last boolean

**Tool**: Claude Code (Opus 5)

Three issues that all sat on the same ten lines of README, plus the one
CLI flag that never caught up to the library. Both remaining P2s closed.

**Changes**

- Split the subtitle (#62, #94). The differentiator half keeps the slot;
  the scope disclaimer moved to Known limitations.
- Rewrote the lede against the detector (#63, #95). 48/100 → 18/100.
- Replaced `--html` with `--format`, defaulting to text (#65, #96).

**PRs merged**: #94, #95, #96

**Closed**: #62, #63, #65

The subtitle question turned on one word in `readme.md`: the slot is for
an italic *differentiator*. That settles both halves at once. "Fetch a
page by the cheapest means that works" is the differentiator and earns
the slot — it is not repetition of the lede, because compressing a claim
the summary then expands is exactly what the heading / badges / subtitle
/ summary order is for. "Not for bulk scraping" is a limit, and a limit
placed where nobody has decided to use the tool yet does no work. In
Known limitations it is read by someone about to scale up, which is the
only reader it was ever for. The hyphen that prompted the ticket was a
symptom of one line doing two jobs.

The lede is the more useful result, because it says why five rewrites in
one session failed. The mechanical pass was clean both times — no marker
vocabulary, no curly quotes, not one em-dash. Everything that scored was
structural, and the structure survived every rewrite that only changed
words. The load-bearing one: "pagefetch selects the transport per
request" followed by "It issues..., inspects..., and escalates...", an
abstract topic sentence with its own concrete restatement immediately
behind it. Deleting the abstract half is the only edit that removes it;
rewording either half leaves the shape and the reader flags the
replacement too.

Worth keeping: the three-part list stayed. "Bot wall, error page, body
too short" is what `detection.py` actually returns, so it is a real list
and not a reach for three — what gave it away as padding was the broken
parallelism, two noun phrases and then an adjectival one. Fixing the
parallelism was the right move, deleting the list would not have been.

`--format` is small but closes the loop on something wuseria ADR-035
started: the library replaced `raw_html` with `ContentMode` for the
reason `quality.md` gives, and the CLI kept the boolean for another year.
The argument that a boolean cannot express its own default is not
abstract here — before this there was no way to write "text", so a script
could not state its intent and would have silently followed the default
if it moved.

One thing found while writing it, not fixed: `_flag_value` returns `None`
both for "flag absent" and "flag present as the last argument", so a
trailing `--wait` silently takes the default. `_parse_mode` guards
against it; `_parse_wait_ms` still does not. Left alone as out of scope
rather than smuggled in.

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
