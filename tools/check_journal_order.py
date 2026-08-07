"""Check the dev journal's entry order against base/core/docs.md.

One rule, reported under two codes:

    UNDATED  a session heading that does not open with a date
    ORDER    an entry dated before the entry above it

Run it over the journal:

    python tools/check_journal_order.py docs/dev-journal.md

`docs.md` requires session entries in chronological order, oldest first
and newest at the bottom. This journal was newest-first from its first
commit, against a submodule pin that had carried the rule for five weeks,
and it stayed that way for twenty sessions — because `docs.md` also tells
each session to read the prior entries and copy their skeleton exactly.
That instruction is sound and it propagates whatever it finds, so the
ordering is gated rather than reviewed.

Three things this deliberately does not do. It does not police the rest of
the heading — the theme and its em dash are format rather than order, and
belong to whatever checks format. It does not parse dates, because ISO
dates sort correctly as strings and a parser would only add a way to fail.
And it does not skip a level-two heading it cannot read: an undated one is
reported rather than passed over, since a check whose whole purpose is
that nothing slips through unnoticed should not have a silent branch. A
non-session heading added later is expected to fail here and to be
answered with a carve-out and its reasoning, the way ADR-016 records
those.

A heading may open with a date range, which the upstream-history entry
uses; its start date is the ordering key. Headings and fences are both
recognised at column zero only, so a fenced block indented inside a list
item cannot hide one from the other.
"""

import re
import sys
from pathlib import Path

# A session heading opens with its date, optionally a range for an entry
# covering several days. Everything after that is the theme.
_HEADING = re.compile(r"^## (\d{4}-\d{2}-\d{2})(?: to \d{4}-\d{2}-\d{2})?\b")

_SESSION = "## "

# A shell transcript can hold a line opening with `##`, which is a comment
# to the shell and a heading to a naive reader. This is the same problem
# the comment-layout checker solves with `tokenize`, at the scale markdown
# needs.
_FENCE = "```"


def check(path: Path) -> list[tuple[int, str, str]]:
    """Return `(line, code, text)` for every violation in one journal."""
    lines = path.read_text(encoding="utf-8").splitlines()
    found: list[tuple[int, str, str]] = []
    previous = ""
    fenced = False

    for row, line in enumerate(lines, start=1):
        if line.startswith(_FENCE):
            fenced = not fenced
            continue

        if fenced or not line.startswith(_SESSION):
            continue

        match = _HEADING.match(line)
        if match is None:
            found.append((row, "UNDATED", line.strip()))
            continue

        date = match.group(1)
        if previous and date < previous:
            found.append((row, "ORDER", f"{line.strip()}  [follows {previous}]"))

        previous = date

    return found


def main(argv: list[str]) -> int:
    """Print every violation in the given journals; return an exit code."""
    if not argv:
        print("usage: check_journal_order.py JOURNAL [JOURNAL ...]", file=sys.stderr)
        return 2

    found = 0
    for name in argv:
        path = Path(name)
        for row, code, text in check(path):
            print(f"{path.as_posix()}:{row}: {code}: {text}")
            found += 1

    if found:
        print(f"\n{found} journal-order violation(s). See base/core/docs.md.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
