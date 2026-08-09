from pathlib import Path
from textwrap import dedent

import pytest
from check_code_citations import check

REPO_ROOT = Path(__file__).resolve().parent.parent

ROOTS = ("src", "tests", "examples", "tools")


def codes(tmp_path: Path, source: str) -> list[str]:
    """Return the violation codes the checker reports for one module."""
    path = tmp_path / "module.py"
    path.write_text(dedent(source).lstrip("\n"), encoding="utf-8")
    return [code for _, code, _ in check(path)]


VIOLATIONS = [
    pytest.param("# see #123 for the reasoning\nX = 1\n", "ISSUE", id="in-a-comment"),
    pytest.param('"""Do a thing, per #123."""\n', "ISSUE", id="in-a-module-docstring"),
    pytest.param(
        'def f():\n    """Do a thing.\n\n    Superseded by #7.\n    """\n',
        "ISSUE",
        id="in-a-function-docstring",
    ),
    pytest.param(
        'class C:\n    """A thing, narrowed by #7."""\n',
        "ISSUE",
        id="in-a-class-docstring",
    ),
    pytest.param("# per ADR-002, it stays\nX = 1\n", "RECORD", id="record-hyphenated"),
    pytest.param("# per ADR 002, it stays\nX = 1\n", "RECORD", id="record-spaced"),
    pytest.param("# per ADR0002, it stays\nX = 1\n", "RECORD", id="record-bare"),
    pytest.param("X = 1  # narrowed by #4\n", "ISSUE", id="trailing-comment"),
]


@pytest.mark.parametrize(("source", "expected"), VIOLATIONS)
def test_each_citation_is_reported(tmp_path, source, expected):
    assert codes(tmp_path, source) == [expected]


ACCEPTED = [
    pytest.param(
        "# the descriptor is named, not the thread that chose it\nX = 1\n",
        id="substance-instead-of-a-number",
    ),
    pytest.param(
        "# Rappe 1992, UFF: parameters come from the published table\nX = 1\n",
        id="a-named-source-ages-gracefully",
    ),
    pytest.param(
        'X = "see #123"\nY = """a docstring-shaped string, per ADR-002"""\n',
        id="a-string-literal-is-not-a-comment",
    ),
    pytest.param(
        "# noqa and nosec carry no number\nX = 1  # noqa: S314\n",
        id="tool-directives",
    ),
    pytest.param(
        "# the colour is #ff00ff and the anchor is #top\nX = 1\n",
        id="a-hash-without-digits",
    ),
]


@pytest.mark.parametrize("source", ACCEPTED)
def test_conforming_code_stays_silent(tmp_path, source):
    assert codes(tmp_path, source) == []


def lines(tmp_path: Path, source: str) -> list[int]:
    """Return the lines the checker reports for one module."""
    path = tmp_path / "module.py"
    path.write_text(dedent(source).lstrip("\n"), encoding="utf-8")
    return [row for row, _, _ in check(path)]


def test_a_citation_is_reported_on_its_own_line(tmp_path):
    # A docstring is one token, so the line it opens on is the naive
    # answer for everything inside it. Every citation in a long module
    # docstring would then report as line 1 and none could be found.
    source = '''
    """Summary.

    Filler.

    Narrowed by #7.
    """
    '''
    assert lines(tmp_path, source) == [5]


def test_both_codes_are_reported_from_one_file(tmp_path):
    source = """
    # opened by #7
    X = 1

    # per ADR-002
    Y = 2
    """
    assert codes(tmp_path, source) == ["ISSUE", "RECORD"]


def test_the_repository_carries_no_citations():
    found = [
        f"{path.relative_to(REPO_ROOT).as_posix()}:{row}: {code}: {text}"
        for root in ROOTS
        for path in sorted((REPO_ROOT / root).rglob("*.py"))
        for row, code, text in check(path)
    ]
    assert found == []
