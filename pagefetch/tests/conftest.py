"""Shared pytest fixtures for the pagefetch test suite.

Adds the package's parent directory to sys.path so `import pagefetch`
resolves when tests run from anywhere, and provides a temp-dir-backed
FileCache.
"""

import sys
from pathlib import Path

import pytest

# The directory holding the package is three levels up from this file
# (<parent>/pagefetch/tests/conftest.py) — the repo root here, and the
# host project's package directory when pagefetch is vendored.
PACKAGE_PARENT = Path(__file__).resolve().parent.parent.parent
if str(PACKAGE_PARENT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_PARENT))

from pagefetch import FileCache  # noqa: E402
from pagefetch.chrome import ChromeReaper  # noqa: E402


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
