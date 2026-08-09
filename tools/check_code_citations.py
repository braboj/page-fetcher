"""Check that no code comment or docstring cites an issue, PR or record.

One rule, reported under two codes:

    ISSUE   a `#` followed immediately by digits
    RECORD  an `ADR` followed by digits

Run it over the repository's Python roots:

    python tools/check_code_citations.py src tests examples tools

Comments come from `tokenize` and docstrings from `ast`, so a citation
inside an ordinary string literal is left alone — test data describing a
violation is not one. Markdown is never scanned: cross-referencing by
number is what the README, the records and the journal are for.

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


def check(path: Path) -> list[tuple[int, str, str]]:
    """Return `(line, code, text)` for every citation in one file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[tuple[int, str, str]] = []

    for row, text in list(_comments(path)) + list(_docstrings(path, tree)):
        for code, pattern in PATTERNS:
            match = pattern.search(text)
            if match is not None:
                found.append((row, code, f"{match.group()}  in: {text.strip()}"))

    return sorted(found)


def _python_files(root: Path) -> Iterator[Path]:
    """Yield every Python file under one root, in a stable order."""
    if root.is_file():
        yield root
        return

    yield from sorted(root.rglob("*.py"))


def main(argv: list[str]) -> int:
    """Print every citation in the given roots; return an exit code."""
    if not argv:
        print("usage: check_code_citations.py ROOT [ROOT ...]", file=sys.stderr)
        return 2

    found = 0
    for name in argv:
        for path in _python_files(Path(name)):
            for row, code, text in check(path):
                print(f"{path.as_posix()}:{row}: {code}: {text}")
                found += 1

    if found:
        print(f"\n{found} citation(s) in code. See PLAYBOOK 3.10.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
