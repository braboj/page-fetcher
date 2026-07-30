"""CLI flag-validation tests.

Unknown flags were silently discarded, so every typo ran the command with
the default instead. On --clean-cache that inverts the operation: a
mistyped --dry-run deletes.
"""

import io

import pytest

from pagefetch import ContentMode, FileCache, Transport
from pagefetch.__main__ import (
    DEFAULT_WAIT_MS,
    EXIT_ALL_FAILED,
    _collect_urls,
    _parse_transport,
    _parse_wait_ms,
    _unknown_flags,
    main,
)


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


# --- _parse_transport -------------------------------------------------


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["pagefetch", "https://x.test"], Transport.AUTO),
        (["pagefetch", "https://x.test", "--js"], Transport.PLAYWRIGHT),
        (["pagefetch", "https://x.test", "--nodriver"], Transport.NODRIVER),
        (["pagefetch", "https://x.test", "--uc"], Transport.UC),
    ],
)
def test_transport_selection(argv, expected):
    assert _parse_transport(argv) == expected


@pytest.mark.parametrize(
    ("flags", "expected"),
    [
        (["--uc", "--nodriver"], Transport.UC),
        (["--nodriver", "--js"], Transport.NODRIVER),
        (["--uc", "--js"], Transport.UC),
        (["--js", "--uc", "--nodriver"], Transport.UC),
    ],
)
def test_transport_precedence_is_slowest_wins(flags, expected):
    # Order in argv does not matter; the ladder's own order decides. The
    # slowest, most evasive tier wins, on the reasoning that someone who
    # asked for it at all has already hit a wall the faster ones cannot
    # clear.
    assert _parse_transport(["pagefetch", "https://x.test", *flags]) == expected


# --- --wait -----------------------------------------------------------


def test_wait_defaults_when_absent():
    assert _parse_wait_ms(["pagefetch", "https://x.test"]) == DEFAULT_WAIT_MS


def test_wait_accepts_a_whole_number():
    assert _parse_wait_ms(["pagefetch", "https://x.test", "--wait", "5000"]) == 5000


def test_wait_accepts_zero():
    assert _parse_wait_ms(["pagefetch", "https://x.test", "--wait", "0"]) == 0


@pytest.mark.parametrize("value", ["abc", "1.5", "", "5000ms"])
def test_wait_rejects_a_non_integer(value):
    with pytest.raises(ValueError, match="whole number of milliseconds"):
        _parse_wait_ms(["pagefetch", "https://x.test", "--wait", value])


def test_wait_rejects_a_negative_value():
    with pytest.raises(ValueError, match="cannot be negative"):
        _parse_wait_ms(["pagefetch", "https://x.test", "--wait", "-1000"])


def test_bad_wait_exits_cleanly_rather_than_tracebacking(monkeypatch, capsys):
    # #24: the int() was outside the try, so this produced a traceback
    # where every other bad argument produced "Error: ...".
    code = _run(monkeypatch, ["https://x.test", "--wait", "abc"])
    assert code == EXIT_ALL_FAILED
    err = capsys.readouterr().err
    assert err.startswith("Error: --wait expects a whole number")
    assert "Traceback" not in err


# --- batch input ------------------------------------------------------


def test_batch_file_is_read_one_url_per_line(tmp_path):
    listing = tmp_path / "urls.txt"
    listing.write_text("https://a.test\nhttps://b.test\n", encoding="utf-8")

    urls = _collect_urls(["pagefetch", "--batch", str(listing)], str(listing))

    assert urls == ["https://a.test", "https://b.test"]


def test_batch_file_skips_blanks_and_comments(tmp_path):
    listing = tmp_path / "urls.txt"
    listing.write_text(
        "# a note\n\nhttps://a.test\n   \n#https://disabled.test\n  https://b.test  \n",
        encoding="utf-8",
    )

    urls = _collect_urls(["pagefetch", "--batch", str(listing)], str(listing))

    assert urls == ["https://a.test", "https://b.test"]


def test_batch_file_combines_with_urls_given_as_arguments(tmp_path):
    listing = tmp_path / "urls.txt"
    listing.write_text("https://b.test\n", encoding="utf-8")

    urls = _collect_urls(
        ["pagefetch", "https://a.test", "--batch", str(listing)], str(listing)
    )

    assert urls == ["https://a.test", "https://b.test"]


def test_batch_reads_stdin_when_the_file_is_a_dash(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("https://a.test\n# skip\n\n"))

    urls = _collect_urls(["pagefetch", "--batch", "-"], "-")

    assert urls == ["https://a.test"]


def test_missing_batch_file_exits_with_an_error(tmp_path, capsys):
    missing = tmp_path / "nope.txt"

    with pytest.raises(SystemExit) as exc:
        _collect_urls(["pagefetch", "--batch", str(missing)], str(missing))

    assert exc.value.code == EXIT_ALL_FAILED
    assert "Error: batch file not found" in capsys.readouterr().err


# --- no target --------------------------------------------------------


def test_no_arguments_prints_usage_and_exits_non_zero(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["pagefetch"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == EXIT_ALL_FAILED
    assert "py -m pagefetch <url>" in capsys.readouterr().out


def test_flags_without_a_url_print_usage_and_exit_non_zero(monkeypatch, capsys):
    # Arguments were given, so the argv-length check passes, but nothing
    # in them is a URL to fetch.
    code = _run(monkeypatch, ["--html", "--no-cache"])
    assert code == EXIT_ALL_FAILED
    assert "py -m pagefetch <url>" in capsys.readouterr().out
