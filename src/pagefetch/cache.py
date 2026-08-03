"""Filesystem cache for fetched pages.

Caches responses on disk keyed by a hash of the URL, so repeated fetches
of the same page during a session are free. The cache directory is a
constructor parameter (not a module global) so the package stays portable:
a consuming project points it wherever it likes; the default is relative
to the current working directory.

The key scheme (sha256(url) truncated to 16 hex chars, plus a .txt/.html
suffix) is fixed — changing it would silently invalidate every existing
cached file.
"""

import hashlib
import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .source import ContentMode

# A consuming project can point every entry point (CLI included) at one
# cache directory by setting this env var, without the package hardcoding
# any project layout. Explicit cache_dir= still wins over it.
CACHE_DIR_ENV = "PAGEFETCH_CACHE_DIR"

# The stem every cached body carries — see url_hash. entries() matches on
# it so a sweep can only ever reach files this cache wrote.
_KEY_STEM = re.compile(r"[0-9a-f]{16}")


@dataclass
class CleanReport:
    """Outcome of a cache sweep.

    `removed` pairs each purged file with the reason it was junk;
    `dry_run` means nothing was actually deleted.
    """

    removed: list[tuple[Path, str]] = field(default_factory=list)
    kept: int = 0
    dry_run: bool = False


class FileCache:
    """A directory of cached page responses and screenshots."""

    def __init__(self, cache_dir: Path | str | None = None):
        """Resolve the cache directory and confirm it is usable.

        Accepts a str as well as a Path so that a caller forwarding a
        possibly-empty value — `FileCache(os.environ.get("DIR", ""))` —
        reaches the empty check below instead of losing the distinction
        to `Path("")`. See `_reject_empty`.
        """
        # Precedence: explicit arg > PAGEFETCH_CACHE_DIR env > CWD-relative
        # default. The default stays portable (not tied to any project
        # layout); a consumer uses the env var to unify all entry points.
        if cache_dir is not None:
            source = "cache_dir argument"
            self.cache_dir = self._reject_empty(cache_dir, source, "pass None")
        # Membership, not truthiness: an empty value is a caller reaching
        # past the default, not a caller who never set one.
        elif CACHE_DIR_ENV in os.environ:
            source = f"${CACHE_DIR_ENV}"
            self.cache_dir = self._reject_empty(
                os.environ[CACHE_DIR_ENV], source, f"unset {CACHE_DIR_ENV}"
            )
        else:
            self.cache_dir = Path.cwd() / ".cache" / "pagefetch"
            source = "default"
        # Validate at construction, not at first write — a bad value (a path
        # that is a file, or whose parent is missing/read-only) fails here
        # with a clear message instead of cryptically on the first cache op.
        self._validate_cache_dir(source)

    @staticmethod
    def _reject_empty(value: Path | str, source: str, to_default: str) -> Path:
        """Reject a present-but-empty cache dir instead of defaulting.

        An empty value used to resolve exactly as an absent one, so the
        highest-priority source lost silently to the lowest: an unset
        variable expanded into `--cache-dir "$VAR"` picked up the default
        the caller was reaching past.

        Only a str still carries the distinction. `Path("")` is `.`, so a
        caller who converts before calling has already made an empty value
        indistinguishable from an explicit `Path(".")`, which is a
        legitimate choice this cannot reject. `entries()` is what bounds
        the damage in that case.
        """
        if isinstance(value, str) and value == "":
            raise ValueError(
                f"pagefetch cache dir (from {source}) is empty — expected a "
                f"directory path; {to_default} to use the default"
            )
        return Path(value)

    def _validate_cache_dir(self, source: str) -> None:
        """Fail fast if the resolved cache dir cannot be created/written.

        Does not create the directory — that stays lazy (write()). It only
        confirms the path is usable: not an existing non-directory, and the
        nearest existing ancestor is a writable directory.
        """
        path = self.cache_dir
        if path.exists() and not path.is_dir():
            raise ValueError(
                f"pagefetch cache dir (from {source}) is not a directory: {path}"
            )
        # Walk up to the nearest existing ancestor and check it is writable.
        ancestor = path
        while not ancestor.exists():
            parent = ancestor.parent
            if parent == ancestor:  # reached filesystem root
                break
            ancestor = parent
        if not ancestor.is_dir():
            raise ValueError(
                f"pagefetch cache dir (from {source}) has a non-directory "
                f"ancestor: {ancestor} (for {path})"
            )
        if not os.access(ancestor, os.W_OK):
            raise ValueError(
                f"pagefetch cache dir (from {source}) is not writable: "
                f"{path} (nearest existing ancestor {ancestor} is read-only)"
            )

    @staticmethod
    def url_hash(url: str) -> str:
        """Return the cache key stem for a URL.

        The scheme is fixed: changing the digest, its length, or the
        suffixes below silently invalidates every existing cache. It is
        also spelled as a pattern in `_KEY_STEM`, which `entries()`
        matches on — a change here has to move both.
        """
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    def key(self, url: str, mode: ContentMode) -> Path:
        """Return the path a URL's body occupies for the given mode."""
        suffix = ".html" if mode is ContentMode.HTML else ".txt"
        return self.cache_dir / (self.url_hash(url) + suffix)

    def screenshot_path(self, url: str) -> Path:
        """Return the path a URL's screenshot occupies."""
        return self.cache_dir / (self.url_hash(url) + ".png")

    def read(self, url: str, mode: ContentMode) -> str | None:
        """Return the cached body for a URL, or None if there is none."""
        path = self.key(url, mode)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def write(self, url: str, mode: ContentMode, content: str) -> None:
        """Store a body under the URL's key, creating the directory."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.key(url, mode).write_text(content, encoding="utf-8")

    def delete(self, url: str, mode: ContentMode) -> bool:
        """Remove one cached entry. Returns True if a file was removed.

        Idempotent — a missing entry is not an error.
        """
        path = self.key(url, mode)
        if path.exists():
            path.unlink()
            return True
        return False

    def entries(self) -> list[Path]:
        """All cached page bodies (.txt / .html).

        Screenshots (.png) are not page content and are excluded.

        Names must also match the key scheme. Inside a real cache
        directory nothing else is there to match, so the filter looks
        redundant — it is not, because `clean()` deletes what this
        returns, and a cache dir that resolved somewhere unintended is
        exactly the case where the sweep must find nothing rather than
        read whatever `.txt`/`.html` files it lands among.
        """
        if not self.cache_dir.exists():
            return []
        return sorted(
            p
            for p in self.cache_dir.iterdir()
            if p.is_file()
            and p.suffix in (".txt", ".html")
            and _KEY_STEM.fullmatch(p.stem)
        )

    def clean(
        self, classify: Callable[[str], str | None], dry_run: bool = False
    ) -> CleanReport:
        """Sweep the cache, removing entries whose body is junk.

        `classify(body)` returns a short reason string when the body is junk
        (e.g. "404/error", "bot-blocked") or None to keep it. Real content is
        kept. With `dry_run=True` nothing is deleted — the report lists what
        would be removed.
        """
        report = CleanReport(dry_run=dry_run)
        for path in self.entries():
            try:
                body = path.read_text(encoding="utf-8")
            except OSError:
                continue
            reason = classify(body)
            if reason is None:
                report.kept += 1
                continue
            report.removed.append((path, reason))
            if not dry_run:
                path.unlink()
        return report
