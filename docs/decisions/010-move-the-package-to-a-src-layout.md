# ADR-010: Move the package to a src/ layout

**Status:** Accepted
**Date:** 2026-08-02

## Context

`templates/stack/python-lib.md` (`[ID: python-lib-structure]`) prescribes
`src/[package]/` with `tests/` alongside it, and names the reason: a source
layout "prevents accidental imports of the uninstalled package". This
repository does not follow it. CLAUDE.md §1.2 recorded the deviation:

> The package layout is flat, not `src/` — deviation from `python-lib.md`,
> kept because the package predates this repository and the key scheme in
> `cache.py` is path-independent

Neither clause is a reason to stay. The first is history. The second says
moving is *safe*, which is an argument for the move rather than against it.

Spike #83 measured what the deviation actually costs, against a throwaway
copy of `HEAD` rather than by reading:

- **The suite has never tested an installed package.** `pagefetch` is not
  installed in this development checkout — `pip show pagefetch` reports
  nothing — and all 304 tests pass anyway. Every green run in this clone
  has exercised the working directory.
- **Installing does not fix it.** A clean virtualenv with the wheel
  correctly installed still resolves the checkout when the working
  directory is the repository root, which is where CI's
  `pip install -e ".[dev]"` and every documented command run from.
- **Nothing is broken today.** The wheel is correct — eight modules, tests
  excluded, entry point present, `pagefetch --help` works from a neutral
  cwd. The risk is latent, not realised.
- **The move is measurement-neutral.** Tests, coverage, statement counts,
  ruff's file count and mypy's source count are identical before and
  after, and the wheel built from either layout has identical contents.

So the deviation costs one thing: the gate cannot see the difference
between code that ships and code that merely sits in the working
directory. It has not yet been charged for that, which is a statement
about luck rather than about design.

## Decision

**1. The package moves to `src/pagefetch/`, and the suite to `tests/`.**

Two moves rather than one, and both happen — leaving the suite inside the
package would keep the hand-written `exclude = ["pagefetch.tests*"]` that
exists only because tests are packaged-adjacent.

```
  today                          decided
  .                              .
  +-- pagefetch/                 +-- src/
  |   +-- __init__.py            |   +-- pagefetch/
  |   +-- network.py             |       +-- __init__.py
  |   +-- ...                    |       +-- network.py
  |   +-- tests/                 |       +-- ...
  +-- pyproject.toml             +-- tests/
                                 +-- pyproject.toml

  import pagefetch resolves to:

  flat     cwd = repo root  --> ./pagefetch/         (never installed)
           cwd = elsewhere   --> site-packages/
  src/     cwd = repo root  --> site-packages/        (or the editable
           cwd = elsewhere   --> site-packages/        finder; never cwd)
```

The point is the bottom row: under `src/`, the working directory stops
being an answer to `import pagefetch`. With nothing installed the suite
fails to collect — `ModuleNotFoundError: No module named 'pagefetch'` —
instead of passing against source that was never packaged.

**2. The `cache.py` half of the deviation note is retired, not relocated.**

Path-independence of the cache key scheme is a fact about `cache.py`, and
CLAUDE.md §2.6 already states it. It was doing duty in §1.2 as a reason to
stay, which it never was.

**3. This ADR decides; #71 executes.**

`base/core/docs.md` requires the ADR at the moment of the decision, before
the files move. The mechanical work — seven `pyproject.toml` settings and
14 documentation references — stays in #71, with the spike's verified
config table as its checklist.

## Alternatives considered

| Alternative | Why rejected |
| -- | -- |
| Keep the flat layout, record the reasoning properly | There is no reasoning to record. The spike went looking for a cost to moving and the measurements found none, which leaves the deviation resting on the package's age. |
| Move the package, leave the suite at `pagefetch/tests/` | Halves the benefit and keeps the `pagefetch.tests*` exclude. The exclude exists solely because the suite sits inside the distributed package; moving one without the other preserves the thing that made it necessary. |
| Keep the layout; add a CI job that installs the wheel and imports it from a neutral directory | The strongest alternative, and genuinely catches finding 1. Rejected because it detects the failure instead of preventing it: local runs stay shadowed, so a contributor still sees green against unpackaged source and learns about it from CI. A layout that cannot express the bug beats a job that reports it. |
| Document "run pytest from outside the repository" | Unenforceable, and contradicted by every command in CLAUDE.md §1.3 and the README. A convention that the project's own documented workflow violates is not a control. |

## Consequences

| Consequence | Detail |
| -- | -- |
| A working checkout now requires an install | `py -m pip install -e ".[dev]"` stops being setup advice and becomes a precondition — CLAUDE.md §1.3 already leads with it, and the suite now enforces it. |
| The failure mode changes shape | A module missing from `packages.find` becomes a collection error rather than a green run and a broken wheel. |
| The coverage floor is unaffected | The measured figure is unchanged at 79.37% against the 76% floor, so ADR-002's ratchet neither moves nor needs to. |
| One `pyproject.toml` exclude disappears | `coverage.omit` and the `packages.find` tests exclude both stop being needed; `coverage.source` and CI's `--cov=pagefetch` are unchanged, resolving by import name. |
| CLAUDE.md §1.2 loses its deviation note | The chain's structure rule applies unqualified once #71 lands. |
| The repository stops deviating on structure | `[ID: python-lib-structure]` also prescribes `examples/`, which #78 tracks separately and this ADR does not decide. |

**Upstream:** none. This adopts a rule the template chain already carries;
what was missing was this project obeying it. The template's demand for
scanned-file counts compared before and after was the check that made the
move verifiable rather than hopeful, and it worked as written.

## Related

- [ADR-004](004-adopt-solid-ai-templates.md) — the chain this deviation was
  recorded against
- [ADR-002](002-python-toolchain-and-ci.md) — the coverage ratchet the move
  leaves untouched
