"""Command-line interface for pagefetch.

Thin wrapper over NetworkFetcher.

Usage:
    py -m pagefetch <url>                          # single URL, auto mode
    py -m pagefetch <url> --format html            # raw HTML output
    py -m pagefetch <url> --format text            # stripped text (default)
    py -m pagefetch <url> --http                   # force plain HTTP
    py -m pagefetch <url> --js                     # force a JS-rendering browser
    py -m pagefetch <url> --headed                 # force bot bypass (needs display)
    py -m pagefetch <url> --headless               # force bot bypass (no display)
    py -m pagefetch <url> --wait 5000              # extra wait (ms)
    py -m pagefetch <url> --no-cache               # bypass cache

    py -m pagefetch --batch urls.txt               # batch from file
    py -m pagefetch --batch urls.txt --headed      # batch with bot bypass
    py -m pagefetch --batch urls.txt --output-dir out/  # save to files
    py -m pagefetch url1 url2 url3                 # batch from args
    echo url | py -m pagefetch --batch -           # batch from stdin

    py -m pagefetch --clean-cache                  # purge junk cache entries
    py -m pagefetch --clean-cache --dry-run        # list junk, delete nothing

    py -m pagefetch <url> --cache-dir DIR          # use a specific cache dir
                                                   # (overrides $PAGEFETCH_CACHE_DIR)

Transport flags may be combined, in any order. The most escalated one wins:
--headless over --headed over --js over --http.

Exit codes:
    0   every requested URL returned content
    1   nothing came back, or the arguments were rejected
    2   a batch returned content for some URLs but not all
"""

import sys
from pathlib import Path

from .cache import FileCache
from .detection import is_bot_blocked, is_error_page
from .network import NetworkFetcher
from .source import DEFAULT_WAIT_MS, ContentMode, FetchOptions, Transport

# argv[0] is the program name, so anything useful needs at least one more.
_MIN_ARGV_WITH_TARGET = 2

# Exit codes. A fetch that returns nothing used to exit 0, so a caller
# writing `pagefetch "$url" > page.txt && process page.txt` processed an
# empty file and never knew. Partial batch failure gets its own code
# because "some pages are missing" and "nothing came back" call for
# different handling in a pipeline.
EXIT_OK = 0
EXIT_ALL_FAILED = 1
EXIT_PARTIAL = 2

_VALUE_FLAGS = {"--wait", "--batch", "--output-dir", "--cache-dir", "--format"}
_BARE_FLAGS = {
    "--no-cache",
    "--http",
    "--js",
    "--headed",
    "--headless",
    "--clean-cache",
    "--dry-run",
    "--help",
}
_HELP_FLAGS = {"--help", "-h"}

# The accepted --format values. ContentMode is the library's type; this
# maps the CLI's spelling onto it so the two can be named independently.
_FORMATS = {"text": ContentMode.TEXT, "html": ContentMode.HTML}


def _parse_transport(argv: list[str]) -> Transport:
    """The transport to force, or AUTO when no transport flag is given.

    Flags passed together resolve to the most escalated one rather than
    being rejected, which is what the CLI has always done.
    """
    if "--headless" in argv:
        return Transport.HEADLESS
    if "--headed" in argv:
        return Transport.HEADED
    if "--js" in argv:
        return Transport.JS
    if "--http" in argv:
        return Transport.HTTP
    return Transport.AUTO


def _parse_wait_ms(argv: list[str]) -> int:
    """Milliseconds for --wait, defaulting to DEFAULT_WAIT_MS.

    Raises ValueError so main() reports it the way every other bad
    argument is reported. Parsing this inline used to put an unguarded
    int() in main's body, so `--wait abc` produced a traceback where an
    unusable --cache-dir produced a clean message.
    """
    raw = _flag_value(argv, "--wait", expects="a whole number of milliseconds")
    if raw is None:
        return DEFAULT_WAIT_MS
    try:
        wait_ms = int(raw)
    except ValueError:
        raise ValueError(
            f"--wait expects a whole number of milliseconds, got {raw!r}"
        ) from None
    if wait_ms < 0:
        raise ValueError(f"--wait cannot be negative, got {wait_ms}")
    return wait_ms


def _parse_mode(argv: list[str]) -> ContentMode:
    """The output format for --format, defaulting to text.

    Raises ValueError so main() reports it like every other bad argument.
    Absence and emptiness are told apart by _flag_value, so None here
    means the flag was not given at all.
    """
    accepted = ", ".join(sorted(_FORMATS))
    raw = _flag_value(argv, "--format", expects=f"one of: {accepted}")
    if raw is None:
        return ContentMode.TEXT
    try:
        return _FORMATS[raw]
    except KeyError:
        raise ValueError(f"--format expects one of: {accepted}, got {raw!r}") from None


def _flag_value(argv: list[str], flag: str, expects: str = "a value") -> str | None:
    """The value following `flag`, or None when the flag is absent.

    Absence and emptiness are told apart here rather than at each call
    site, because every call site tells them apart wrongly. Returning
    None for both used to mean `pagefetch <url> --wait` ran with
    DEFAULT_WAIT_MS and exited 0 — silently substituting the default the
    user was explicitly reaching past. `--cache-dir` and `--output-dir`
    had the same shape.

    Two ways to arrive empty, one verdict: the flag can trail the
    argument list with nothing after it, or carry a value that is the
    empty string. Neither is a flag the user did not pass.

    `expects` completes the message, so a caller that knows what it
    wants says so: "--format expects one of: html, text".
    """
    if flag not in argv:
        return None
    idx = argv.index(flag)
    if idx + 1 >= len(argv):
        raise ValueError(f"{flag} expects {expects}")
    value = argv[idx + 1]

    # An explicitly empty value is the same mistake arriving by the other
    # route: `--cache-dir "$UNSET"` is a value the caller meant to pass,
    # and every call site below truth-tested it back into the None an
    # absent flag produces. No flag here accepts an empty value.
    if value == "":
        raise ValueError(f"{flag} expects {expects}, got an empty value")
    return value


def _unknown_flags(argv: list[str]) -> list[str]:
    """Arguments that look like flags but are not recognized.

    Skips the value that follows a value flag, exactly as _collect_urls
    does, so `--batch -` does not report "-" and a value that happens to
    start with a dash is never read as a flag.
    """
    unknown: list[str] = []
    skip_next = False
    for arg in argv[1:]:
        if skip_next:
            skip_next = False
            continue
        if arg in _VALUE_FLAGS:
            skip_next = True
            continue
        if arg.startswith("--") and arg not in _BARE_FLAGS:
            unknown.append(arg)
    return unknown


def _collect_urls(argv: list[str], batch_file: str | None) -> list[str]:
    urls: list[str] = []
    skip_next = False
    for arg in argv[1:]:
        if skip_next:
            skip_next = False
            continue
        if arg in _VALUE_FLAGS:
            skip_next = True
            continue
        if arg.startswith("--"):
            continue
        urls.append(arg)

    if batch_file:
        if batch_file == "-":
            lines = sys.stdin
        else:
            batch_path = Path(batch_file)
            if not batch_path.exists():
                print(f"Error: batch file not found: {batch_file}", file=sys.stderr)
                sys.exit(EXIT_ALL_FAILED)
            lines = batch_path.read_text(encoding="utf-8").splitlines()

        # Blank lines and # comments let a URL list be annotated and
        # partially disabled without deleting entries.
        for raw_line in lines:
            line = raw_line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


def _classify_junk(body: str) -> str | None:
    """Reason a cached body is junk, or None to keep it.

    Order matters only for the label — a page that is both is reported as
    bot-blocked.
    """
    if is_bot_blocked(body):
        return "bot-blocked"
    if is_error_page(body):
        return "404/error"
    return None


def _make_cache(argv: list[str]) -> FileCache:
    """Build a FileCache honoring --cache-dir.

    A CLI value is passed as the explicit cache_dir (highest precedence:
    CLI > env > default); absent the flag, FileCache resolves the env var
    / default itself.
    """
    cli_dir = _flag_value(argv, "--cache-dir", expects="a directory path")

    # Forward the raw value, including "". _flag_value tells absence from
    # emptiness; converting or truth-testing here collapses them again and
    # hands FileCache the same None an absent flag produces.
    return FileCache(cache_dir=cli_dir)


def _clean_cache(cache: FileCache, dry_run: bool) -> None:
    """Sweep the cache of bot-blocked / 404 entries, printing a summary."""
    report = cache.clean(_classify_junk, dry_run=dry_run)
    verb = "would remove" if dry_run else "removed"
    if report.removed:
        print(f"{verb} {len(report.removed)} junk entries:", file=sys.stderr)
        for path, reason in report.removed:
            print(f"    {path.name}  ({reason})", file=sys.stderr)
    print(
        f"{verb} {len(report.removed)} junk entries, kept {report.kept}",
        file=sys.stderr,
    )


def main() -> None:
    """Run the CLI: parse argv, fetch or clean, exit with a status code."""
    argv = sys.argv
    if len(argv) < _MIN_ARGV_WITH_TARGET:
        print(__doc__)
        sys.exit(EXIT_ALL_FAILED)

    if _HELP_FLAGS.intersection(argv[1:]):
        print(__doc__)
        return

    # Checked before anything else acts on argv. A discarded flag used to
    # mean the command ran with the default instead — and for --clean-cache
    # that inverts the operation, since a mistyped --dry-run deletes.
    unknown = _unknown_flags(argv)
    if unknown:
        print(f"Error: unknown flag: {', '.join(unknown)}", file=sys.stderr)
        print("Run `py -m pagefetch --help` for usage.", file=sys.stderr)
        sys.exit(EXIT_ALL_FAILED)

    # Every value flag is read here rather than deeper in, so a bad
    # argument never reaches a fetch and always reports the same way.
    # --output-dir and --batch are read before the --clean-cache branch
    # for the reason _unknown_flags runs before everything: a value flag
    # that is quietly discarded lets a mistyped command run as a
    # different one.
    try:
        cache = _make_cache(argv)
        wait_ms = _parse_wait_ms(argv)
        mode = _parse_mode(argv)
        output_dir = _flag_value(argv, "--output-dir", expects="a directory path")
        batch_file = _flag_value(argv, "--batch", expects="a file path")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(EXIT_ALL_FAILED)

    if "--clean-cache" in argv:
        _clean_cache(cache, dry_run="--dry-run" in argv)
        return

    transport = _parse_transport(argv)
    use_cache = "--no-cache" not in argv

    urls = _collect_urls(argv, batch_file)
    if not urls:
        print(__doc__)
        sys.exit(EXIT_ALL_FAILED)

    opts = FetchOptions(
        mode=mode, transport=transport, wait_ms=wait_ms, use_cache=use_cache
    )
    fetcher = NetworkFetcher(cache=cache)

    # An unsupported scheme is a typo in the arguments, not a runtime
    # fault — report it the way the cache-dir errors above are reported
    # rather than with a traceback.
    try:
        if len(urls) == 1 and not output_dir:
            result = fetcher.fetch(urls[0], opts)
            if result.content:
                sys.stdout.buffer.write(
                    result.content.encode("utf-8", errors="replace")
                )
                sys.stdout.buffer.write(b"\n")
            if not result.ok:
                print(f"Error: no content fetched for {result.url}", file=sys.stderr)
                sys.exit(EXIT_ALL_FAILED)
            return

        results = fetcher.fetch_batch(urls, opts)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(EXIT_ALL_FAILED)

    _write_batch_output(results, output_dir, mode)
    sys.exit(_batch_exit_code(results))


def _batch_exit_code(results) -> int:
    """Grade a batch by how many URLs returned content.

    EXIT_OK if every URL did, EXIT_ALL_FAILED if none did, EXIT_PARTIAL
    otherwise. An empty batch is not a failure.
    """
    if not results:
        return EXIT_OK
    failed = sum(1 for r in results if not r.ok)
    if failed == 0:
        return EXIT_OK
    return EXIT_ALL_FAILED if failed == len(results) else EXIT_PARTIAL


def _write_batch_output(results, output_dir: str | None, mode: ContentMode) -> None:
    """Write the batch results.

    One file per URL to a directory (hash-named), or delimited blocks to
    stdout.
    """
    out_path = Path(output_dir) if output_dir else None
    if out_path:
        out_path.mkdir(parents=True, exist_ok=True)

    suffix = ".html" if mode is ContentMode.HTML else ".txt"
    for result in results:
        if not result.content:
            continue
        if out_path:
            fname = FileCache.url_hash(result.url) + suffix
            (out_path / fname).write_text(result.content, encoding="utf-8")
            print(
                f"[batch]   -> {fname} ({len(result.content)} bytes)", file=sys.stderr
            )
        else:
            sys.stdout.buffer.write(f"--- {result.url} ---\n".encode())
            sys.stdout.buffer.write(result.content.encode("utf-8", errors="replace"))
            sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()
