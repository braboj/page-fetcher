"""ChromeReaper attribution and lifetime.

The reaper kills processes, so the question it has to answer correctly is
"did this interpreter start that Chrome?". It used to answer by sampling
chrome.exe PIDs either side of a launch and claiming the difference, which
also claims a browser window the user opened during the fetch — observed
killing a real Chrome process during a plain `pytest` run, since
_start_nodriver_session samples for real even when the engine is a fake.

Nothing here starts a process. The process table is injected, so the
ancestry logic is exercised directly.
"""

import atexit

import pytest

from pagefetch import FileCache, NetworkFetcher
from pagefetch.chrome import ChromeReaper, default_reaper

# (pid, parent pid, image name) — the shape _process_table returns.
OURS = 1000


def _table(*rows):
    return list(rows)


# --- attribution ------------------------------------------------------


def test_chrome_launched_by_us_is_ours():
    table = _table((2000, OURS, "chrome.exe"))
    assert ChromeReaper._own_chrome_pids(table, OURS) == {2000}


def test_chrome_the_user_opened_is_not_ours():
    # The regression: explorer.exe started this one, not us.
    table = _table((2000, 500, "chrome.exe"), (500, 4, "explorer.exe"))
    assert ChromeReaper._own_chrome_pids(table, OURS) == set()


def test_renderer_children_of_our_browser_are_ours():
    # Chrome spawns a tree; killing only the top process leaves the rest.
    table = _table(
        (2000, OURS, "chrome.exe"),
        (2001, 2000, "chrome.exe"),
        (2002, 2000, "chrome.exe"),
        (2003, 2001, "chrome.exe"),
    )
    assert ChromeReaper._own_chrome_pids(table, OURS) == {2000, 2001, 2002, 2003}


def test_our_chrome_is_found_through_an_intermediate_process():
    # A driver may launch Chrome via a launcher stub rather than directly,
    # so the walk cannot assume the parent is chrome.exe or is us.
    table = _table(
        (1500, OURS, "chromedriver.exe"),
        (2000, 1500, "chrome.exe"),
    )
    assert ChromeReaper._own_chrome_pids(table, OURS) == {2000}


def test_our_chrome_and_the_users_chrome_are_told_apart():
    table = _table(
        (2000, OURS, "chrome.exe"),
        (2001, 2000, "chrome.exe"),
        (3000, 500, "chrome.exe"),
        (3001, 3000, "chrome.exe"),
        (500, 4, "explorer.exe"),
    )
    assert ChromeReaper._own_chrome_pids(table, OURS) == {2000, 2001}


def test_non_chrome_descendants_are_not_claimed():
    table = _table((2000, OURS, "python.exe"), (2001, 2000, "notepad.exe"))
    assert ChromeReaper._own_chrome_pids(table, OURS) == set()


def test_a_parent_cycle_does_not_hang():
    # PIDs get reused and the table is a snapshot, so a cycle is possible.
    table = _table((2000, 2001, "chrome.exe"), (2001, 2000, "chrome.exe"))
    assert ChromeReaper._own_chrome_pids(table, OURS) == set()


def test_a_self_parenting_row_does_not_hang():
    table = _table((2000, 2000, "chrome.exe"))
    assert ChromeReaper._own_chrome_pids(table, OURS) == set()


def test_an_empty_table_claims_nothing():
    # The non-Windows and query-failure case: find nothing, kill nothing.
    assert ChromeReaper._own_chrome_pids([], OURS) == set()


def test_image_name_matching_is_case_insensitive_via_the_table():
    # _process_table lowercases the name column, so matching is exact
    # against a known-lowercase constant rather than guessing at casing.
    table = _table((2000, OURS, "chrome.exe"))
    assert ChromeReaper._own_chrome_pids(table, OURS) == {2000}


# --- reading the process table ----------------------------------------


class _Completed:
    def __init__(self, stdout: str):
        self.stdout = stdout


def _stub_run(monkeypatch, stdout="", raises=None):
    def fake(*args, **kwargs):
        if raises is not None:
            raise raises
        return _Completed(stdout)

    monkeypatch.setattr("subprocess.run", fake)


def test_process_table_parses_rows(monkeypatch):
    monkeypatch.setattr("sys.platform", "win32")
    _stub_run(monkeypatch, "2000,1000,chrome.exe\n1000,500,python.exe\n")

    assert ChromeReaper._process_table() == [
        (2000, 1000, "chrome.exe"),
        (1000, 500, "python.exe"),
    ]


def test_process_table_lowercases_the_image_name(monkeypatch):
    # Windows reports Chrome.exe / CHROME.EXE depending on how it started,
    # and ownership matching compares against a lowercase constant.
    monkeypatch.setattr("sys.platform", "win32")
    _stub_run(monkeypatch, "2000,1000,Chrome.EXE\n")

    assert ChromeReaper._process_table() == [(2000, 1000, "chrome.exe")]


@pytest.mark.parametrize(
    "line",
    ["", "garbage", "2000,1000", "notanumber,1000,chrome.exe", "2000,x,chrome.exe"],
)
def test_process_table_skips_malformed_rows(monkeypatch, line):
    monkeypatch.setattr("sys.platform", "win32")
    _stub_run(monkeypatch, f"{line}\n2000,1000,chrome.exe\n")

    assert ChromeReaper._process_table() == [(2000, 1000, "chrome.exe")]


def test_process_table_keeps_a_name_containing_a_comma(monkeypatch):
    # The name is the last field and is split off with maxsplit, so a
    # comma inside it does not shift the numeric columns.
    monkeypatch.setattr("sys.platform", "win32")
    _stub_run(monkeypatch, "2000,1000,odd,name.exe\n")

    assert ChromeReaper._process_table() == [(2000, 1000, "odd,name.exe")]


def test_process_table_is_empty_off_windows(monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    _stub_run(monkeypatch, "2000,1000,chrome.exe\n")

    # No query at all — the reaper is a documented no-op off Windows.
    assert ChromeReaper._process_table() == []


def test_process_table_is_empty_when_the_query_fails(monkeypatch):
    monkeypatch.setattr("sys.platform", "win32")
    _stub_run(monkeypatch, raises=OSError("powershell not found"))

    # Failing closed: nothing found means nothing killed.
    assert ChromeReaper._process_table() == []


def test_running_chrome_pids_parses_tasklist_csv(monkeypatch):
    _stub_run(monkeypatch, '"chrome.exe","2000","Console","1","50,000 K"\n')

    assert ChromeReaper.running_chrome_pids() == {2000}


def test_running_chrome_pids_is_empty_when_tasklist_fails(monkeypatch):
    _stub_run(monkeypatch, raises=OSError("tasklist not found"))

    assert ChromeReaper.running_chrome_pids() == set()


def test_running_chrome_pids_skips_the_no_tasks_banner(monkeypatch):
    # tasklist prints a plain-text line, not CSV, when the filter matches
    # nothing.
    _stub_run(monkeypatch, "INFO: No tasks are running which match.\n")

    assert ChromeReaper.running_chrome_pids() == set()


# --- tracking ---------------------------------------------------------


def test_track_new_since_requires_both_new_and_ours(monkeypatch):
    reaper = ChromeReaper(register_atexit=False)
    monkeypatch.setattr(
        ChromeReaper, "own_chrome_pids", classmethod(lambda cls: {2000, 2001})
    )

    reaper.track_new_since({2001})

    # 2001 existed before the launch; 2000 did not.
    assert reaper._spawned_pids == {2000}


def test_track_new_since_ignores_chrome_that_is_not_ours(monkeypatch):
    reaper = ChromeReaper(register_atexit=False)
    monkeypatch.setattr(ChromeReaper, "own_chrome_pids", classmethod(lambda cls: set()))

    reaper.track_new_since(set())

    assert reaper._spawned_pids == set()


def test_cleanup_with_nothing_tracked_kills_nothing(monkeypatch):
    reaper = ChromeReaper(register_atexit=False)
    called = []
    monkeypatch.setattr(
        ChromeReaper, "running_chrome_pids", classmethod(lambda cls: called.append(1))
    )

    reaper.cleanup()

    # Not even a process query — the common case must cost nothing.
    assert called == []


def test_cleanup_kills_only_tracked_survivors(monkeypatch, capsys):
    reaper = ChromeReaper(register_atexit=False)
    reaper._spawned_pids = {2000, 2001}
    monkeypatch.setattr(
        ChromeReaper, "running_chrome_pids", classmethod(lambda cls: {2000, 3000})
    )
    killed: list[int] = []
    monkeypatch.setattr("os.kill", lambda pid, sig: killed.append(pid))

    reaper.cleanup()

    # 2001 already exited; 3000 is not ours.
    assert killed == [2000]
    assert "Killed 1 orphaned Chrome process(es)" in capsys.readouterr().err


# --- lifetime ---------------------------------------------------------


def test_fetchers_share_one_reaper_and_one_atexit_handler():
    # Every NetworkFetcher used to build its own reaper and register its
    # own atexit handler, none ever removed: 100 fetchers meant 100
    # handlers and 100 process queries at exit.
    # Create the shared reaper first, so what is measured is the cost of
    # the fetchers rather than the one-off cost of the singleton.
    default_reaper()
    before = atexit._ncallbacks()
    cache = FileCache(cache_dir=None)
    fetchers = [NetworkFetcher(cache=cache) for _ in range(50)]

    assert atexit._ncallbacks() == before
    assert len({id(f._reaper) for f in fetchers}) == 1


def test_default_reaper_is_a_singleton():
    assert default_reaper() is default_reaper()


def test_an_injected_reaper_still_wins():
    mine = ChromeReaper(register_atexit=False)
    fetcher = NetworkFetcher(cache=FileCache(cache_dir=None), reaper=mine)
    assert fetcher._reaper is mine


@pytest.mark.parametrize("register", [True, False])
def test_register_atexit_flag_is_honored(register):
    before = atexit._ncallbacks()
    reaper = ChromeReaper(register_atexit=register)
    assert atexit._ncallbacks() == before + (1 if register else 0)
    if register:
        atexit.unregister(reaper.cleanup)
