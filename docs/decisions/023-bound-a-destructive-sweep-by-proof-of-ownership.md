# ADR-023: Bound a destructive sweep by proof of ownership

**Status:** Accepted
**Date:** 2026-08-07

## Context

Issue #107 was filed P1 for a resolution defect: an empty
`PAGEFETCH_CACHE_DIR`, or an empty `--cache-dir`, resolved to the working
directory rather than being rejected. The severity did not come from the
resolution. It came from what the store would then do — `entries()` returned
every `.txt` and `.html` file in the directory, `clean()` ran the junk
classifier over each one, and unlinked whatever it called junk. A page saved
by hand that happened to trip a wall pattern was deleted.

The fix in #109 rejected empty values. Its fourth acceptance criterion asked
a separate question: whether `entries()` should also filter on the key
scheme as defence in depth, since the scheme is fixed by CLAUDE.md §2.6 and
a `[0-9a-f]{16}` name filter costs nothing. It does filter now, through
`_KEY_STEM`.

The 2026-08-03 session shipped that narrowing without a decision record. It
judged the change a bug fix implementing a chain rule rather than an
architectural decision, noted that this was arguable because it changes what
`clean()` may touch, and flagged the judgment rather than assuming it.

It is arguable, and the flag was right to be raised, because the package
makes this same move twice. ADR-005 decided that `ChromeReaper` may kill
only Chrome descended from this interpreter, and must kill nothing when
ownership cannot be established — written against a sampling method that
claimed "appeared during this window" when it needed "belongs to this
process". `entries()` is that decision for files. Both are the same failure:
a destructive operation reaching outside what the package created and
destroying something the user did not offer it.

## Decision

**1. A destructive operation acts only on what it can prove it created.**

Proof is a property the package itself wrote — process ancestry for the
reaper, the key scheme for the store. Not a path, not a configuration value,
not a file extension. Those are the inputs that fail; they cannot also be
the evidence.

**2. Where proof is unavailable, the operation finds nothing.**

Not an error, not a prompt, not a best guess. A cache directory that
resolved somewhere unintended yields an empty sweep, and `--clean-cache`
reports nothing removed. The reaper already behaves this way, and the
symmetry is deliberate: the safe outcome of a lost ownership check is that
the destructive step has no work to do.

**3. The filter stays where it looks redundant.**

Inside a real cache directory nothing but cache entries matches, so the name
check reads as dead code on every ordinary inspection. The case it exists
for is the one where the directory is not the cache. `entries()` says this
in its docstring and must keep saying it, because the next reader to find it
redundant will be right about the common case and wrong about the reason.

**4. This binds the next destructive operation.**

Whatever is added — an eviction policy, a per-host purge, a repair pass —
establishes ownership the same way before it deletes.

## Alternatives considered

**Rely on the resolution fix alone.** #109 made empty values an error, so
the reported path is closed. Rejected because the criterion asked about
mis-resolution in general, not about the one route that had been found. The
filter is a single `fullmatch` against a pattern the key scheme already
fixes, and it holds for routes nobody has thought of.

**Error on a file that does not match, rather than skipping it.** Rejected:
a real cache directory legitimately holds screenshots, which `entries()`
already excludes as not being page content. Erroring would make any
unrelated file in the directory fatal to a clean, converting a safety
measure into a denial of the feature.

**Record nothing, as the 2026-08-03 session judged.** Rejected on the second
occurrence rather than the first. One instance is a bug fix; two instances
of the same reasoning in the same package is the principle the package
operates by, and leaving only ADR-005 written implies the caution is about
processes being dangerous rather than about destruction needing proof.

## Consequences

- The key scheme is load-bearing for safety, not only for lookup. CLAUDE.md
  §2.6 already forbids changing it because that invalidates every existing
  entry; this is a second and independent reason.
- Removing the `_KEY_STEM` check as dead code now requires superseding this
  record rather than a cleanup commit.
- The reasoning stays spelled out in the `entries()` docstring in substance,
  not as a citation — `quality.md` forbids naming a record number in code,
  and this is exactly the case it is for: the docstring has to survive
  without the reader having found this file.
- A destructive operation that cannot establish ownership at all does not
  get written. There is no third answer here — proceeding is what #107
  reported.

## Related

- ADR-005, which decided the same question for processes and is the reason
  this one is recorded.
- Chapter 9 gains a row per this record.
