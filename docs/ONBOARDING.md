# Onboarding

Everything needed to go from a fresh clone to a passing gate. Daily
workflows live in [PLAYBOOK.md](PLAYBOOK.md) — this document covers the
first hour only.

## 1. Prerequisites

| Tool           | Version | Notes                                            |
| -------------- | ------- | ------------------------------------------------ |
| Python         | 3.10+   | 3.10 and 3.13 are the versions CI runs           |
| git            | any     | with submodule support                           |
| GitHub CLI     | any     | `gh` — the PR and issue commands in the playbook |
| Chrome         | current | only for the browser tiers; not needed for tests |
| draw.io        | desktop | only to change a diagram; see PLAYBOOK 4.7       |

No database, broker, or other service is required. Tier 1 runs on the
standard library alone, and the test suite needs neither network nor
browser. Nothing in the gate needs draw.io — it is here because a chapter
diagram cannot be re-exported without it.

On Windows, `py` is the launcher used throughout the docs. On Linux and
macOS substitute `python3`.

## 2. First-time setup

```bash
git clone --recurse-submodules https://github.com/braboj/page-fetcher.git
cd page-fetcher
py -m pip install -e ".[dev]"
pre-commit install
git config fetch.prune true
```

The editable install is a precondition, not a convenience. The package
lives in `src/`, so a checkout with nothing installed cannot import it and
the suite fails to collect with `ModuleNotFoundError: No module named
'pagefetch'`. That is the layout doing its job — it is what stops tests
passing against source that was never packaged (ADR-010).

`fetch.prune` matters here because the repository deletes head branches on
merge. Without it, `origin/<branch>` outlives the branch it points at and
reads as a branch that refuses to delete.

If you cloned without `--recurse-submodules`:

```bash
git submodule update --init
```

The submodule at `docs/solid-ai-templates` holds the shared template
system — the review, audit and documentation rules this project follows.
Nothing in the package imports it, so a checkout without it still builds
and tests.

No editor is required, but `.vscode/settings.json` and
`.vscode/extensions.json` are tracked, so VS Code will offer to install
the three extensions that surface the gates as you type — Python, Ruff
and Mypy Type Checker. Accept them. The settings turn Pylance's type
evaluation off on purpose: mypy is the type checker the gate runs, and
two checkers at two strictnesses means the editor flags errors CI
accepts. Completion, hover and rename are unaffected.

## 3. Verify the setup

Run the gate. All five should pass on a clean checkout:

```bash
py -m ruff check .          # -> All checks passed!
py -m ruff format --check . # -> N files already formatted
py -m mypy                  # -> Success: no issues found in N source files
py tools/check_comment_layout.py src tests examples tools  # -> no output
py -m pytest --cov=pagefetch
```

The layout check prints nothing when it passes, which is the whole of its
output contract — anything on stdout is a violation with its file, line and
rule. The suite runs it a second time, so a checkout without
`pre-commit install` still fails locally rather than in CI.

The test run ends with the suite count and the coverage verdict, in this
shape:

```text
N passed in <a couple of seconds>
Required test coverage of <floor>% reached. Total coverage: <measured>%
```

What matters is that nothing failed and coverage *reached* the floor —
the floor is a ratchet that moves, so the numbers here would go stale if
they were pinned. `pyproject.toml` holds the current one.

Then run an example. None of them touches the network, so a clean run
confirms the install resolves the package and nothing else:

```bash
py examples/fake_fetcher.py
```

`examples/README.md` pairs each one with the output it produces, so a
difference is visible rather than something to judge. CI runs every file
in that directory against an install with no dev extra.

Then fetch a real page to confirm tier 1 works end to end:

```bash
py -m pagefetch https://en.wikipedia.org/wiki/Web_scraping
```

That prints roughly 30 KB of page text to stdout and says nothing on
stderr — a silent stderr means tier 1 handled it without escalating.

To exercise the browser tiers, add the optional engines. They are not
needed for any test:

```bash
py -m pip install -e ".[browsers]"
playwright install chromium
```

## 4. Key files

Read these in order. The README's "Project structure" section lists the
rest.

| File                         | Why it matters                                       |
| ---------------------------- | ---------------------------------------------------- |
| `README.md`                  | What the package does and how to run it              |
| `examples/README.md`         | Runnable patterns paired with their real output      |
| `CLAUDE.md`                  | The rules this project holds contributors to         |
| `docs/arc42/`                | How the ladder, detection and the cache work         |
| `src/pagefetch/source.py`    | The `PageSource` contract everything else implements |
| `src/pagefetch/network.py`   | The four tiers and the escalation orchestrator       |
| `src/pagefetch/detection.py` | The predicates that decide when to escalate          |
| `docs/decisions/`            | Why the boundaries are where they are                |

## 5. Project context

`pagefetch` fetches a web page by the cheapest means that works. It starts
with plain HTTP, inspects the response, and escalates through headless and
headed browsers only when what came back is a bot wall, an error page, or
implausibly short.

Two constraints shape almost every decision:

- **Tier 1 is standard library only.** The package installs with no
  dependencies at all. Browser libraries are optional extras, imported
  lazily inside the tier that uses them.
- **A wrong escalation decision is silent.** Classifying a real page as
  junk loses it with no error a caller can act on, so the detection
  predicates are held to a higher bar than their size suggests. See
  `docs/audits/2026-07-30-360.md` for what that failure looks like in
  practice.

Start with [ADR-001](decisions/001-extract-pagefetch-into-standalone-repo.md)
for how the package came to be standalone, and
[ADR-003](decisions/003-url-scheme-allowlist.md) for the clearest example
of the project's approach to drawing a boundary and saying what it does not
cover.

## 6. Daily workflow

See [PLAYBOOK.md](PLAYBOOK.md) — section 1 for git and issues, section 3
for the quality checks, section 4 for maintenance.
