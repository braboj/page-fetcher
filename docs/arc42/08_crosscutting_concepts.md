# Crosscutting Concepts

## Classification

Every decision the package makes about a response — return it, store it,
escalate past it, delete it — comes from the same set of pure predicates
over the body. They are pure on purpose: no I/O, no configuration, no
knowledge of which transport produced the body or what will be done with
the verdict. That is what lets the same rule run before returning, before
storing, on reading a stored body and during a sweep without four copies of
it.

Patterns are matched against two forms of the same body: the first five
kilobytes of raw markup, and the first twenty kilobytes with tags removed.
Both are needed because walls and error pages embed their text in
script-heavy and style-heavy wrappers. The raw form catches markers bound
to markup, a title or a script source; the de-tagged form catches prose
broken across tags.

| Concept | Implementation |
| --------- | ---------------- |
| Wall, challenge or throttle stub | `BOT_DETECTION_PATTERNS`, plus a short body carrying a meta-refresh |
| Not-found or gone, at any size | `ERROR_PAGE_PATTERNS` |
| Not-found or gone, only when short | `AMBIGUOUS_ERROR_PAGE_PATTERNS` |
| Plausibly a page at all | `looks_like_real_content` |
| Never serve this from the store | `is_cacheable_junk` |
| Size floor for a real page | `MIN_REAL_CONTENT_BYTES` |

### Why Two Error Lists

A not-found verdict is terminal: no escalation, nothing stored, no content
returned. That makes a false positive here the most expensive mistake the
package can make, so the phrasing that can arrive innocently is separated
from the phrasing that cannot.

"No longer available" and "has been discontinued" mean the page is gone on
a stub, and mean one variant is out of stock in the body copy of a
perfectly good product page. They count only below the size floor, where
there is too little else on the page for the phrase to be incidental. A
title of 404 or 410, "page not found", and "the page you requested could
not be found" are decisive at any size.

The same reasoning governs walls. "Rate limit" alone is ordinary technical
prose that an article about API design says in passing, so it registers
only alongside a word that a page actually being throttled would use.

The rule that follows for anyone adding a pattern: it must not match
ordinary body copy, because both lists are scanned over twenty kilobytes of
de-tagged text. A bare phrase will hit real pages.

### The Size Floor

A body below the floor is not a page, whatever it contains. This is the
safety net for stubs that carry no recognizable wording at all — a
retailer's "slow down" page that is well-formed, several kilobytes long and
says nothing a pattern would catch. The floor is checked against raw
markup, never against text: real content reduced to text is legitimately
much shorter than the threshold.

### What Classification Does Not Ask

Every predicate asks whether a response *failed*. None asks whether it is
*complete*. A body that clears the floor and trips no pattern is returned
as it stands, even when a meaningful part of the page renders in
JavaScript — a comments thread, a lazy-loaded table, a shell padded out
with layout markup. Nothing escalates, nothing reaches standard error, and
the partial body is stored under the key a complete one would have used. A
caller who needs completeness names the JavaScript transport.

The omission is deliberate. Candidate signals for under-rendering — a
text-to-markup ratio, an empty mount point, framework bootstrap markers, a
script requirement — each produce a false positive on some complete page,
and the cost of that false positive is what settles it rather than its
frequency. The plain transport hands back a sentinel instead of the body
when it signals escalation, so the markup is already discarded by the time
a browser rung is tried, and the browser rungs are optional extras that a
default install does not have. On such a host a wrong "incomplete" verdict
converts a good page into no page.

## Response Decoding

The plain transport advertises only the compressions it can undo, which is
gzip and deflate: the standard library covers both, and advertising an
encoding that cannot be undone is how a response becomes unreadable.
Deflate falls back to a raw stream when the zlib header is absent, because
some servers send one that way.

Two cases are handled against the header rather than with it. A body
carrying gzip's signature is decompressed even when the response did not
declare gzip, and a declared encoding that cannot be undone — including any
chain of them — fails the transport instead of being passed on. Both point
the same way: undecoded bytes read as text become mojibake, mojibake is
comfortably larger than the size floor, and it would therefore pass as a
page and be stored as one.

| Concept | Implementation |
| --------- | ---------------- |
| What is advertised | `ACCEPT_ENCODING` |
| What can be undone | `DECODABLE_ENCODINGS` |
| Undeclared compression | gzip signature sniffing in `_decompress` |
| Anything else | `ValueError`, which fails the transport |

## Retained Content

Bodies are kept on disk, one file per URL and content form. The key is a
truncated digest of the URL plus a suffix naming the form, and the two
forms of one page are separate entries. The scheme is fixed: the digest,
its length and the suffixes are load-bearing, and changing any of them
orphans every existing entry silently rather than failing.

Validity is decided by content, not by age. There is no expiry. Reference
pages change rarely, and the change that matters — the page going away —
arrives as a not-found body the classifier already recognizes. So a stored
body is classified when it is read, and one that is a wall or a not-found
page is deleted and treated as a miss. A store poisoned before a rule
existed, or holding a product page withdrawn since, heals itself on the
next fetch. A sweep does the same thing in bulk, and can report without
deleting.

Only the pattern checks apply on read, not the size floor: a stored body in
text form is legitimately short after markup is stripped.

The flag that ignores the store is a refresh rather than a bypass. It
decides whether a stored body is *served*, not whether a fresh one is
*stored* — so a fetch under it replaces the stale entry instead of leaving
it to be served next time. Every path honours this identically, including a
batch holding a browser open.

| Concept | Implementation |
| --------- | ---------------- |
| Key derivation | `FileCache.url_hash` and `FileCache.key` |
| Single read, with the scrub | `NetworkFetcher._read_cache` |
| Single write, ungated by the flag | `NetworkFetcher._write_cache` |
| Bulk sweep | `FileCache.clean` with a caller-supplied verdict |
| What counts as junk | `is_cacheable_junk`, shared by both paths |

## Waiting for a Browser

Browser transports poll rather than sleeping a fixed time. They wait for
the document to report itself complete, then read the page source on an
exponential backoff from half a second to a two-second cap until the wall
patterns are gone. A fifteen-second deadline bounds that wait, and reaching
it fails the transport rather than returning what is on screen.

Settling afterwards differs by transport: one scrolls to the bottom and
waits half a second, the other polls the document height until it stops
changing or three seconds pass.

The point is that a security handshake takes as long as it takes.
Polling adapts to it; a fixed sleep is either wasted time on a fast page or
a failure on a slow one. A caller asking for more wait than the default
gets an additional explicit sleep on top — the default is a floor, not a
budget.

## Configuration

There is one configurable value, the store directory, and it resolves from
a command-line flag, then a constructor argument, then an environment
variable, then a built-in default under the working directory.

An empty value is an error at every level, not a fall back to the next one.
A variable that is unset and expanded into a wrapper script would otherwise
silently pick the default the caller was reaching past, and the error names
which source supplied the empty value.

Validation happens when the store is constructed rather than at the first
write, so a bad path fails immediately rather than cryptically. The
directory itself is created lazily.

A typed settings object and dotenv loading are not used. They would add
dependencies that break the standard-library-only property of the default
install, and they are more machinery than one value justifies. The point to
revisit is several values — a user agent, timeouts, transport toggles — at
which point one typed object would arrive across all of them at once.

## The URL Boundary

Every public entry point rejects a URL whose scheme is not HTTP or HTTPS,
before any request is made or any browser is launched. Without it the plain
transport would read a local file and hand the contents back as page
content.

This is a scheme allowlist and nothing more. It does not stop a request to
a loopback address, a link-local address or anything else on a private
network, and it is not intended to. Blocking private ranges would break
ordinary intranet and localhost fetching while offering a guarantee this
layer cannot honestly make: the check would have to resolve the host and
re-check after every redirect to mean anything. A consumer whose URLs come
from user input, a configuration they do not control, or a redirect chain
still needs their own filter — and the check function and the allowed-scheme
set are both exported so they can apply the same rule at their own
boundary.

| Concept | Implementation |
| --------- | ---------------- |
| The rule | `require_supported_scheme` |
| The set | `ALLOWED_SCHEMES` |
| Where it runs | Every public method, before any transport |

## Process Ownership

A browser started by a transport can outlive the fetch when something goes
wrong. Cleaning up requires knowing which browsers are ours, and sampling
process identifiers before and after a launch does not establish that: a
browser window the user opens while a fetch is running lands in the same
set.

Attribution therefore runs on ancestry. A browser this package started is a
descendant of the running interpreter, and the user's own browser is not. A
process is recorded only when it is both new since the launch sample and
descended from this process. Where ancestry cannot be established, nothing
is recorded and nothing is killed — leaving a browser behind is a nuisance,
and killing somebody's open tabs is not.

The process query is platform-specific and confined to one module, which
does nothing else. On platforms where it does not apply, it returns nothing
and cleanup is a no-op.

## Narration and Failure Reporting

Content goes to standard output. Everything else — an escalation, a skipped
transport, a decode failure, a batch's progress, the count of browsers
reaped — goes to standard error with a bracketed prefix naming the
transport or phase that emitted it. A successful plain fetch says nothing
at all; the transports narrate only when something happens.

The split is what makes redirection safe. A failed fetch writes nothing to
standard output and exits non-zero, so a shell chain that redirects into a
file and processes it stops rather than processing an empty file.

A batch grades itself by how many URLs returned content: all, none, or
some. The third has its own exit status because "some pages are missing"
and "nothing came back" call for different handling.

Failure never arrives as an exception. The abstract page source states it
directly: a fetch that fails returns an unsuccessful result with empty
content. Exceptions are reserved for a caller's mistake — an unsupported
scheme, an unusable store directory, a malformed flag value.

## Testability

The abstract page source exists so that consuming code can be written
against an interface and exercised without a network. The published double
is backed by a map of URLs to bodies, records what it was asked for, and
derives the text form from the stored body exactly as the real
implementation does — so a consumer exercising both forms sees them differ
under test the way they will in production.

The package's own suite runs with no network and no browser. Escalation is
tested by substituting the four transport methods, which is what makes the
ladder's ordering testable without any engine installed. Two host queries
are stubbed for the whole suite as well, so no test enumerates or signals a
process on the machine it runs on.

| Concept | Implementation |
| --------- | ---------------- |
| The substitutable interface | `PageSource` |
| The published double | `FakeFetcher` |
| Ladder tests without engines | Transport methods substituted per test |
| Host queries neutralized suite-wide | A fixture stubbing both process queries |

## Naming

Transports are named for what they require of the caller, not for the
engine behind them. A display or no display is the part a caller cannot
change; which library renders the page is not. The same names are used for
the enumeration members, the command-line flags, the reported transport and
the narration prefixes, so replacing an engine changes nothing a caller has
written down and no name in this documentation.
