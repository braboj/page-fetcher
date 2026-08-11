"""FileCache tests — key stability and round-trip.

The key scheme must never change: existing on-disk caches in consuming
projects depend on sha256(url)[:16] + suffix. These tests pin it.
"""

import hashlib

import pytest

from pagefetch import ContentMode, FileCache
from pagefetch.cache import CACHE_DIR_ENV
from pagefetch.errors import CacheDirNotADirectory, CacheDirNotSet


def test_url_hash_is_sha256_first_16_hex():
    url = "https://example.com/lens"
    expected = hashlib.sha256(url.encode()).hexdigest()[:16]
    assert FileCache.url_hash(url) == expected
    assert len(FileCache.url_hash(url)) == 16


def test_key_suffix_depends_on_mode(cache: FileCache):
    url = "https://example.com"
    assert cache.key(url, ContentMode.HTML).suffix == ".html"
    assert cache.key(url, ContentMode.TEXT).suffix == ".txt"


def test_key_filename_is_hash_plus_suffix(cache: FileCache):
    url = "https://example.com"
    key = cache.key(url, ContentMode.HTML)
    assert key.name == FileCache.url_hash(url) + ".html"


def test_write_then_read_round_trips(cache: FileCache):
    url = "https://example.com"
    cache.write(url, ContentMode.HTML, "<html>hi</html>")
    assert cache.read(url, ContentMode.HTML) == "<html>hi</html>"


def test_read_missing_returns_none(cache: FileCache):
    assert cache.read("https://nope.example", ContentMode.TEXT) is None


def test_modes_do_not_collide(cache: FileCache):
    url = "https://example.com"
    cache.write(url, ContentMode.HTML, "html-content")
    cache.write(url, ContentMode.TEXT, "text-content")
    assert cache.read(url, ContentMode.HTML) == "html-content"
    assert cache.read(url, ContentMode.TEXT) == "text-content"


def test_default_cache_dir_is_portable(monkeypatch):
    # Must not be tied to any project layout — CWD-relative default.
    monkeypatch.delenv(CACHE_DIR_ENV, raising=False)
    assert FileCache().cache_dir.name == "pagefetch"


# --- cache_dir precedence: explicit > env > default ------------------


def test_env_var_sets_cache_dir(monkeypatch, tmp_path):
    monkeypatch.setenv(CACHE_DIR_ENV, str(tmp_path / "envcache"))
    assert FileCache().cache_dir == tmp_path / "envcache"


def test_explicit_arg_overrides_env(monkeypatch, tmp_path):
    monkeypatch.setenv(CACHE_DIR_ENV, str(tmp_path / "envcache"))
    explicit = tmp_path / "explicit"
    assert FileCache(cache_dir=explicit).cache_dir == explicit


# --- present but empty is an error, not a default --------------------


def test_empty_env_var_is_rejected(monkeypatch):
    # Used to fall back to the default, making the highest-priority source
    # lose silently to the lowest — the shape a wrapper script produces
    # when the variable it forwards is unset.
    monkeypatch.setenv(CACHE_DIR_ENV, "")
    with pytest.raises(CacheDirNotSet):
        FileCache()


def test_empty_env_var_error_names_the_source_and_the_way_out(monkeypatch):
    monkeypatch.setenv(CACHE_DIR_ENV, "")
    with pytest.raises(CacheDirNotSet) as exc:
        FileCache()
    message = str(exc.value)
    assert CACHE_DIR_ENV in message
    assert "directory path" in message
    assert f"unset {CACHE_DIR_ENV}" in message


def test_empty_cache_dir_argument_is_rejected(monkeypatch):
    monkeypatch.delenv(CACHE_DIR_ENV, raising=False)
    with pytest.raises(CacheDirNotSet):
        FileCache(cache_dir="")


def test_unset_env_var_still_uses_the_default(monkeypatch):
    # The other half of the distinction: absent must keep working.
    monkeypatch.delenv(CACHE_DIR_ENV, raising=False)
    assert FileCache().cache_dir.name == "pagefetch"


def test_str_cache_dir_is_accepted(monkeypatch, tmp_path):
    # The signature widened to str so an empty one reaches the check above;
    # a non-empty str must resolve exactly as the Path would.
    monkeypatch.delenv(CACHE_DIR_ENV, raising=False)
    assert FileCache(cache_dir=str(tmp_path / "c")).cache_dir == tmp_path / "c"


# --- load-time validation --------------------------------------------


def test_valid_nonexistent_dir_under_writable_parent_is_accepted(tmp_path):
    # The dir need not exist yet — write() creates it lazily. Validation
    # only requires a usable (writable) existing ancestor.
    cache = FileCache(cache_dir=tmp_path / "a" / "b" / "c")
    assert cache.cache_dir == tmp_path / "a" / "b" / "c"


def test_cache_dir_pointing_at_a_file_is_rejected(tmp_path):
    a_file = tmp_path / "not-a-dir.txt"
    a_file.write_text("x", encoding="utf-8")
    with pytest.raises(CacheDirNotADirectory):
        FileCache(cache_dir=a_file)


def test_cache_dir_with_file_ancestor_is_rejected(tmp_path):
    a_file = tmp_path / "file.txt"
    a_file.write_text("x", encoding="utf-8")
    with pytest.raises(CacheDirNotADirectory):
        FileCache(cache_dir=a_file / "sub" / "cache")


def test_validation_error_names_the_source(tmp_path, monkeypatch):
    a_file = tmp_path / "f.txt"
    a_file.write_text("x", encoding="utf-8")
    monkeypatch.setenv(CACHE_DIR_ENV, str(a_file))
    with pytest.raises(CacheDirNotADirectory) as exc:
        FileCache()

    # The type says what went wrong; this test is about the message saying
    # which setting supplied the path, which the type cannot carry.
    assert CACHE_DIR_ENV in str(exc.value)


def test_validation_does_not_create_the_dir(tmp_path):
    target = tmp_path / "lazy" / "cache"
    FileCache(cache_dir=target)

    # Construction must not create the cache dir — that stays lazy (write()).
    assert not target.exists()


# --- delete / entries / clean ----------------------------------------


def test_delete_removes_entry_and_is_idempotent(cache: FileCache):
    url = "https://example.com"
    cache.write(url, ContentMode.HTML, "<html>hi</html>")
    assert cache.delete(url, ContentMode.HTML) is True
    assert cache.read(url, ContentMode.HTML) is None

    # Second delete is a no-op, not an error.
    assert cache.delete(url, ContentMode.HTML) is False


def test_entries_lists_bodies_excluding_screenshots(cache: FileCache):
    cache.write("https://a.test", ContentMode.HTML, "a")
    cache.write("https://b.test", ContentMode.TEXT, "b")

    # A .png screenshot must not be treated as a page body.
    cache.cache_dir.mkdir(parents=True, exist_ok=True)
    cache.screenshot_path("https://a.test").write_bytes(b"\x89PNG")
    suffixes = sorted(p.suffix for p in cache.entries())
    assert suffixes == [".html", ".txt"]


def test_entries_empty_when_no_cache_dir(tmp_path):
    assert FileCache(cache_dir=tmp_path / "missing").entries() == []


def test_entries_ignores_names_outside_the_key_scheme(cache: FileCache):
    # What bounds clean() when a cache dir resolved somewhere unintended.
    # Path("") is ".", so a caller who converts before calling can still
    # hand the constructor the working directory; these are the files that
    # would be sitting in it.
    cache.write("https://a.test", ContentMode.HTML, "a")
    cache.cache_dir.mkdir(parents=True, exist_ok=True)
    (cache.cache_dir / "README.html").write_text("<h1>hi</h1>", encoding="utf-8")
    (cache.cache_dir / "notes.txt").write_text("mine", encoding="utf-8")

    # Right length, wrong alphabet — the scheme is lowercase hex.
    (cache.cache_dir / "ZZZZZZZZZZZZZZZZ.txt").write_text("x", encoding="utf-8")

    # Right alphabet, wrong length.
    (cache.cache_dir / "abc123.txt").write_text("x", encoding="utf-8")

    names = [p.name for p in cache.entries()]
    assert names == [FileCache.url_hash("https://a.test") + ".html"]


def test_clean_leaves_files_outside_the_key_scheme_alone(cache: FileCache):
    # The consequence that matters: junk classification never reaches a
    # file this cache did not write, however junk-shaped its body is.
    cache.cache_dir.mkdir(parents=True, exist_ok=True)
    bystander = cache.cache_dir / "index.html"
    bystander.write_text("<title>404 Not Found</title>", encoding="utf-8")

    report = cache.clean(lambda body: "404/error" if "404" in body else None)

    assert report.removed == []
    assert bystander.exists()


def test_clean_removes_only_junk_and_reports(cache: FileCache):
    cache.write("https://good.test", ContentMode.HTML, "real lens specs")
    cache.write("https://bad.test", ContentMode.HTML, "junk page")

    def classify(body: str) -> str | None:
        return "junk" if "junk" in body else None

    report = cache.clean(classify)
    assert report.kept == 1
    assert len(report.removed) == 1
    assert report.removed[0][1] == "junk"
    assert cache.read("https://good.test", ContentMode.HTML) == "real lens specs"
    assert cache.read("https://bad.test", ContentMode.HTML) is None


def test_clean_dry_run_deletes_nothing(cache: FileCache):
    cache.write("https://bad.test", ContentMode.HTML, "junk page")

    report = cache.clean(lambda body: "junk" if "junk" in body else None, dry_run=True)
    assert report.dry_run is True
    assert len(report.removed) == 1

    # File still present — dry run only reports.
    assert cache.read("https://bad.test", ContentMode.HTML) == "junk page"
