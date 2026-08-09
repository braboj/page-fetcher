from pathlib import Path
from textwrap import dedent

import pytest
from check_code_citations import _scannable_files, check

REPO_ROOT = Path(__file__).resolve().parent.parent

# The same roots the hook and the CI step pass. Listed rather than derived
# so that a root added to one and forgotten in the others fails here.
ROOTS = (
    "src",
    "tests",
    "examples",
    "tools",
    ".github",
    "pyproject.toml",
    ".pre-commit-config.yaml",
)


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


CONFIG = [
    pytest.param("ci.yml", "steps:\n  # per ADR-002\n", "RECORD", id="yaml"),
    pytest.param("p.toml", "# raised when #4 landed\nx = 1\n", "ISSUE", id="toml"),
    pytest.param("s.cfg", "# see #9\n[x]\n", "ISSUE", id="cfg"),
]


@pytest.mark.parametrize(("name", "source", "expected"), CONFIG)
def test_a_citation_in_commented_configuration_is_reported(
    tmp_path, name, source, expected
):
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    assert [code for _, code, _ in check(path)] == [expected]


def test_a_hash_inside_a_quoted_config_value_is_not_a_comment(tmp_path):
    # A `#` inside a quote is data, not a comment opener. Reading the line
    # naively would report the value and there would be nothing to fix.
    path = tmp_path / "ci.yml"
    path.write_text('key: "a literal #42 inside a value"\n', encoding="utf-8")
    assert check(path) == []


def test_a_trailing_config_comment_is_read_past_its_value(tmp_path):
    path = tmp_path / "ci.yml"
    path.write_text('key: "value"  # narrowed by #42\n', encoding="utf-8")
    assert [code for _, code, _ in check(path)] == ["ISSUE"]


def test_every_citation_on_a_line_is_reported(tmp_path):
    # A line naming two issues at once must report twice, or the count
    # undersells what is left to fix.
    path = tmp_path / "p.toml"
    path.write_text("# raised when #4 and #5 landed\n", encoding="utf-8")
    assert [code for _, code, _ in check(path)] == ["ISSUE", "ISSUE"]


def test_the_repository_carries_no_citations():
    found = [
        f"{path.relative_to(REPO_ROOT).as_posix()}:{row}: {code}: {text}"
        for root in ROOTS
        for path in _scannable_files(REPO_ROOT / root)
        for row, code, text in check(path)
    ]
    assert found == []


def test_the_commented_configuration_is_actually_reached():
    # The assertion above passes whether the config roots are scanned or
    # silently skipped, so the file list is checked against what the roots
    # are supposed to cover.
    scanned = {
        path.relative_to(REPO_ROOT).as_posix()
        for root in ROOTS
        for path in _scannable_files(REPO_ROOT / root)
    }
    assert "pyproject.toml" in scanned
    assert ".pre-commit-config.yaml" in scanned
    assert ".github/workflows/ci.yml" in scanned
