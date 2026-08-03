"""CLI flag-validation tests.

Unknown flags were silently discarded, so every typo ran the command with
the default instead. On --clean-cache that inverts the operation: a
mistyped --dry-run deletes.
"""

import io

import pytest

from pagefetch import ContentMode, FileCache, Transport
from pagefetch.__main__ import (
    _VALUE_FLAGS,
    DEFAULT_WAIT_MS,
    EXIT_ALL_FAILED,
    _collect_urls,
    _flag_value,
    _parse_mode,
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
        (["pagefetch", "https://x.test", "--format", "html"], []),
        (["pagefetch", "--clean-cache", "--dry-run"], []),
        (["pagefetch", "https://x.test", "--wait", "500"], []),
        (["pagefetch", "--batch", "-"], []),
        (["pagefetch", "--clean-cache", "--dyr-run"], ["--dyr-run"]),
        (["pagefetch", "https://x.test", "--fomrat", "html"], ["--fomrat"]),
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


# --- an explicitly empty value ---------------------------------------


@pytest.mark.parametrize(
    ("flag", "expects"),
    [
        ("--cache-dir", "a directory path"),
        ("--output-dir", "a directory path"),
        ("--batch", "a file path"),
        ("--wait", "a whole number of milliseconds"),
        ("--format", "one of"),
    ],
)
def test_empty_flag_value_is_rejected(monkeypatch, capsys, flag, expects):
    # #98 rejected a value flag with nothing after it. An explicitly empty
    # value took the other route: _flag_value returned "", and every call
    # site truth-tested it back into the None an absent flag produces.
    monkeypatch.delenv("PAGEFETCH_CACHE_DIR", raising=False)

    code = _run(monkeypatch, ["https://x.test", flag, ""])

    assert code == EXIT_ALL_FAILED
    err = capsys.readouterr().err
    assert "empty value" in err
    assert flag in err
    assert expects in err


def test_empty_cache_dir_value_does_not_sweep_the_working_directory(
    tmp_path, monkeypatch, capsys
):
    # The reason it is not merely a precedence nit: the silent fallback
    # ran the sweep somewhere the caller never named.
    monkeypatch.delenv("PAGEFETCH_CACHE_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    bystander = tmp_path / "page.html"
    bystander.write_text("<title>404 Not Found</title>", encoding="utf-8")

    code = _run(monkeypatch, ["--clean-cache", "--cache-dir", ""])

    assert code == EXIT_ALL_FAILED
    assert bystander.exists()
    assert "empty value" in capsys.readouterr().err


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
        (["pagefetch", "https://x.test", "--http"], Transport.HTTP),
        (["pagefetch", "https://x.test", "--js"], Transport.JS),
        (["pagefetch", "https://x.test", "--headed"], Transport.HEADED),
        (["pagefetch", "https://x.test", "--headless"], Transport.HEADLESS),
    ],
)
def test_transport_selection(argv, expected):
    assert _parse_transport(argv) == expected


@pytest.mark.parametrize(
    ("flags", "expected"),
    [
        (["--headless", "--headed"], Transport.HEADLESS),
        (["--headed", "--js"], Transport.HEADED),
        (["--headless", "--js"], Transport.HEADLESS),
        (["--js", "--headless", "--headed"], Transport.HEADLESS),
        (["--http", "--js"], Transport.JS),
        (["--http", "--headless"], Transport.HEADLESS),
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


def test_wait_without_a_value_is_rejected():
    # #98: this returned DEFAULT_WAIT_MS and exited 0, substituting the
    # default for the value the user was explicitly reaching past.
    with pytest.raises(ValueError, match="whole number of milliseconds"):
        _parse_wait_ms(["pagefetch", "https://x.test", "--wait"])


def test_bad_wait_exits_cleanly_rather_than_tracebacking(monkeypatch, capsys):
    # #24: the int() was outside the try, so this produced a traceback
    # where every other bad argument produced "Error: ...".
    code = _run(monkeypatch, ["https://x.test", "--wait", "abc"])
    assert code == EXIT_ALL_FAILED
    err = capsys.readouterr().err
    assert err.startswith("Error: --wait expects a whole number")
    assert "Traceback" not in err


# --- --format ---------------------------------------------------------


def test_format_defaults_to_text_when_absent():
    assert _parse_mode(["pagefetch", "https://x.test"]) is ContentMode.TEXT


@pytest.mark.parametrize(
    ("value", "expected"),
    [("text", ContentMode.TEXT), ("html", ContentMode.HTML)],
)
def test_format_accepts_both_modes(value, expected):
    assert _parse_mode(["pagefetch", "https://x.test", "--format", value]) is expected


@pytest.mark.parametrize("value", ["bogus", "HTML", "txt", ""])
def test_format_rejects_an_unknown_value(value):
    with pytest.raises(ValueError, match="expects one of: html, text"):
        _parse_mode(["pagefetch", "https://x.test", "--format", value])


def test_format_without_a_value_is_rejected():
    # Distinct from absence on purpose: falling back to the default here
    # would hand back exactly what the user was trying to override.
    with pytest.raises(ValueError, match="expects one of: html, text"):
        _parse_mode(["pagefetch", "https://x.test", "--format"])


def test_bad_format_exits_cleanly_rather_than_tracebacking(monkeypatch, capsys):
    code = _run(monkeypatch, ["https://x.test", "--format", "bogus"])
    assert code == EXIT_ALL_FAILED
    err = capsys.readouterr().err
    assert err.startswith("Error: --format expects one of: html, text")
    assert "Traceback" not in err


# --- a value flag with no value ---------------------------------------


def test_flag_value_returns_none_when_the_flag_is_absent():
    assert _flag_value(["pagefetch", "https://x.test"], "--cache-dir") is None


def test_flag_value_reads_the_following_argument():
    argv = ["pagefetch", "https://x.test", "--cache-dir", "cache"]
    assert _flag_value(argv, "--cache-dir") == "cache"


@pytest.mark.parametrize("flag", sorted(_VALUE_FLAGS))
def test_every_value_flag_rejects_a_missing_value(flag):
    # Parametrized over the set rather than a hand-written list, so a
    # value flag added later inherits the guard instead of repeating #98.
    with pytest.raises(ValueError, match=f"{flag} expects "):
        _flag_value(["pagefetch", "https://x.test", flag], flag)


@pytest.mark.parametrize(
    ("flag", "message"),
    [
        ("--wait", "Error: --wait expects a whole number of milliseconds"),
        ("--format", "Error: --format expects one of: html, text"),
        ("--cache-dir", "Error: --cache-dir expects a directory path"),
        ("--output-dir", "Error: --output-dir expects a directory path"),
        ("--batch", "Error: --batch expects a file path"),
    ],
)
def test_a_value_flag_with_no_value_exits_cleanly(monkeypatch, capsys, flag, message):
    # #98: --wait, --cache-dir and --output-dir each fell back to their
    # default and exited 0. --format already guarded; it is here to keep
    # the five messages in one place.
    code = _run(monkeypatch, ["https://x.test", flag])
    assert code == EXIT_ALL_FAILED
    err = capsys.readouterr().err
    assert err.startswith(message)
    assert "Traceback" not in err


def test_a_missing_value_is_rejected_before_clean_cache_acts(
    monkeypatch, capsys, tmp_path
):
    # --clean-cache deletes, so it must not run off a command line that
    # was already rejected — the same reason _unknown_flags runs first.
    code = _run(
        monkeypatch,
        ["--clean-cache", "--cache-dir", str(tmp_path), "--output-dir"],
    )
    assert code == EXIT_ALL_FAILED
    assert "--output-dir expects" in capsys.readouterr().err


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
    code = _run(monkeypatch, ["--format", "html", "--no-cache"])
    assert code == EXIT_ALL_FAILED
    assert "py -m pagefetch <url>" in capsys.readouterr().out
