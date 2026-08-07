from pathlib import Path
from textwrap import dedent

import pytest
from check_journal_order import check

REPO_ROOT = Path(__file__).resolve().parent.parent

JOURNAL = REPO_ROOT / "docs" / "dev-journal.md"


def codes(tmp_path: Path, source: str) -> list[str]:
    """Return the violation codes the checker reports for a journal."""
    path = tmp_path / "journal.md"
    path.write_text(dedent(source).lstrip("\n"), encoding="utf-8")
    return [code for _, code, _ in check(path)]


VIOLATIONS = [
    pytest.param(
        """
        ## 2026-08-07 — The newer one

        ## 2026-08-06 — The older one
        """,
        "ORDER",
        id="newest-first-pair",
    ),
    pytest.param(
        """
        ## 2026-08-06 — The older one

        ## 2026-08-06 (second session) — Same day

        ## 2026-08-05 — A day earlier
        """,
        "ORDER",
        id="entry-out-of-place-after-a-same-day-run",
    ),
    pytest.param(
        """
        ## Architecture overview

        ## 2026-08-06 — A session
        """,
        "UNDATED",
        id="heading-without-a-date",
    ),
]


@pytest.mark.parametrize(("source", "expected"), VIOLATIONS)
def test_each_rule_fires(tmp_path, source, expected):
    assert codes(tmp_path, source) == [expected]


ACCEPTED = [
    pytest.param(
        """
        ## 2026-08-05 — The oldest

        ## 2026-08-06 — The middle

        ## 2026-08-07 — The newest
        """,
        id="ascending-dates",
    ),
    pytest.param(
        """
        ## 2026-08-02 — First of the day

        ## 2026-08-02 (second session) — Second of the day

        ## 2026-08-02 (third session) — Third of the day
        """,
        id="several-sessions-sharing-a-date",
    ),
    pytest.param(
        """
        ## 2026-05-20 to 2026-05-30 — Upstream history

        ## 2026-07-26 — The first session here
        """,
        id="leading-date-range-keyed-on-its-start",
    ),
]


@pytest.mark.parametrize("source", ACCEPTED)
def test_conforming_journals_stay_silent(tmp_path, source):
    assert codes(tmp_path, source) == []


def test_a_heading_inside_a_fence_is_not_an_entry(tmp_path):
    source = """
    ## 2026-08-06 — A session

    ```bash
    ## 2026-01-01 — not a heading, a shell comment
    git log --oneline
    ```

    ## 2026-08-07 — The next session
    """
    assert codes(tmp_path, source) == []


def test_an_unclosed_fence_does_not_swallow_the_rest(tmp_path):
    # Every entry after an unbalanced fence would go unchecked, which is
    # the silent failure this checker exists to prevent. The toggle leaves
    # them inside the fence, so the ORDER below is still reported.
    source = """
    ```bash
    git log --oneline
    ```

    ## 2026-08-07 — The newer one

    ## 2026-08-06 — The older one
    """
    assert codes(tmp_path, source) == ["ORDER"]


def test_the_journal_conforms():
    found = [
        f"{JOURNAL.relative_to(REPO_ROOT).as_posix()}:{row}: {code}: {text}"
        for row, code, text in check(JOURNAL)
    ]
    assert found == []
