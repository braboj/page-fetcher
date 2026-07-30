"""CLI flag-validation tests.

Unknown flags were silently discarded, so every typo ran the command with
the default instead. On --clean-cache that inverts the operation: a
mistyped --dry-run deletes.
"""

import pytest

from pagefetch import ContentMode, FileCache
from pagefetch.__main__ import EXIT_ALL_FAILED, _unknown_flags, main


def _run(monkeypatch, argv):
    monkeypatch.setattr("sys.argv", ["pagefetch", *argv])
    with pytest.raises(SystemExit) as exc:
        main()
    return exc.value.code


# --- _unknown_flags --------------------------------------------------


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["pagefetch", "https://x.test"], []),
        (["pagefetch", "https://x.test", "--html"], []),
        (["pagefetch", "--clean-cache", "--dry-run"], []),
        (["pagefetch", "https://x.test", "--wait", "500"], []),
        (["pagefetch", "--batch", "-"], []),
        (["pagefetch", "--clean-cache", "--dyr-run"], ["--dyr-run"]),
        (["pagefetch", "https://x.test", "--htlm"], ["--htlm"]),
        (["pagefetch", "https://x.test", "--no-cahce"], ["--no-cahce"]),
        (["pagefetch", "https://x.test", "--a", "--b"], ["--a", "--b"]),
    ],
)
def test_unknown_flags_detection(argv, expected):
    assert _unknown_flags(argv) == expected


def test_a_value_that_looks_like_a_flag_is_not_reported():
    # --cache-dir's value is consumed, so a dashed path is not a flag.
    assert (
        _unknown_flags(["pagefetch", "--cache-dir", "--weird", "https://x.test"]) == []
    )


# --- main() ----------------------------------------------------------


def test_unknown_flag_exits_with_error(monkeypatch, capsys):
    code = _run(monkeypatch, ["https://x.test", "--htlm"])
    assert code == EXIT_ALL_FAILED
    err = capsys.readouterr().err
    assert "unknown flag: --htlm" in err
    assert "--help" in err


def test_mistyped_dry_run_does_not_delete(tmp_path, monkeypatch, capsys):
    # The regression this ticket exists for: --dyr-run used to be discarded,
    # so the sweep ran for real against the flag meant to prevent it.
    monkeypatch.delenv("PAGEFETCH_CACHE_DIR", raising=False)
    target = tmp_path / "cache"
    cache = FileCache(cache_dir=target)
    cache.write("https://gone.test", ContentMode.HTML, "<title>404 Not Found</title>")

    code = _run(
        monkeypatch,
        ["--clean-cache", "--cache-dir", str(target), "--dyr-run"],
    )

    assert code == EXIT_ALL_FAILED
    assert cache.read("https://gone.test", ContentMode.HTML) is not None
    assert "unknown flag: --dyr-run" in capsys.readouterr().err


def test_unknown_flag_is_rejected_before_the_cache_is_built(tmp_path, monkeypatch):
    # Rejection happens before _make_cache, so an argv that is wrong in two
    # ways reports the flag rather than the cache dir — and no cache
    # directory is validated or created on the way to the error.
    monkeypatch.delenv("PAGEFETCH_CACHE_DIR", raising=False)
    a_file = tmp_path / "f.txt"
    a_file.write_text("x", encoding="utf-8")

    _run(monkeypatch, ["https://x.test", "--cache-dir", str(a_file), "--bogus"])


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_help_prints_usage_and_exits_zero(monkeypatch, capsys, flag):
    monkeypatch.setattr("sys.argv", ["pagefetch", flag])

    main()

    assert "py -m pagefetch <url>" in capsys.readouterr().out
