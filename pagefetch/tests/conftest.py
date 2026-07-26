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


@pytest.fixture
def cache(tmp_path: Path) -> FileCache:
    return FileCache(cache_dir=tmp_path / "cache")
