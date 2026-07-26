"""Orphaned-Chrome cleanup.

Headed browser tiers (Nodriver, SeleniumBase UC) spawn Chrome processes
that can outlive the fetch if something goes wrong. ChromeReaper tracks
the PIDs spawned during its lifetime and kills any survivors at exit.

This is the one Windows-specific, side-effectful part of the package; it
is isolated here so the rest stays portable. On non-Windows platforms the
tasklist call simply yields no PIDs and cleanup is a no-op.
"""

import atexit
import contextlib
import os
import signal
import subprocess
import sys

# tasklist's CSV rows are "image name","pid",... — a row is only usable
# once the PID column is present.
_PID_COLUMN = 1
_MIN_CSV_COLUMNS = 2


class ChromeReaper:
    """Tracks Chrome PIDs spawned by this process and reaps survivors."""

    def __init__(self) -> None:
        self._spawned_pids: set[int] = set()
        atexit.register(self.cleanup)

    @staticmethod
    def running_chrome_pids() -> set[int]:
        """All chrome.exe PIDs currently running (Windows only; empty set
        elsewhere or on error)."""
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

    def track_new_since(self, pids_before: set[int]) -> None:
        """Record Chrome PIDs that appeared since pids_before was sampled."""
        self._spawned_pids.update(self.running_chrome_pids() - pids_before)

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
