# ADR-005: Decide Chrome ownership by process ancestry, and kill nothing otherwise

**Status:** Accepted
**Date:** 2026-07-30

## Context

The headed browser tiers spawn Chrome processes that can outlive a fetch
when something goes wrong. `ChromeReaper` exists to kill those survivors at
interpreter exit.

Its original attribution method was to sample `chrome.exe` PIDs before a
launch, sample again after, and claim the difference. That establishes
"appeared during this window", not "belongs to this process". They are
different claims, and the gap between them is the user's own browser.

It was not a theoretical gap. A plain `pytest pagefetch/tests/test_batch.py`
printed `[cleanup] Killed 1 orphaned Chrome process(es)` and terminated a
real Chrome process on the development machine. No test in that file
launches a browser — the engines are injected as fakes — but
`_start_nodriver_session` samples the live process list for real
regardless. The sampling window is however long a headed Chrome takes to
start, and opening a tab during it was enough.

This is the worst class of bug this package can have: it reaches outside
its own process and destroys something the user did not offer it.

## Decision

**1. Ownership is established by process ancestry.**

A Chrome this package started is a descendant of this interpreter; the
user's own browser is not. `own_chrome_pids` walks each `chrome.exe`
process's parent chain looking for `os.getpid()`.

The walk goes *through* non-Chrome intermediates, because a driver may
launch Chrome via a launcher stub, and it is depth-bounded, because the
process table is a snapshot of a moving target and PIDs get reused, so a
cycle is possible and must not hang.

**2. Where ownership cannot be established, nothing is tracked.**

Off Windows, on query timeout, or on any parse failure, the process table
comes back empty and every caller therefore finds nothing to reap. This is
deliberate and the direction of the failure matters: leaving a browser
behind is a nuisance, killing someone's open tabs is not, and a tool that
cannot tell the difference should not act.

**3. The before/after sample is kept as a second, independent condition.**

Ancestry alone would claim a Chrome that the *consuming application*
launched itself before the fetch — it is a descendant of the same
interpreter. Requiring both conditions excludes it.

**4. Only the ancestry query pays for parent PIDs.**

`tasklist` cannot report a parent PID, so ancestry goes through PowerShell
CIM. The before-sample and the liveness check need only a PID set, so they
stay on `tasklist`. Routing all three through CIM made the test suite
slower than the code it replaced.

**5. One reaper per interpreter.**

`default_reaper()` is a cached singleton, built on first use so importing
the package registers nothing. A reaper per `NetworkFetcher` registered an
`atexit` handler per fetcher, none ever removed: 50 fetchers meant 50
handlers and 50 process queries at exit. An injected reaper still wins, so
a caller can substitute or disable one.

**6. The test suite does not touch the host's process table.**

A `conftest` fixture stubs both queries for every test but the reaper's
own. Nothing in the suite launches a browser, so nothing in it has any
business enumerating or signalling processes.

## Alternatives considered

- **Keep sampling, narrow the window.** Rejected: it shrinks the odds
  without changing the claim. A narrower window still cannot distinguish
  our Chrome from the user's, and a rare wrong kill is worse than a
  frequent one because nobody connects it to this tool.
- **Take the PID from the driver.** `nodriver` exposes a browser process
  handle. Rejected as the sole mechanism: SeleniumBase does not expose an
  equivalent cleanly, both are library internals that can move without
  notice, and neither can be tested here without installing the optional
  engines. Ancestry needs nothing from either library. This remains
  available as a future refinement *alongside* ancestry.
- **Match on the launch's `--user-data-dir`.** Rejected: this package does
  not control the launch arguments, so it would have to read command lines
  it did not set.
- **Remove the reaper entirely.** Rejected, though seriously considered —
  it is the only change that guarantees no wrong kill. Orphaned headed
  Chrome is a real problem on Windows, and ancestry attribution solves it
  without the collateral risk.

## Consequences

- The reaper is Windows-only in effect, as before, and now says so by
  returning an empty table rather than by accident of a failed
  `tasklist` call.
- Ancestry costs one PowerShell start per browser launch. That lands only
  on the headed-browser path, which already takes 6–24s.
- `chrome.py` is fully covered — the parsing is tested against injected
  tables rather than by spawning real subprocesses, which is how it
  reached 100% while the suite stopped touching the host.
- A consuming application that launches its own Chrome from the same
  interpreter is protected by the before/after condition, not by ancestry.
  If that condition is ever removed as redundant, that protection goes
  with it.

## Related

- #21 — the issue, raised from P2 to P0 when the test suite was observed
  killing a real browser process.
- `docs/audits/2026-07-30-360.md` — C9 and Security finding 5.
