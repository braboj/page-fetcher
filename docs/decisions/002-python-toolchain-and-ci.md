# ADR-002: Python toolchain and CI

**Status:** Accepted
**Date:** 2026-07-26

## Context

The package arrived from wuseria (ADR-001) with a passing test suite and
nothing enforcing it. Formatting, typing, and lint were whatever the author
happened to write; a pull request could break any of them silently. ADR-001
recorded "no CI yet" as a known consequence, and it was the main argument for
wuseria keeping its own copy rather than consuming this repository — depending
on something unverified is worse than holding a duplicate.

The package is small (eight modules, ~680 statements) and has no runtime
dependencies at all for tier 1. Whatever gets adopted has to stay proportionate
to that.

## Decision

Adopt ruff, mypy, pytest with coverage, pre-commit, and GitHub Actions, wired
as three layers where each repeats the one before it.

```text
editor            pre-commit (1-5s)         CI (1-3 min)
  |                     |                        |
ruff LSP    ->   ruff check --fix        lint    ruff check + format --check
mypy plugin      ruff format             types   mypy
                 mypy                    test    pytest --cov, py3.10 + 3.13
                 gitleaks                secrets gitleaks
                 file hygiene            sast    CodeQL
                                          |
                                        gate  <- the one required check
```

**1. ruff for both lint and format.**

One tool replaces black, flake8, isort, and most of pylint, with one config
block and no plugin version-matching. The rule set is broad on purpose —
pycodestyle, pyflakes, isort, pyupgrade, bugbear, simplify, bandit,
blind-except, pylint, and ruff's own rules — because the cost of a broad set is
paid once, in per-file ignores, rather than continuously in rules nobody
enabled.

Line length is ruff's default 88. The code was written to roughly that already;
eight files were reformatted on adoption, all of it whitespace.

Worth knowing: `ruff format` also formats Python inside Markdown fences, so the
README's examples are now gated too. That is a feature — a doc example that
does not parse is a bug — but it surprises on first encounter.

**2. Per-file ignores carry their reason, and a pointer when work is deferred.**

Three patterns in this package legitimately trip the broad rule set: the tier
ladder's blind `except Exception` (a browser failure must fall through to the
next tier, not abort), the lazy browser imports (hoisting them would make every
optional dependency mandatory), and `try/except/pass` in teardown (a failure
closing a browser must not mask a fetched result).

Each ignore states why in `pyproject.toml`. Two of them are not justifications
but deferrals, and say so with an issue number: `S310` (the fetcher accepts any
URL scheme, issue #3) and `PLR0912`/`PLR0915` (`_run_batch` is genuinely too
long at 64 statements, issue #4). A suppression without a reason is
indistinguishable from one nobody revisited.

**3. The coverage floor is measured, not aspirational.**

The inherited target was 90%. Actual source coverage is 46.6%, and the gap is
structural rather than neglect: the browser-tier method bodies need a headed
Chrome, so most of `network.py` and `chrome.py` cannot run in CI at all. The
pure logic that *can* be tested — detection, cache, source, fake — already sits
at 94-100%.

`fail_under` is therefore 45: a ratchet floor just under the measured number,
which fails the build on regression and says nothing flattering about the
package. Tests are excluded from the measurement, since counting a suite that
is 100% by construction inflates the headline to 65% and measures nothing.

Raising the floor is issue #4's job, and it has the order right: cover the
batch path first, then refactor it.

**4. CI matrix is the ends of the supported range, not every version.**

Python 3.10 (the `requires-python` floor, which catches newer syntax slipping
in) and 3.13 (which catches deprecations early). The versions between add
runtime and find nothing these two miss.

**5. One aggregating `gate` job is the required status check.**

Branch protection names `gate` and nothing else. Naming each job individually
means a job added later is not required until someone remembers to update the
ruleset — a gate that silently stops gating. `gate` treats anything other than
`success` as failure, so a skipped or cancelled dependency cannot pass by
omission.

**6. Third-party actions are pinned to commit SHAs.**

A tag can be moved to point at different code; a SHA cannot. The readable
version stays in a trailing comment so Dependabot still bumps them.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| black + flake8 + isort + pylint | Four tools, four configs, and plugin-version coupling between them, to do what ruff does in one config block. |
| Default (narrow) ruff rule set | E, F and friends would have missed every finding that mattered here — the unchecked `subprocess.run`, the `contextlib.suppress` candidates, the unguarded URL scheme, and the `None` dereference in the batch loop. |
| Keep the 90% coverage target | It was never reachable: the browser tiers need headed Chrome. A gate that cannot pass gets disabled, and then nothing is gated. |
| Report coverage without failing | The floor is the only thing stopping a slow slide. Warn-only is right for a large legacy codebase; at 680 statements the ratchet costs nothing. |
| Full matrix (3.10 through 3.13) | Two more jobs per run to catch nothing the endpoints miss. |
| Require each CI job in branch protection | A job added later silently is not required. The aggregator makes that impossible to forget. |
| Refactor `_run_batch` now to satisfy PLR0912 | The batch path has zero test coverage; refactoring it here would be unverifiable. Deferred to issue #4, tests first. |
| Restrict URL schemes now to satisfy S310 | A behaviour change does not belong in a PR that sets up tooling. Deferred to issue #3. |
| Tag-pinned actions (`@v5`) | A tag is mutable; SHA-pinning is the standard supply-chain control. |

## Consequences

| Consequence | Effect |
| --- | --- |
| The gate is real | Lint, format, types, tests, coverage, secrets, and SAST all block a merge. The main argument against wuseria consuming this repo as a submodule (Imbra-Ltd/wuseria#1456) is gone. |
| Contributors need `pre-commit install` | One command per clone, documented in the README. Skipping it is survivable — CI repeats everything. |
| Formatting churn landed once | Eight files reformatted on adoption. Subsequent diffs are content-only. |
| README examples are now gated | `ruff format --check` covers fenced Python in Markdown, so a doc example that does not parse fails CI. |
| The coverage number is publicly unflattering | 46.6% is the honest figure for a package whose browser tiers cannot run in CI. Better than a 90% claim that measures a suite against itself. |
| Two lint rules are suppressed with deferred work behind them | Issues #3 and #4. If either is closed without action, the suppression comment becomes stale and should go with it. |
