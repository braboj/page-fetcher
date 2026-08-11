"""The error contract: what this package raises, and what it means.

Every error raised deliberately derives from `PagefetchError`, so a caller
can wrap a whole fetch in one handler. Each also derives from the built-in
its site raised before, so this module adds discrimination without taking
any away.

That second base is load-bearing. Every one of these sites raised a bare
`ValueError`, callers catch `ValueError`, and the suite asserted on message
text because the type carried nothing. Dropping `ValueError` would break
all of that at once; keeping it means a caller opts in to the finer type
when it wants one and is otherwise unaffected.

Depth is bounded by one question: could a caller reasonably act
differently? A missing scheme invites prepending one, while an unsupported
scheme is a refusal, so those are separate. A cache directory that is unset
is a different repair from one that is not writable. A chained
Content-Encoding and an unknown one both mean the same thing to a caller —
escalate — so they share a type, and so do the command-line faults, which
all end the same way. The alternative, a type per raise site, only
re-encodes the messages in class names.

This module imports nothing from the package. It sits below `source.py`
rather than beside it, so the contract module's own rule — that it depends
on nothing — is untouched whether or not it ever raises.
"""


class PagefetchError(Exception):
    """Base for every error this package raises on purpose.

    Catching this catches a deliberate refusal and nothing else: a bug in
    the package still surfaces as whatever it really is.
    """


class InvalidURL(PagefetchError, ValueError):
    """A URL this package will not fetch.

    Raised before any request is made or any browser is launched, so it
    never costs a fetch.
    """


class MissingScheme(InvalidURL):
    """A URL with no scheme at all, such as `example.com/page`.

    Separate from an unsupported scheme because it is usually a typo with
    an obvious repair, and the message offers it.
    """


class UnsupportedScheme(InvalidURL):
    """A URL whose scheme this package refuses, such as `file://`.

    A refusal rather than a mistake: the scheme parsed, and the answer is
    still no.
    """


class CacheDirError(PagefetchError, ValueError):
    """The configured cache directory cannot be used.

    The message names which setting supplied the path, because the failure
    is as often in the wiring as in the directory.
    """


class CacheDirNotSet(CacheDirError):
    """The cache directory setting is present but empty.

    Distinct from unset, which legitimately falls back to the default.
    An empty value is a wrapper forwarding a variable it never received,
    and treating it as absent lets the highest-priority source lose
    silently to the lowest.
    """


class CacheDirNotADirectory(CacheDirError):
    """The cache path, or something above it, is not a directory."""


class CacheDirNotWritable(CacheDirError):
    """The cache directory exists but cannot be written to."""


class UnsupportedEncoding(PagefetchError, ValueError):
    """A response body carries a Content-Encoding this package cannot undo.

    Covers an unknown encoding and a chain alike: both mean the tier must
    fail rather than hand back bytes it could not decode. Terminal for the
    tier, not for the fetch — undecoded bytes clear the size floor as
    mojibake and would be cached as though they were a page.
    """


class CommandLineError(PagefetchError, ValueError):
    """An argument the CLI cannot act on.

    A missing value, an empty one, or a value outside what the flag
    accepts. One type because the CLI answers all of them the same way:
    name the flag, say what it wanted, and exit.
    """
