# ADR-015: Examples that cannot fetch

**Status:** Accepted
**Date:** 2026-08-04

## Context

`templates/stack/python-lib.md` (`[ID: python-lib-structure]`) prescribes
an `examples/` directory: runnable, maintained usage patterns, one file per
pattern, smoke-tested in CI so they cannot rot, excluded from the wheel like
`tests/`. `templates/base/core/readme.md` adds the index — each example
paired with the exact command and the output it produces, real and never
fabricated, running offline against data the project already bundles.

ADR-010 adopted the rest of that structure rule and closed noting this part
was left: "`[ID: python-lib-structure]` also prescribes `examples/`, which
#78 tracks separately and this ADR does not decide."

The requirement collides with what this package is. Every rule above is
satisfiable by a library that computes; this one fetches web pages. An
example that demonstrates the package doing its job needs a network, and
the moment it has one it is neither offline nor reproducible — the output
in the index becomes a claim about what a remote server returned on the day
it was written.

The suite already solved this problem once, by stubbing the four tier
methods, and `FakeFetcher` exists as a `PageSource` that needs no network
at all. What was undecided is whether examples may reach for the real
fetcher when the fake would be less convincing.

## Decision

**1. No example constructs a `NetworkFetcher`.**

Not "examples should avoid the network" — the fetcher itself is out of
bounds, because that is the line a reader can check and CI can enforce.
The examples drive `FakeFetcher`, `FileCache` and the pure predicates
against canned bodies and the captured page already in `tests/fixtures/`.

```
  what an example may use          what it may not
  ------------------------         ---------------
  FakeFetcher                      NetworkFetcher
  FileCache (temp dir)             any live URL
  detection predicates             any browser tier
  tests/fixtures/*.html
```

The weaker rule fails in a way the stronger one cannot: "avoid the network"
invites an example that constructs the real fetcher and forces `HTTP`
transport against a URL that "obviously" resolves, which is offline until
the day it is not.

**2. The smoke job installs without the dev extra, and globs.**

A separate `Examples` job, `pip install -e .` and nothing more. Reusing the
test job would have been one line, and would have proved only that the
examples run beside pytest — which no reader has. Globbing `examples/*.py`
rather than listing files means a new example is covered without editing
CI, so the file someone forgot to register is not the file that stops being
checked.

**3. The index carries real output, and the label is chosen to survive the
secret scanner.**

The cache example first printed `key: 1002e41fbd8c1d1a.txt`. The stem is
`sha256(url)` truncated — public and reproducible by anyone who runs the
example — but a keyword followed by a 16-hex token is gitleaks'
`generic-api-key` shape, and the secret scan failed on a documentation file
containing no secret. The label changed to `entry:`; the scanner did not.

An allowlist would have been the faster fix and is the wrong one twice
over: a fingerprint-scoped entry dies at squash-merge and leaves dead
config behind, and a path-scoped entry permanently exempts the one file in
the repository whose contents are pasted program output.

**4. Nothing is excluded from the wheel, because nothing needs to be.**

#78 scoped "a wheel exclusion alongside the existing
`exclude = ["pagefetch.tests*"]`". That exclude no longer exists — ADR-010
retired it — and under `src/` an `examples/` directory at the repository
root cannot reach the wheel, the same way `tests/` cannot. Verified by
building the wheel and listing it: eight modules and `dist-info`, nothing
else.

## Alternatives considered

| Alternative | Why rejected |
| -- | -- |
| Drive `NetworkFetcher` against `tests/fixtures/` over `file://` | The scheme allowlist rejects `file://` at every entry point, and ADR-003 put it there deliberately. An example whose first act is to defeat a security control teaches the wrong thing twice. |
| One example that fetches a live URL, marked "needs network" | The index would carry output that is real on the day of writing and a lie afterwards. `readme.md` allows a dry run where the true output needs something the reader lacks; it does not allow output that silently expires. |
| Reuse the `test` job for the smoke run | One line cheaper, and it proves the wrong claim — that examples work alongside pytest and the linters. The reader has the package and nothing else. |
| Fewer examples, one per README feature | The features are not the seams. Batch results and `FetchResult` reading are one file because a batch returns a list of results; cache keys and the junk sweep are one file because the sweep only means something once entries exist. |
| Allowlist the gitleaks finding | Weakens a scanner over a documentation path to accommodate output that only looked like a credential, and leaves config that outlives the commit it names. |

## Consequences

| Consequence | Detail |
| -- | -- |
| The examples cannot demonstrate escalation | The ladder is what the package is for, and no example shows it running. `docs/ARCHITECTURE.md` and the README's Usage section carry it instead. This is the price of the offline rule, paid knowingly. |
| A fifth example inherits the constraint | CLAUDE.md §1.2 states it, and CI enforces it — an example that fetches fails the gate rather than the reader. |
| `mypy` gains a third root | `files = ["src", "tests", "examples"]`. An example that no longer type-checks is a published mistake, and the pre-commit hook mirrors the list already. |
| One ruff exemption | `S101` for `examples/**`. The `FakeFetcher` example is a consumer's test pattern made executable; printing PASS/FAIL instead of asserting would demonstrate a way nobody writes tests. |
| The coverage floor is unaffected | `coverage.source` resolves by import name, so `examples/` is outside the denominator. The measured figure is unchanged at 79.84% against the 76% floor. |
| The structure deviation from `python-lib.md` closes | ADR-010 left this one part open. Nothing in `[ID: python-lib-structure]` is now unimplemented. |

**Upstream:** two candidates, both filed.
[solid-ai-templates#987](https://github.com/braboj/solid-ai-templates/issues/987)
for `base/core/readme.md` — the examples index is the one document whose
content is machine-generated prose, so the rule that mandates real output
should say that the output is read by the secret scanner, and that the
label is what gives way. #987 also carries the second-order point that the
scanner reads commit history rather than the working tree, so a follow-up
fix does not clear the check.
[solid-ai-templates#988](https://github.com/braboj/solid-ai-templates/issues/988)
for `stack/python-lib.md` — "smoke-tested in CI" does not say how the
package is installed for that job, and installing as a consumer does is
what makes the test mean anything.

Decision 1 is project-specific: it names `NetworkFetcher`, and a library
that does not fetch has nothing to ban.

## Related

- [ADR-010](010-move-the-package-to-a-src-layout.md) — adopted the rest of
  `[ID: python-lib-structure]` and deferred this part
- [ADR-003](003-url-scheme-allowlist.md) — the allowlist that rules out the
  `file://` alternative
- [ADR-002](002-python-toolchain-and-ci.md) — the gate this adds a job to
