# ADR-016: Gate the comment-layout convention

**Status:** Accepted
**Date:** 2026-08-05

## Context

`templates/base/core/quality.md` states three comment-layout rules as
MUSTs: a block comment sits directly above the item it documents, never
trailing to the right of code and never separated from it by a blank line;
each comment-plus-item group is separated from the next by one blank line;
comment prose wraps to the line-length limit. CLAUDE.md §2.3 restates them.

Unlike the neighbouring rule about ticket numbers in comments — which
`quality.md` tells projects to "enforce with a test that greps" — these
three name no enforcement mechanism at all. In this repository that meant
review, and review had been passing them since the first commit.

The gap surfaced from a reader, not a tool. One site in
`examples/cache_lifecycle.py` had a comment about the cache key scheme
sitting above the two `write` calls, with a second comment jammed against
the code below it and no blank line between the groups — eleven lines that
read as one block, with each comment describing code it was not above.

A sweep of all four Python roots found 25 more:

```text
  22  comment block with code directly above it, no blank line
   4  aside to the right of code, not a tool directive
  --
  26  across tests/ (15), src/ (10), examples/ (1 — the site above)
```

No ruff rule covers any of it. `E501` covers the third rule — it measures
comment lines like any other — which leaves the two structural ones
unenforced and unenforceable by the existing toolchain.

## Decision

**1. The convention is gated, not reviewed.**

`tools/check_comment_layout.py`, wired into both enforcement layers: a
`repo: local` pre-commit hook, and a step in the `Lint and format` job that
`Gate` already depends on. The script is standard library only, so the CI
step needs nothing installed beyond the runner's Python.

The hook is `language: python` and not `language: system`, which the script
would otherwise justify. `system` resolves `python` from `PATH`, and the
documented development platform is Windows, where every command in the
README uses the `py` launcher and `PATH` has no `python` on it at all. The
hook failed on the machine it was written on. Letting pre-commit supply the
interpreter costs one cached virtualenv and works on both platforms.

The suite runs it too. `test_the_repository_conforms` walks the same four
roots, so a contributor who has not run `pre-commit install` still sees the
failure locally rather than in CI.

**2. It checks two rules, not three.**

Width is `E501`'s job and is left there. A second implementation would
report every long comment twice and drift the moment `line-length` moved.
The module docstring says so, because "the checker does not check the third
rule" is exactly the kind of omission a later reader reads as a bug.

**3. Five carve-outs, four of which are not exceptions.**

The rule as written assumes a comment always has a preceding sibling to be
separated from. Four times it does not, and one of those is a direct
contradiction with another tool:

| Carve-out | Why the rule cannot apply |
| -- | -- |
| Comment opening a block, or indented past the line above | No preceding sibling — the construct starts here |
| Comment under a docstring | `D202` forbids the blank line outright. Enforcing both is impossible |
| Comment on `elif` / `else` / `except` / `finally` / `case` | The clause belongs to the construct above. Obeying the rule blank-lines one branch of a chain and not the others |
| Comment inside brackets | `ruff format` strips blank lines inside collection literals |
| `# ---` section banner | A divider, not a comment on the line below. The blank line under it is the point |

The bracket case is the load-bearing one, and it was found the expensive
way: the first mechanical pass inserted three blank lines into
`detection.py`'s pattern list, and `ruff format --check` deleted them
again. A style rule the formatter undoes is not a rule, it is a loop. The
same pass put a blank line before a commented `elif` in `cache.py` while
the `else` below kept none, which is how the continuation case was found.

**4. Value tables keep their trailing comments, by shape and not by path.**

Ten sites — the `ContentMode` and `Transport` members, `tier_used`, and
three entries in the bot-detection pattern list — annotate a value with a
short note on the same line:

```text
  AUTO = "auto"      # http, escalating through the browser tiers as needed
  HTTP = "http"      # force a plain HTTP request, no browser
  JS = "js"          # force a browser that renders JavaScript
```

Moving those above their values turns five lines into fourteen and turns a
table a reader scans into a list they have to reassemble. This is the one
carve-out that is a preference rather than an impossibility, and it is
recorded as such.

It is recognised by shape — a constant assignment, an annotated field, or a
literal collection element — rather than by an allowlist of paths. A path
allowlist would exempt the files rather than the construct, and would go on
exempting them after the construct was gone. The four asides that were
fixed sit on `if` and `assert` lines, which no shape rule would ever admit.

## Alternatives considered

| Alternative | Why rejected |
| -- | -- |
| A ruff rule | None exists for either structural rule. Adding one means a Rust plugin against a linter with no plugin API — a fork of ruff to enforce a blank line. |
| Leave it to review | That is the status quo under test, and it produced 26 sites over the life of the repository. The one that was noticed was noticed by a person reading an example, not by the process meant to catch it. |
| Convert the value tables as well | Considered and deferred. It is a defensible change and a large one, and it is not what the sweep was for; the shape carve-out is the single place to delete if it is ever taken. |
| Path-based allowlist for the value tables | Exempts `source.py` and `detection.py` wholesale, including future comments that have nothing to do with a value table. The same objection ADR-015 raised against a path-scoped gitleaks allowlist. |
| A `# noqa`-style per-line opt-out | A style gate with an escape hatch on every line is a suggestion with extra steps. The five carve-outs are stated once, in code, and tested. |
| Glob the roots instead of listing them | A new top-level directory would be silently unchecked. Listing them makes it a two-line deliberate act, in the hook and the CI step. |

## Consequences

| Consequence | Detail |
| -- | -- |
| 26 sites changed, no behaviour did | 22 blank lines and 4 comments moved above their code. The suite is the proof: 354 pass, coverage unchanged at 79.84% against the 76% floor. |
| `tools/` is a fourth Python root | `mypy` gains it in `files`, plus `mypy_path` so the suite can import it; `pytest` gains `pythonpath`. The README's structure table lists it. |
| The four asides say more than they did | `# playwright NOT called` became two lines explaining that Playwright is skipped rather than tried and failed. A trailing aside has room for a fragment; a block comment has room for the reason. |
| The ten value-table sites remain | They are conforming under the shape rule, not exempted in spite of it. Deleting `VALUE_TABLE` is the whole change if that is ever revisited. |
| A new top-level directory is unchecked until added | Deliberate, per the alternatives above. Two places: the hook's `args` and the CI step. |
| The checker is subject to its own rule | `tools/` is in the roots it is run against, and the suite checks it like everything else. |

**Upstream:** a candidate, not yet filed. `quality.md` states all three rules
as MUSTs and names an enforcement mechanism for its neighbouring
ticket-number rule but none for these. This repository's experience is the
argument: unenforced, they accumulated 26 violations while every other
quality gate stayed green. The carve-out table above is the part worth
proposing, because a project that adopts the rule without it will fight its
own formatter on the first collection literal it annotates.

## Related

- [ADR-002](002-python-toolchain-and-ci.md) — the three-layer gate this
  adds to, and the `Gate` check that covers it
- [ADR-015](015-examples-that-cannot-fetch.md) — the `examples/` root now
  also under this check, and the argument against path-scoped allowlists
- [ADR-010](010-move-the-package-to-a-src-layout.md) — the root layout the
  checker walks
