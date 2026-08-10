"""The error contract: what this package raises, and what it means.

Every error raised deliberately derives from `PagefetchError`, so a caller
can wrap a whole fetch in one handler. Each also derives from the built-in
its site raised before, so this module adds discrimination without taking
any away.

That second base is the load-bearing part. Every one of these sites raised
a bare `ValueError`, callers catch `ValueError`, and the suite asserted on
message text because the type carried nothing. Dropping `ValueError` would
break all of that at once; keeping it means a caller opts in to the finer
type when it wants one and is otherwise unaffected.

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
    """A URL with no scheme, or a scheme this package will not fetch.

    Raised before any request is made or any browser is launched, so it
    never costs a fetch.
    """


class CacheDirError(PagefetchError, ValueError):
    """The configured cache directory cannot be used.

    Covers the whole resolution: an empty setting, a path that is not a
    directory, a non-directory ancestor, and a directory that is not
    writable. The message names which, and where the setting came from.
    """


class UnsupportedEncoding(PagefetchError, ValueError):
    """A response body carries a Content-Encoding this package cannot undo.

    Terminal for the tier rather than for the fetch: handing the bytes back
    undecoded is what this refusal exists to prevent, because mojibake
    clears the size floor and is cached as though it were a page.
    """


class CommandLineError(PagefetchError, ValueError):
    """An argument the CLI cannot act on.

    A missing value, a value of the wrong shape, or one outside the range
    the flag accepts. The message names the flag and what it wanted.
    """
