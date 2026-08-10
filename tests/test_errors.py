import ast
from pathlib import Path

import pytest

from pagefetch import errors
from pagefetch.cache import FileCache
from pagefetch.network import _decompress, require_supported_scheme

PACKAGE = Path(__file__).resolve().parent.parent / "src" / "pagefetch"

RAISED = [
    pytest.param(
        lambda: require_supported_scheme("file:///etc/passwd"),
        errors.InvalidURL,
        id="a-scheme-the-package-will-not-fetch",
    ),
    pytest.param(
        lambda: require_supported_scheme("example.com/page"),
        errors.InvalidURL,
        id="a-url-with-no-scheme",
    ),
    pytest.param(
        lambda: _decompress(b"whatever", "br"),
        errors.UnsupportedEncoding,
        id="an-encoding-that-cannot-be-undone",
    ),
    pytest.param(
        lambda: _decompress(b"whatever", "gzip, br"),
        errors.UnsupportedEncoding,
        id="a-chained-encoding",
    ),
]


@pytest.mark.parametrize(("call", "expected"), RAISED)
def test_each_site_raises_its_own_type(call, expected):
    with pytest.raises(expected):
        call()


@pytest.mark.parametrize(("call", "expected"), RAISED)
def test_every_error_is_still_a_value_error(call, expected):
    # The whole point of the second base class. Callers written against the
    # old contract, and every assertion in the rest of the suite, keep
    # working — so this is a change nobody has to notice.
    assert issubclass(expected, ValueError)
    with pytest.raises(ValueError):
        call()


@pytest.mark.parametrize(("call", "expected"), RAISED)
def test_every_error_answers_to_the_base(call, expected):
    assert issubclass(expected, errors.PagefetchError)
    with pytest.raises(errors.PagefetchError):
        call()


def test_a_bad_cache_dir_is_its_own_type(tmp_path):
    target = tmp_path / "not-a-dir"
    target.write_text("", encoding="utf-8")
    with pytest.raises(errors.CacheDirError):
        FileCache(cache_dir=target).ensure_dir()


def test_two_failures_that_were_indistinguishable_now_are(tmp_path):
    # Both of these were a bare ValueError, so a caller wanting to retry a
    # bad cache directory while letting a bad URL through had nothing to
    # branch on but the message text. This is what the types buy.
    target = tmp_path / "not-a-dir"
    target.write_text("", encoding="utf-8")

    with pytest.raises(errors.CacheDirError):
        FileCache(cache_dir=target).ensure_dir()
    with pytest.raises(errors.InvalidURL):
        require_supported_scheme("ftp://example.com")

    assert not issubclass(errors.CacheDirError, errors.InvalidURL)
    assert not issubclass(errors.InvalidURL, errors.CacheDirError)


def test_the_type_survives_a_reworded_message():
    # The assertion names the failure rather than quoting it, so editing
    # the user-facing text cannot break this test. Twenty-two assertions
    # elsewhere in the suite still quote a message, and rewording one of
    # them breaks two tests that were never about wording.
    with pytest.raises(errors.InvalidURL) as caught:
        require_supported_scheme("ftp://example.com")

    assert "ftp" in str(caught.value)


def _raised_names(path: Path) -> list[str]:
    """Return the name of every exception type raised in one module."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise) or node.exc is None:
            continue

        exc = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
        name = getattr(exc, "id", None) or getattr(exc, "attr", None)
        if name is not None:
            names.append(name)

    return names


def test_the_package_raises_nothing_outside_the_contract():
    # The guard that keeps this from decaying: a bare `raise ValueError`
    # added later would leave one failure the hierarchy cannot describe,
    # and nothing else in the gate would notice.
    declared = {
        name
        for name, obj in vars(errors).items()
        if isinstance(obj, type) and issubclass(obj, errors.PagefetchError)
    }

    escaping = {
        f"{path.name}: {name}"
        for path in sorted(PACKAGE.glob("*.py"))
        for name in _raised_names(path)
        if name not in declared
    }
    assert escaping == set()
