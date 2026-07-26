# ADR-001: Extract pagefetch into a standalone repository

**Status:** Accepted
**Date:** 2026-07-26

## Context

`pagefetch` was written inside [Imbra-Ltd/wuseria](https://github.com/Imbra-Ltd/wuseria),
a Fujifilm lens and camera explorer, as the fetcher behind that project's
optical-spec scrapers. It began as a single 748-line script,
`tools/fetch-page.py`, and was refactored into an importable package at
`tools/pagefetch/` under that repository's ADR-035.

ADR-035 already described the package as standalone and submodule-ready, and
the code holds to it: nothing under `tools/pagefetch/` imports anything
outside itself or the standard library, and no host-specific value is read
from a global — the one configurable value, `cache_dir`, is a constructor
parameter with a portable default. The extraction was deferred at the time,
not rejected.

Two things made it worth doing now. The package is useful to projects that
have nothing to do with camera lenses, and vendoring a copy into each of them
is how a shared utility starts to drift. And a package living three
directories deep in an unrelated repository is not discoverable by anyone who
might use it.

The awkward part is history. `tools/pagefetch/` carries only seven commits,
because the directory did not exist before the refactor. Filtering on that
path alone produces a repository that appears to begin on 2026-05-28, with
the origin of the escalation logic — the three-tier engine, the Nodriver
tier, the bot-detection patterns — silently dropped. The ancestor script
carries the rest.

## Decision

Split `pagefetch` into `braboj/page-fetcher`, a public MIT-licensed
repository, preserving history across the package and its ancestor script.

**1. History spans all three paths, not just the package.**

The split runs `git filter-repo` over `tools/pagefetch/`,
`tools/fetch-page.py`, and `tools/FETCH-PAGE.md` together. The refactor
commit deleted the script and created the package in one step, so including
the script's path keeps that commit legible as a refactor rather than an
apparently-from-nothing creation.

```text
wuseria (1142 commits)
  |
  +-- tools/fetch-page.py ------+  5 commits, from 2026-05-20
  +-- tools/FETCH-PAGE.md ------+  (deleted / stubbed at the refactor)
  +-- tools/pagefetch/ ---------+  7 commits, from 2026-05-28
                                |
                          filter-repo
                                |
                                v
                    page-fetcher (13 commits)
                    oldest: adds fetch-page.py
                    newest: the package as it stands
```

Thirteen commits, twelve of them non-merge. That is the honest ceiling: the
code is roughly two months old and every commit that touched it is here.

**2. The package sits at `pagefetch/`, not at the repository root.**

Tests live inside the package and resolve `import pagefetch` by walking up
from `pagefetch/tests/conftest.py` to the directory above the package and
placing it on `sys.path`. With the package at `pagefetch/`, that directory is
the repository root and the mechanism works unchanged. Flattening the package
contents to the root would have broken every import for no gain.

**3. MIT, copyright Branimir Georgiev.**

`git log` across all three paths shows a single author across twelve
non-merge commits under two email identities, no third-party contributors,
and no vendored code. wuseria is licensed CC BY-NC-ND 4.0, which does not
constrain this: a license is a grant made to recipients, not a restraint on
the copyright holder, so the sole author may publish the same code under MIT.
`Imbra-Ltd` is a GitHub organisation, and organisation membership is not
copyright assignment.

**4. The AGPL question is a dependency question, and belongs in the README.**

`nodriver`, the tier 3 engine, is AGPL-3.0. It does not reach an MIT-licensed
`pagefetch`: it is neither vendored nor bundled, the import is lazy, and the
tier is skipped when the package is absent. It does reach a consumer who
installs that tier and then distributes a network service built on the
combination. That obligation is stated in the README's Dependencies section
rather than left for someone to discover from a transitive install.

**5. wuseria's ADR-035 and ADR-037 stay where they are.**

ADR-035 covers this package *and* the `brandkit` shared library, which is
coupled to wuseria's data files and stays there — so it cannot move as a
whole. ADR-037 (content-based cache validity, no TTL) is purely about
`pagefetch` and could move, but a merged decision record is immutable, and
copying it here would leave two records of one decision free to drift. Both
stay in wuseria; this ADR cites them, and the README links to them.

Their numbers are orphans outside the 001-086 sequence they came from, and
they cross-reference records that do not exist here. That is the cost of
citing rather than copying, and it is the smaller cost.

**6. wuseria keeps its copy for now.**

ADR-035 anticipated wuseria consuming this package as a git submodule. That
swap is not part of this extraction: roughly 28 files under wuseria's
`tools/` import `pagefetch`, and the standalone repository has no CI of its
own yet. Consuming an unverified dependency is worse than holding a copy.
The two copies are identical as of this ADR and will drift; the submodule
decision is tracked separately and should be taken before that drift matters.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| `git subtree split` on `tools/pagefetch/` | Handles a single prefix, so it cannot reach the pre-refactor history. Yields seven commits and a repository that appears to start at the refactor. |
| Fresh repository, no history | Discards the record of why the escalation ladder has the shape it does. The bot-detection patterns and tier ordering were each added against a specific site that defeated the previous version; that is the most valuable thing in the history. |
| Flatten the package to the repository root | Breaks `import pagefetch` for the test suite and every consumer, in exchange for one less directory level. |
| Copy ADR-035 and ADR-037 into this repository | ADR-035 also decides `brandkit`, which stays in wuseria, so it cannot move whole. Copying either creates two records of one decision, free to diverge. |
| Keep the CC BY-NC-ND 4.0 license | Non-commercial and no-derivatives makes the package unusable as a dependency, which defeats the extraction. |
| Swap wuseria to a submodule in the same change | Touches ~28 importing files and the `tools/` pytest suite against a repository with no CI, bundling a migration into an extraction. |

## Consequences

| Consequence | Effect |
| --- | --- |
| The package is independently consumable | Other projects clone or submodule it instead of vendoring a copy. |
| History is preserved across the refactor boundary | `git log --follow` traces a detection pattern back to the script it was first added to. |
| Two copies exist until the submodule decision is taken | wuseria's `tools/pagefetch/` and this repository will drift. Whichever is fixed first, the other is stale. |
| Cross-repository ADR citations | ADR-035 and ADR-037 are reachable only as links to a public repository. If wuseria ever goes private or is restructured, those links break. |
| No CI yet | The suite passes from a clean clone, but nothing enforces that on a pull request. Lint, type check, coverage, and a CI workflow are the next piece of work. |
| An AGPL dependency in the optional set | Documented rather than removed. A consumer distributing a service on tier 3 inherits an obligation this project's license does not create. |
