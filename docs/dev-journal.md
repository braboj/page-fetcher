# Dev journal

One entry per working session, newest first. Records what changed and why
the decision went the way it did — not a changelog of every commit, which
git already holds.

---

## 2026-07-30 — 360 audit and the P0 fixes

**Tool**: Claude Code (Opus 5)

**Changes**

- Vendored `solid-ai-templates` as a submodule at
  `docs/solid-ai-templates`, matching the path and URL used by
  `corrosim_repo` and `randomgen`.
- Ran a 360-degree audit and stored it at `docs/audits/2026-07-30-360.md`.
  The perspective set was re-projected per the template's headless rule —
  pagefetch has no user-facing surface, so Discovery does not apply, Value
  reduced to the README contract, and Quality split into five engineering
  dimensions. Overall grade C-, weakest dimension Correctness.
- Fixed the three P0s the audit found, each reproduced against the code
  before being written up.
- Raised the coverage floor 63 → 70; `__main__.py` went 39% → 87%.
- Added the standard documents this file is part of.

**PRs merged**: #26, #27, #28

**Issues closed**: #12, #13, #14, #17

**Issues created**: #12 through #25

**Decisions**

- *Ambiguous detection phrases are size-gated rather than dropped.* "No
  longer available" and "has been discontinued" are genuine soft-404
  markers on a stub and ordinary body copy on a real product page. Deleting
  them would lose real soft-404 detection; keeping them unanchored was
  losing real pages. They now count only below `MIN_REAL_CONTENT_BYTES`.
- *Batch failure exits 2, not 1.* "Some pages are missing" and "nothing
  came back" call for different handling in a pipeline, and collapsing them
  would force the caller to count output files to tell them apart.
- *The coverage floor sits below the measured figure.* It is measured on
  Windows and enforced on Linux, where the `chrome.py` branches fall
  differently. The margin is headroom, not slack.

**Learned**

- `gh pr merge --delete-branch` closes stacked PRs pointing at the deleted
  branch rather than retargeting them. Recovery is to recreate the ref,
  reopen, then retarget. Recorded in CLAUDE.md 2.1.
- ruff walks the filesystem, not the git index, so a submodule is linted
  even when it is not part of this repository's tracked files. CI never saw
  it, because `actions/checkout` does not fetch submodules by default —
  only the documented local gate broke.

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
