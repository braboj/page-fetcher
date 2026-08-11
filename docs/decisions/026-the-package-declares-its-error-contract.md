# ADR-026: The package declares its error contract

**Status:** Accepted
**Date:** 2026-08-10

## Context

Thirteen sites across four modules raised a bare `ValueError`: two for a
URL the package will not fetch, four for a cache directory it cannot use,
two for a `Content-Encoding` it cannot undo, and five for a command-line
argument it cannot act on. The package defined no exception type at all.

A caller therefore could not tell those apart. Catching `ValueError`
around a fetch catches a bad URL, an unusable cache directory, and any
`ValueError` raised by the caller's own code inside the same block, with
no way to branch between them.

The suite had the same problem and answered it the only way available:
twenty-two assertions matched on message text. `match="is empty"`,
`match="not a directory"`, `match="unsupported Content-Encoding"`. Those
read as assertions about behaviour but are assertions about wording, and
they fail for the wrong reason. Rewording one cache message —
`"is not a directory"` to `"must be a directory, but is not"` — broke two
tests, neither of which was about how the message reads.

## Decision

**1. Every error the package raises on purpose derives from
`PagefetchError`, declared in `errors.py`.**

A caller can wrap a whole fetch in one handler and catch deliberate
refusals only. A bug inside the package still surfaces as whatever it
really is, which a broad `except ValueError` around a fetch did not allow.

**2. Every error also derives from the built-in its site raised before.**

All ten types derive from `ValueError`. This is what makes the change
invisible to anyone not asking for it: existing callers, both CLI
handlers, and every assertion in the suite kept working with no edit. It
also bounds the future — a new error type inherits whichever built-in its
site would otherwise have raised, and dropping that base later is a
breaking change to be decided on its own.

**3. Depth is bounded by one question: could a caller reasonably act
differently?**

A missing scheme invites prepending one; an unsupported scheme is a
refusal. An unset cache directory is a different repair from one that is
not writable. Those are separate types. A chained `Content-Encoding` and
an unknown one both mean *escalate*, and every command-line fault ends the
same way — those share a type. The result is ten types for thirteen sites,
not thirteen.

**4. A test asserts the type. It asserts the message only when the message
is its subject.**

Where a test pinned a failure by quoting prose, it now names the type.
Where a test is about what the message tells the user — that it names the
setting that supplied a path, that it offers `https://` for a
scheme-relative URL — it keeps asserting the text, and its name says so.

**5. The contract is closed, and a test keeps it closed.**

`test_the_package_raises_nothing_outside_the_contract` walks every `raise`
in the package and fails on anything outside the hierarchy. Without it the
contract erodes one commit at a time, and nothing else in the gate looks.

## Alternatives considered

**Leave the bare `ValueError`s and keep matching on messages.** Rejected
by measurement rather than by taste: one reword, two failures, neither
about wording. The suite was pinning the only thing it could reach.

**A type per raise site.** Thirteen types for thirteen sites re-encodes
the messages as class names and calls it a hierarchy. It would let a test
pin any variant, but no caller would branch on most of them, and the
depth would then exist to serve the tests rather than the callers. The
tests that genuinely pin a variant now say so in their names instead.

**A structured `reason` slug on each error, asserted instead of the
type.** Rejected as a second discrimination mechanism beside the class,
where Python already has one. It would also have to be kept consistent by
hand at every raise site, with nothing checking it.

**Put the types in `source.py`.** That module is the contract every other
module depends on and may not import from any of them, so error types
living there would be reachable without a new module. Rejected because
`errors.py` imports nothing either, so it costs the same and keeps
`source.py` about the fetch protocol. Either choice satisfies the
no-imports rule.

**Leave `__main__.py` raising bare `ValueError`.** The CLI is arguably a
consumer of the library rather than part of its API, and a programmatic
caller never sees a `CommandLineError`. Rejected because `__main__.py`
ships in the wheel behind a console-script entry point, and exempting it
would mean the closure test in point 5 has to skip a module — an exemption
covering more than its stated reason, which this repository has spent
effort removing elsewhere.

## Consequences

- Ten error types, exported from `__init__`, since an error a caller
  cannot name is not a contract.
- The twenty-two message assertions become type assertions, except where
  the message is the subject. Rewording the cache message that previously
  broke two tests now breaks none.
- `errors.py` is a new module in a package whose structure rules name each
  one. CLAUDE.md 1.2 gains it.
- A new raise site must use or add a type. The closure test enforces it;
  the cost is that adding a genuinely new kind of failure is now two edits
  rather than one.
- The `BLE001` exemption on `network.py` is unaffected. Those catches
  wrap failures from playwright, nodriver, seleniumbase and urllib, and a
  type declared here does not change what a driver raises.

**Upstream:** the generic rule — a library declares an error hierarchy
rooted in one base, each type also deriving from the built-in it replaces
so the change is not breaking, with a test asserting the hierarchy is
closed — is reusable and belongs near `base/core/quality.md`'s existing
material on error handling. Filed upstream as `#1007`.

## Related

- ADR-010 on the `src/` layout that makes `errors.py` importable as part
  of the installed package.
- ADR-016 on gating a convention no linter expresses, which is the shape
  the closure test in point 5 takes.
