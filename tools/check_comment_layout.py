"""Check the comment-layout conventions from CLAUDE.md 2.3.

Three rules, each reported under its own code:

    GROUP     a comment block with code directly above it and no blank line
    DETACHED  a comment block separated from the item it documents
    TRAILING  a comment to the right of code

CLAUDE.md 2.3 states a fourth — comment prose wraps to the line-length
limit — which is not implemented here because ruff's E501 already fails on
it, comments included. A second check would only report it twice.

Run it over the repository's Python roots:

    python tools/check_comment_layout.py src tests examples tools

Comments are found with `tokenize`, so a `#` inside a string literal is
never mistaken for one. The carve-outs below are less exceptions to the
convention than places where it cannot apply: each marks a spot where the
rule would contradict the formatter, another linter rule, or the shape of
the syntax itself. Every one is explained where it is defined.
"""

import re
import sys
import tokenize
from collections.abc import Iterator
from pathlib import Path

# Tool directives address the checker on the line they sit on, so they have
# nowhere else to go. Everything else earns its place above the code.
DIRECTIVES = ("# noqa", "# nosec", "# type:", "# pragma:")

# A comment documenting one of these belongs to the construct already open
# above it. Separating it would put a blank line inside one branch of a
# chain and not the others, which reads worse than the rule it satisfies.
CONTINUATIONS = ("elif ", "else:", "except", "finally:", "case ")

# A divider between sections rather than a comment on the line below it, so
# the blank line under it is the point. network.py is built out of these.
BANNER = "# ---"

_LITERAL = (
    r"""(?:[rbfRBF]{0,2}"[^"]*"|[rbfRBF]{0,2}'[^']*'|-?\d[\d_.]*|True|False|None)"""
)

# A value table is a run of constants or collection elements, each carrying
# a short note. Moving those notes above their values turns a table a reader
# scans into a list they have to assemble, so the trailing form stays.
VALUE_TABLE = re.compile(
    rf"""^(?:\w+\s*=\s*)?{_LITERAL}\s*,?$ | ^\w+\s*:\s*[\w\[\]\s,|.'"]+$""",
    re.VERBOSE,
)


def _comments(path: Path) -> Iterator[tuple[tokenize.TokenInfo, int]]:
    """Yield every comment token in a file with its bracket nesting depth."""
    depth = 0
    with path.open("rb") as handle:
        for token in tokenize.tokenize(handle.readline):
            if token.type == tokenize.OP:
                if token.string in {"(", "[", "{"}:
                    depth += 1
                elif token.string in {")", "]", "}"}:
                    depth -= 1
            elif token.type == tokenize.COMMENT:
                yield token, depth


def _code_below(lines: list[str], row: int) -> str:
    """Return the first line of code under a comment block, stripped."""
    for probe in range(row, len(lines)):
        stripped = lines[probe].strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return ""


def _needs_separating(lines: list[str], row: int) -> bool:
    """Say whether a comment block at `row` must be preceded by a blank line.

    False wherever the comment opens a construct rather than following a
    sibling: the line above ends a block header or a docstring, the comment
    is indented past it, or the comment documents a continuation clause.
    """
    above = lines[row - 2] if row > 1 else ""
    if not above.strip() or above.strip().startswith("#"):
        return False

    comment_indent = len(lines[row - 1]) - len(lines[row - 1].lstrip())
    if comment_indent > len(above) - len(above.lstrip()):
        return False

    if above.rstrip().endswith(":") or above.strip().endswith(('"""', "'''")):
        return False

    return not _code_below(lines, row).startswith(CONTINUATIONS)


def check(path: Path) -> list[tuple[int, str, str]]:
    """Return `(line, code, text)` for every violation in one file."""
    lines = path.read_text(encoding="utf-8").splitlines()
    found: list[tuple[int, str, str]] = []
    blocks: dict[int, int] = {}

    for token, depth in _comments(path):
        row = token.start[0]
        line = lines[row - 1]

        if line[: token.start[1]].strip():
            code = line[: token.start[1]].strip()
            if not token.string.startswith(DIRECTIVES) and not VALUE_TABLE.match(code):
                found.append((row, "TRAILING", line.strip()))
            continue

        blocks[row] = depth

    for row, depth in sorted(blocks.items()):
        line = lines[row - 1]

        # Only the top of a block can be orphaned from the code above it,
        # and only the bottom can be detached from the item below. Inside
        # brackets the formatter owns the blank lines and strips any this
        # rule would ask for, so the two would never agree.
        if row - 1 not in blocks and depth == 0 and _needs_separating(lines, row):
            found.append((row, "GROUP", line.strip()))

        if row + 1 in blocks or line.strip().startswith(BANNER):
            continue

        if row >= len(lines) or lines[row].strip() == "":
            found.append((row, "DETACHED", line.strip()))

    return sorted(found)


def main(argv: list[str]) -> int:
    """Print every violation under the given roots; return an exit code."""
    if not argv:
        print("usage: check_comment_layout.py ROOT [ROOT ...]", file=sys.stderr)
        return 2

    found = 0
    for root in argv:
        for path in sorted(Path(root).rglob("*.py")):
            for row, code, text in check(path):
                print(f"{path.as_posix()}:{row}: {code}: {text}")
                found += 1

    if found:
        print(f"\n{found} comment-layout violation(s). See CLAUDE.md 2.3.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
