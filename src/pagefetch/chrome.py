"""Orphaned-Chrome cleanup.

Headed browser tiers (Nodriver, SeleniumBase UC) spawn Chrome processes
that can outlive the fetch if something goes wrong. ChromeReaper tracks
the ones this process launched and kills any survivors at exit.

"The ones this process launched" is the whole difficulty. Sampling
`chrome.exe` PIDs before and after a launch and claiming the difference
does not establish ownership: a Chrome window the user opens while a
fetch is running lands in the same set, and gets killed. So attribution
runs on process ancestry instead — a Chrome this package started is a
descendant of this interpreter, and the user's own browser is not.

Where ancestry cannot be established the reaper tracks nothing. Leaving a
browser behind is a nuisance; killing someone's open tabs is not, and a
tool that cannot tell the difference should not be swinging.

This is the one Windows-specific, side-effectful part of the package; it
is isolated here so the rest stays portable. On non-Windows platforms the
process query yields nothing and cleanup is a no-op.
"""

import atexit
import contextlib
import functools
import os
import signal
import subprocess
import sys

# "<pid>,<ppid>,<name>" per line, which is what _process_table asks
# PowerShell to emit.
_ROW_FIELDS = 3

# tasklist's CSV rows are "image name","pid",... — a row is only usable
# once the PID column is present.
_PID_COLUMN = 1
_MIN_CSV_COLUMNS = 2

# Walking a parent chain cannot loop on a well-formed process table, but
# the table is a snapshot of a moving target and PIDs get reused. Bound
# the walk rather than trust it.
_MAX_ANCESTRY_DEPTH = 64

_CHROME_IMAGE = "chrome.exe"


@functools.cache
def default_reaper() -> "ChromeReaper":
    """The process-wide reaper.

    One instance per interpreter, so one atexit handler and one process
    query at exit however many fetchers are built. Registering per
    instance leaked a handler and pinned the reaper alive on every
    NetworkFetcher — 100 fetchers meant 100 handlers and 100 queries.

    Built on first use rather than at import, so importing the package
    registers nothing.
    """
    return ChromeReaper()


class ChromeReaper:
    """Tracks Chrome PIDs spawned by this process and reaps survivors."""

    def __init__(self, register_atexit: bool = True) -> None:
        """Start with no tracked PIDs, optionally reaping them at exit."""
        self._spawned_pids: set[int] = set()
        if register_atexit:
            atexit.register(self.cleanup)

    @staticmethod
    def _process_table() -> list[tuple[int, int, str]]:
        """(pid, parent pid, image name) for every running process.

        Windows only. Returns an empty list elsewhere, on timeout, or on
        any parse failure — every caller then finds nothing to reap, which
        is the safe direction.

        tasklist cannot report a parent PID, so this goes through CIM.
        """
        if sys.platform != "win32":
            return []
        rows: list[tuple[int, int, str]] = []
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "Get-CimInstance Win32_Process | ForEach-Object "
                    '{ "$($_.ProcessId),$($_.ParentProcessId),$($_.Name)" }',
                ],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            for line in result.stdout.splitlines():
                parts = line.strip().split(",", 2)
                if len(parts) != _ROW_FIELDS:
                    continue
                with contextlib.suppress(ValueError):
                    rows.append((int(parts[0]), int(parts[1]), parts[2].lower()))
        except Exception:
            pass
        return rows

    @staticmethod
    def running_chrome_pids() -> set[int]:
        """All chrome.exe PIDs currently running, whoever started them.

        Goes through tasklist rather than the CIM table because callers of
        this only need the PID set, and tasklist answers in a fraction of
        the time a PowerShell start-up costs. Ownership is decided by
        own_chrome_pids, which is the one that pays for parent PIDs.
        """
        pids: set[int] = set()
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq chrome.exe", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            for line in result.stdout.strip().splitlines():
                parts = line.strip('"').split('","')
                if len(parts) >= _MIN_CSV_COLUMNS:
                    with contextlib.suppress(ValueError):
                        pids.add(int(parts[_PID_COLUMN]))
        except Exception:
            pass
        return pids

    @classmethod
    def own_chrome_pids(cls) -> set[int]:
        """chrome.exe PIDs descended from this interpreter.

        A browser started by a tier is a child of this process, and its
        renderer and GPU processes are children of that browser, so the
        whole tree resolves by walking parents. Anything that does not
        reach this PID belongs to someone else and is left alone.
        """
        return cls._own_chrome_pids(cls._process_table(), os.getpid())

    @staticmethod
    def _own_chrome_pids(table: list[tuple[int, int, str]], root_pid: int) -> set[int]:
        """The ancestry walk, separated from how the table is obtained."""
        parents = {pid: ppid for pid, ppid, _ in table}
        chrome = {pid for pid, _, name in table if name == _CHROME_IMAGE}
        owned: set[int] = set()
        for pid in chrome:
            current = pid
            for _ in range(_MAX_ANCESTRY_DEPTH):
                parent = parents.get(current)
                if parent is None or parent == current:
                    break
                if parent == root_pid:
                    owned.add(pid)
                    break
                current = parent
        return owned

    def track_new_since(self, pids_before: set[int]) -> None:
        """Record Chrome this process launched since pids_before.

        Both conditions have to hold: the PID must be new since the sample
        AND descended from this interpreter. Ancestry alone would be
        enough, but a PID that fails either test is not ours to kill.
        """
        self._spawned_pids.update(self.own_chrome_pids() - pids_before)

    def cleanup(self) -> None:
        """Kill tracked Chrome processes that are still running."""
        if not self._spawned_pids:
            return
        still_running = self.running_chrome_pids() & self._spawned_pids
        for pid in still_running:
            with contextlib.suppress(OSError, ProcessLookupError):
                os.kill(pid, signal.SIGTERM)
        if still_running:
            print(
                f"[cleanup] Killed {len(still_running)} orphaned Chrome process(es)",
                file=sys.stderr,
            )
