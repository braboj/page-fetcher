from pathlib import Path
from textwrap import dedent

import pytest
from check_comment_layout import check

REPO_ROOT = Path(__file__).resolve().parent.parent

ROOTS = ["src", "tests", "examples", "tools"]


def codes(tmp_path: Path, source: str) -> list[str]:
    """Return the violation codes the checker reports for a snippet."""
    path = tmp_path / "sample.py"
    path.write_text(dedent(source).lstrip("\n"), encoding="utf-8")
    return [code for _, code, _ in check(path)]


VIOLATIONS = [
    pytest.param(
        """
        x = 1
        # A note about y.
        y = 2
        """,
        "GROUP",
        id="comment-block-jammed-against-the-code-above",
    ),
    pytest.param(
        """
        # A note about x.

        x = 1
        """,
        "DETACHED",
        id="comment-block-cut-off-from-its-item",
    ),
    pytest.param(
        """
        if x == 1:  # an aside
            pass
        """,
        "TRAILING",
        id="aside-to-the-right-of-code",
    ),
    pytest.param(
        """
        assert x == 1  # an aside on an assertion is not a value table
        """,
        "TRAILING",
        id="aside-that-only-resembles-a-value-table",
    ),
]


@pytest.mark.parametrize(("source", "expected"), VIOLATIONS)
def test_each_rule_fires(tmp_path, source, expected):
    assert codes(tmp_path, source) == [expected]


# Every carve-out the checker defines. A regression in any of these makes
# the gate argue with the formatter or with ordinary Python, which is the
# way a style check stops being run rather than the way it stops failing.
CARVE_OUTS = [
    pytest.param(
        """
        def f():
            # A note on what f returns.
            return 1
        """,
        id="comment-opening-a-block",
    ),
    pytest.param(
        """
        def f():
            \"\"\"Do a thing.\"\"\"
            # A note that D202 forbids separating from the docstring.
            return 1
        """,
        id="comment-under-a-docstring",
    ),
    pytest.param(
        """
        if a:
            x = 1
        # A note on the other branch.
        else:
            x = 2
        """,
        id="comment-on-a-continuation-clause",
    ),
    pytest.param(
        """
        VALUES = [
            "a",
            # A note on the group below, which the formatter would not let
            # a blank line separate.
            "b",
        ]
        """,
        id="comment-inside-a-collection-literal",
    ),
    pytest.param(
        """
        # --- a section divider ------------------------------------------

        x = 1
        """,
        id="section-banner",
    ),
    pytest.param(
        """
        import os  # noqa: F401
        """,
        id="tool-directive",
    ),
    pytest.param(
        """
        NAME = "value"  # what it means
        COUNT = 3  # how many
        """,
        id="value-table-of-constants",
    ),
    pytest.param(
        """
        field: str  # what it holds
        """,
        id="value-table-of-annotated-fields",
    ),
    pytest.param(
        """
        VALUES = [
            "a",  # the first
            "b",  # the second
        ]
        """,
        id="value-table-of-collection-elements",
    ),
]


@pytest.mark.parametrize("source", CARVE_OUTS)
def test_carve_outs_stay_silent(tmp_path, source):
    assert codes(tmp_path, source) == []


def test_a_hash_inside_a_string_is_not_a_comment(tmp_path):
    source = """
    URL = "https://example.com/#anchor"
    TEXT = "# not a comment"
    """
    assert codes(tmp_path, source) == []


def test_the_repository_conforms():
    found = [
        f"{path.relative_to(REPO_ROOT).as_posix()}:{row}: {code}: {text}"
        for root in ROOTS
        for path in sorted((REPO_ROOT / root).rglob("*.py"))
        for row, code, text in check(path)
    ]
    assert found == []
