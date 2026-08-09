"""Check that no code comment or docstring cites an issue, PR or record.

One rule, reported under two codes:

    ISSUE   a `#` followed immediately by digits
    RECORD  an `ADR` followed by digits

Run it over the repository's code roots and its commented configuration:

    python tools/check_code_citations.py src tests examples tools \
        .github pyproject.toml .pre-commit-config.yaml

In Python, comments come from `tokenize` and docstrings from `ast`, so a
citation inside an ordinary string literal is left alone — test data
describing a violation is not one. Configuration is line-based instead: a
`#` outside a quote opens a comment, which handles these files and would
not survive an escaped quote or a block scalar carrying a lone `#`.

Markdown is never scanned: cross-referencing by number is what the README,
the records and the journal are for.

There are no carve-outs. The rule allows naming a durable source — an
author, a year, a method — and neither pattern matches one, so nothing
legitimate needs excusing. A case that proves otherwise should be recorded
before it is added here.
"""

import ast
import re
import sys
import tokenize
from collections.abc import Iterator
from pathlib import Path

# The tracker's vocabulary, not the code's. Both name a conversation that
# has ended, where the code needs the fact that came out of it — and the
# reader who follows the number lands on a dead thread rather than on
# whatever superseded it.
PATTERNS = (
    ("ISSUE", re.compile(r"#\d+")),
    ("RECORD", re.compile(r"ADR[\s-]*\d+")),
)

DOCSTRING_OWNERS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)

# Commented configuration counts as code: a workflow, a hook list and the
# project file all carry reasoning, and a number rots there exactly as it
# does in a module. These are read line by line rather than parsed, which
# is why the set is listed instead of inferred.
CONFIG_SUFFIXES = (".yml", ".yaml", ".toml", ".cfg", ".ini")

SCANNED_SUFFIXES = (".py", *CONFIG_SUFFIXES)


def _comments(path: Path) -> Iterator[tuple[int, str]]:
    """Yield every comment in a file with the line it sits on."""
    with path.open("rb") as handle:
        for token in tokenize.tokenize(handle.readline):
            if token.type == tokenize.COMMENT:
                yield token.start[0], token.string


def _docstrings(path: Path, tree: ast.Module) -> Iterator[tuple[int, str]]:
    """Yield every docstring line in a file with the line it sits on."""
    for node in ast.walk(tree):
        if not isinstance(node, DOCSTRING_OWNERS):
            continue

        # The raw literal rather than the cleaned text: `get_docstring`
        # strips leading blank lines, which would shift every line number
        # after it by however many it removed.
        first = node.body[0] if node.body else None
        if not isinstance(first, ast.Expr):
            continue

        literal = first.value
        if not isinstance(literal, ast.Constant) or not isinstance(literal.value, str):
            continue

        for offset, line in enumerate(literal.value.splitlines()):
            yield literal.lineno + offset, line


def _comment_part(line: str) -> str:
    """Return the comment on one config line, ignoring a quoted `#`."""
    quote = ""

    for index, char in enumerate(line):
        if quote:
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char == "#":
            return line[index:]

    return ""


def _config_comments(path: Path) -> Iterator[tuple[int, str]]:
    """Yield every comment in a line-based config file with its line."""
    lines = path.read_text(encoding="utf-8").splitlines()

    for row, line in enumerate(lines, start=1):
        comment = _comment_part(line)
        if comment:
            yield row, comment


def _lines(path: Path) -> Iterator[tuple[int, str]]:
    """Yield every comment or docstring line in one scannable file."""
    if path.suffix in CONFIG_SUFFIXES:
        yield from _config_comments(path)
        return

    tree = ast.parse(path.read_text(encoding="utf-8"))
    yield from _comments(path)
    yield from _docstrings(path, tree)


def check(path: Path) -> list[tuple[int, str, str]]:
    """Return `(line, code, text)` for every citation in one file."""
    found: list[tuple[int, str, str]] = []

    # Every match rather than the first: a line naming two issues in one
    # parenthesis would otherwise report once, and a count that undersells
    # the work left is the one thing a gate must not do.
    for row, text in _lines(path):
        for code, pattern in PATTERNS:
            for match in pattern.finditer(text):
                found.append((row, code, f"{match.group()}  in: {text.strip()}"))

    return sorted(found)


def _scannable_files(root: Path) -> Iterator[Path]:
    """Yield every file under one root this can read, in a stable order."""
    if root.is_file():
        yield root
        return

    yield from sorted(
        path for suffix in SCANNED_SUFFIXES for path in root.rglob(f"*{suffix}")
    )


def main(argv: list[str]) -> int:
    """Print every citation in the given roots; return an exit code."""
    if not argv:
        print("usage: check_code_citations.py ROOT [ROOT ...]", file=sys.stderr)
        return 2

    found = 0
    for name in argv:
        for path in _scannable_files(Path(name)):
            for row, code, text in check(path):
                print(f"{path.as_posix()}:{row}: {code}: {text}")
                found += 1

    if found:
        print(f"\n{found} citation(s) in code. See PLAYBOOK 3.10.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
