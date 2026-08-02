"""Shared pytest fixtures for the pagefetch test suite.

Provides a temp-dir-backed FileCache and keeps the suite away from the
host's real process table.

`import pagefetch` resolves through the install, not through sys.path.
This file used to insert the repository root so the import worked without
one — which is exactly how the suite came to pass against source that was
never packaged. ADR-010 moved the package to `src/` to close that off, so
the manipulation is gone: run the editable install from ONBOARDING §1.
"""

from pathlib import Path

import pytest

from pagefetch import FileCache
from pagefetch.chrome import ChromeReaper


@pytest.fixture
def cache(tmp_path: Path) -> FileCache:
    return FileCache(cache_dir=tmp_path / "cache")


@pytest.fixture(autouse=True)
def _no_real_process_queries(monkeypatch, request):
    """Keep the suite away from the host's real process table.

    A batch test drives _start_nodriver_session with a fake engine, but
    the reaper inside it is real: it queried the live process list and,
    before ownership was decided by ancestry, killed a Chrome the
    developer had open. Nothing in this suite launches a browser, so
    nothing in it has any business enumerating or signalling processes.

    Also keeps the suite fast — the ancestry query starts a PowerShell.
    test_chrome_reaper opts out, since exercising the reaper is its job.
    """
    if request.node.path.name == "test_chrome_reaper.py":
        return
    monkeypatch.setattr(ChromeReaper, "_process_table", staticmethod(list))
    monkeypatch.setattr(ChromeReaper, "running_chrome_pids", staticmethod(set))
