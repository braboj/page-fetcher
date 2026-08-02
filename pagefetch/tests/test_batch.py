"""Batch fetching: session lifecycle, per-URL dispatch, and teardown.

The batch path runs a persistent browser so a run of bot-protected pages
pays the launch cost once instead of per URL. That makes it the part of
the fetcher most likely to leak a process or a loop, and — until these
tests — the part with no coverage at all.

Nothing here launches a browser. The optional engines are injected as
fake modules in `sys.modules`, which is what the tier code imports
lazily, so the real ones are never touched.
"""

import asyncio
import sys

import pytest

from pagefetch import ContentMode, FetchOptions, NetworkFetcher, Transport
from pagefetch.network import _BOT_BLOCKED, _BatchSession


class _FakeBrowser:
    """Stands in for a started Nodriver browser."""

    def __init__(self) -> None:
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


class _FakeNodriverModule:
    """Stands in for the `nodriver` package."""

    def __init__(self, browser: _FakeBrowser | None = None, fail: bool = False):
        self.browser = browser or _FakeBrowser()
        self.fail = fail
        self.started = False

    async def start(self, headless: bool = False):
        if self.fail:
            raise RuntimeError("chrome would not launch")
        self.started = True
        return self.browser


class _FakeSbContext:
    """Stands in for the SB(...) context manager."""

    def __init__(self) -> None:
        self.entered = False
        self.exited = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, *exc_info):
        self.exited = True
        return False


class _FakeSeleniumBaseModule:
    def __init__(self, context: _FakeSbContext | None = None):
        self.context = context or _FakeSbContext()
        self.kwargs: dict | None = None

    def SB(self, **kwargs):
        self.kwargs = kwargs
        return self.context


@pytest.fixture
def fetcher(cache):
    return NetworkFetcher(cache=cache)


@pytest.fixture
def urllib_tier(monkeypatch):
    """Control what tier 1 returns, per URL, and record the calls."""

    def install(fetcher, results: dict[str, str] | str):
        calls: list[str] = []

        def fake(url, mode):
            calls.append(url)
            if isinstance(results, str):
                return results
            return results.get(url, "")

        monkeypatch.setattr(fetcher, "_fetch_urllib", fake)
        return calls

    return install


@pytest.fixture
def no_browser_tiers(monkeypatch):
    """Make the non-urllib tiers inert so nothing can launch."""

    def install(fetcher):
        monkeypatch.setattr(fetcher, "_fetch_playwright", lambda *a, **k: "")
        monkeypatch.setattr(fetcher, "_fetch_nodriver", lambda *a, **k: "")
        monkeypatch.setattr(fetcher, "_fetch_uc", lambda *a, **k: "")

    return install


# --- the plain path ---------------------------------------------------


def test_empty_batch_returns_no_results(fetcher):
    assert fetcher.fetch_batch([]) == []


def test_results_come_back_in_input_order(fetcher, urllib_tier, no_browser_tiers):
    no_browser_tiers(fetcher)
    urls = ["https://c.test", "https://a.test", "https://b.test"]
    urllib_tier(fetcher, {u: f"body {u}" for u in urls})
    results = fetcher.fetch_batch(urls, FetchOptions(use_cache=False))
    assert [r.url for r in results] == urls
    assert [r.content for r in results] == [f"body {u}" for u in urls]


def test_each_result_reports_its_tier_and_ok_flag(
    fetcher, urllib_tier, no_browser_tiers
):
    no_browser_tiers(fetcher)
    urllib_tier(fetcher, {"https://a.test": "body"})
    results = fetcher.fetch_batch(
        ["https://a.test", "https://missing.test"], FetchOptions(use_cache=False)
    )
    assert (results[0].ok, results[0].tier_used) == (True, "http")
    assert (results[1].ok, results[1].tier_used) == (False, "none")
    assert results[1].content == ""


def test_successful_pages_are_cached_and_failures_are_not(
    fetcher, urllib_tier, no_browser_tiers, cache
):
    no_browser_tiers(fetcher)
    urllib_tier(fetcher, {"https://a.test": "body"})
    fetcher.fetch_batch(
        ["https://a.test", "https://missing.test"], FetchOptions(use_cache=True)
    )
    assert cache.read("https://a.test", ContentMode.TEXT) == "body"
    assert cache.read("https://missing.test", ContentMode.TEXT) is None


def test_use_cache_false_still_populates_the_cache(
    fetcher, urllib_tier, no_browser_tiers, cache
):
    # Surprising but deliberate, and the same in the single-URL path:
    # use_cache gates whether a cached body is *served*, not whether a
    # fresh one is stored. A `--no-cache` run is therefore a refresh, not
    # a bypass. Pinned so a future tidy-up cannot silently change it.
    no_browser_tiers(fetcher)
    urllib_tier(fetcher, {"https://a.test": "fresh"})
    cache.write("https://a.test", ContentMode.TEXT, "stale")
    results = fetcher.fetch_batch(["https://a.test"], FetchOptions(use_cache=False))
    assert results[0].content == "fresh"
    assert cache.read("https://a.test", ContentMode.TEXT) == "fresh"


# --- deciding which session to open -----------------------------------


def test_auto_mode_probes_the_first_url_only(fetcher, urllib_tier, no_browser_tiers):
    # The probe decides whether a persistent bot-tier session is worth
    # launching. It must not fetch every URL twice.
    no_browser_tiers(fetcher)
    urls = ["https://a.test", "https://b.test", "https://c.test"]
    calls = urllib_tier(fetcher, {u: "body" for u in urls})
    fetcher.fetch_batch(urls, FetchOptions(use_cache=False))
    # One probe of the first URL, then one fetch per URL.
    assert calls == ["https://a.test", *urls]


def test_auto_mode_starts_nodriver_when_the_probe_is_bot_blocked(
    fetcher, urllib_tier, monkeypatch
):
    nodriver = _FakeNodriverModule()
    monkeypatch.setitem(sys.modules, "nodriver", nodriver)
    urllib_tier(fetcher, _BOT_BLOCKED)

    async def fake_fetch(browser, url, mode, wait_ms):
        return f"nodriver body for {url}"

    monkeypatch.setattr(fetcher, "_nodriver_fetch_with_browser", fake_fetch)

    results = fetcher.fetch_batch(["https://a.test"], FetchOptions(use_cache=False))
    assert nodriver.started is True
    assert results[0].tier_used == "headed"
    assert results[0].content == "nodriver body for https://a.test"


def test_forced_nodriver_skips_the_probe(fetcher, urllib_tier, monkeypatch):
    nodriver = _FakeNodriverModule()
    monkeypatch.setitem(sys.modules, "nodriver", nodriver)
    calls = urllib_tier(fetcher, "irrelevant")

    async def fake_fetch(browser, url, mode, wait_ms):
        return "body"

    monkeypatch.setattr(fetcher, "_nodriver_fetch_with_browser", fake_fetch)
    fetcher.fetch_batch(
        ["https://a.test"],
        FetchOptions(transport=Transport.HEADED, use_cache=False),
    )
    # The transport was chosen explicitly, so tier 1 is never consulted.
    assert calls == []
    assert nodriver.started is True


def test_persistent_nodriver_serves_a_cache_hit_without_fetching(
    fetcher, urllib_tier, cache, monkeypatch
):
    # #15: this path drives the browser directly instead of going through
    # _escalate, and it never consulted the cache — so a batch holding a
    # headed browser re-fetched every URL it already had.
    nodriver = _FakeNodriverModule()
    monkeypatch.setitem(sys.modules, "nodriver", nodriver)
    urllib_tier(fetcher, _BOT_BLOCKED)
    fetched: list[str] = []

    async def fake_fetch(browser, url, mode, wait_ms):
        fetched.append(url)
        return "freshly fetched"

    monkeypatch.setattr(fetcher, "_nodriver_fetch_with_browser", fake_fetch)
    cache.write("https://a.test", ContentMode.TEXT, "cached body")

    results = fetcher.fetch_batch(["https://a.test"], FetchOptions(use_cache=True))

    assert fetched == []
    assert results[0].content == "cached body"
    assert results[0].tier_used == "cache"


def test_persistent_nodriver_caches_what_it_fetches(
    fetcher, urllib_tier, cache, monkeypatch
):
    nodriver = _FakeNodriverModule()
    monkeypatch.setitem(sys.modules, "nodriver", nodriver)
    urllib_tier(fetcher, _BOT_BLOCKED)

    async def fake_fetch(browser, url, mode, wait_ms):
        return "nodriver body"

    monkeypatch.setattr(fetcher, "_nodriver_fetch_with_browser", fake_fetch)
    fetcher.fetch_batch(["https://a.test"], FetchOptions(use_cache=True))

    assert cache.read("https://a.test", ContentMode.TEXT) == "nodriver body"


def test_persistent_nodriver_scrubs_a_junk_cache_entry(
    fetcher, urllib_tier, cache, monkeypatch
):
    # Junk must self-heal on this path too, not just through _fetch_single.
    nodriver = _FakeNodriverModule()
    monkeypatch.setitem(sys.modules, "nodriver", nodriver)
    urllib_tier(fetcher, _BOT_BLOCKED)

    async def fake_fetch(browser, url, mode, wait_ms):
        return "real body"

    monkeypatch.setattr(fetcher, "_nodriver_fetch_with_browser", fake_fetch)
    cache.write("https://a.test", ContentMode.TEXT, "<title>404 Not Found</title>")

    results = fetcher.fetch_batch(["https://a.test"], FetchOptions(use_cache=True))

    assert results[0].content == "real body"
    assert cache.read("https://a.test", ContentMode.TEXT) == "real body"


def test_batch_writes_each_entry_once(fetcher, urllib_tier, no_browser_tiers, cache):
    # _fetch_single wrote, then _run_batch wrote the same bytes again — and
    # on a cache hit it rewrote the entry with its own contents.
    no_browser_tiers(fetcher)
    urllib_tier(fetcher, {"https://a.test": "body"})
    writes: list[str] = []
    original = cache.write

    def counting_write(url, mode, content):
        writes.append(url)
        original(url, mode, content)

    cache.write = counting_write

    fetcher.fetch_batch(["https://a.test"], FetchOptions(use_cache=True))
    assert writes == ["https://a.test"]

    writes.clear()
    fetcher.fetch_batch(["https://a.test"], FetchOptions(use_cache=True))
    assert writes == []


def test_forced_playwright_opens_no_persistent_session(
    fetcher, urllib_tier, no_browser_tiers, monkeypatch
):
    nodriver = _FakeNodriverModule()
    monkeypatch.setitem(sys.modules, "nodriver", nodriver)
    no_browser_tiers(fetcher)
    calls = urllib_tier(fetcher, "body")
    fetcher.fetch_batch(
        ["https://a.test"],
        FetchOptions(transport=Transport.JS, use_cache=False),
    )
    assert nodriver.started is False
    assert calls == []


def test_forced_uc_opens_a_uc_session(fetcher, urllib_tier, monkeypatch):
    seleniumbase = _FakeSeleniumBaseModule()
    monkeypatch.setitem(sys.modules, "seleniumbase", seleniumbase)
    urllib_tier(fetcher, "body")
    monkeypatch.setattr(
        fetcher, "_fetch_uc_with_session", lambda sb, url, mode, wait: "uc body"
    )
    results = fetcher.fetch_batch(
        ["https://a.test"], FetchOptions(transport=Transport.HEADLESS, use_cache=False)
    )
    assert seleniumbase.context.entered is True
    assert seleniumbase.kwargs == {"uc": True, "headless": True}
    assert results[0].content == "uc body"


# --- fallbacks when a session will not start --------------------------


def test_missing_nodriver_falls_back_to_uc(fetcher, urllib_tier, monkeypatch):
    # nodriver absent, seleniumbase present.
    monkeypatch.setitem(sys.modules, "nodriver", None)
    seleniumbase = _FakeSeleniumBaseModule()
    monkeypatch.setitem(sys.modules, "seleniumbase", seleniumbase)
    urllib_tier(fetcher, _BOT_BLOCKED)
    monkeypatch.setattr(
        fetcher, "_fetch_uc_with_session", lambda sb, url, mode, wait: "uc body"
    )
    results = fetcher.fetch_batch(["https://a.test"], FetchOptions(use_cache=False))
    assert seleniumbase.context.entered is True
    assert results[0].content == "uc body"


def test_nodriver_failing_to_launch_falls_back_to_uc(fetcher, urllib_tier, monkeypatch):
    nodriver = _FakeNodriverModule(fail=True)
    monkeypatch.setitem(sys.modules, "nodriver", nodriver)
    seleniumbase = _FakeSeleniumBaseModule()
    monkeypatch.setitem(sys.modules, "seleniumbase", seleniumbase)
    urllib_tier(fetcher, _BOT_BLOCKED)
    monkeypatch.setattr(
        fetcher, "_fetch_uc_with_session", lambda sb, url, mode, wait: "uc body"
    )
    results = fetcher.fetch_batch(["https://a.test"], FetchOptions(use_cache=False))
    assert seleniumbase.context.entered is True
    assert results[0].content == "uc body"


def test_neither_engine_available_still_returns_results(
    fetcher, urllib_tier, no_browser_tiers, monkeypatch
):
    # Both absent: the batch degrades to per-URL mode rather than raising.
    monkeypatch.setitem(sys.modules, "nodriver", None)
    monkeypatch.setitem(sys.modules, "seleniumbase", None)
    no_browser_tiers(fetcher)
    urllib_tier(fetcher, _BOT_BLOCKED)
    results = fetcher.fetch_batch(["https://a.test"], FetchOptions(use_cache=False))
    assert len(results) == 1
    assert results[0].ok is False


# --- teardown ---------------------------------------------------------


def test_nodriver_browser_is_stopped_at_the_end(fetcher, urllib_tier, monkeypatch):
    browser = _FakeBrowser()
    monkeypatch.setitem(sys.modules, "nodriver", _FakeNodriverModule(browser))
    urllib_tier(fetcher, _BOT_BLOCKED)

    async def fake_fetch(b, url, mode, wait_ms):
        return "body"

    monkeypatch.setattr(fetcher, "_nodriver_fetch_with_browser", fake_fetch)
    fetcher.fetch_batch(["https://a.test"], FetchOptions(use_cache=False))
    assert browser.stopped is True


def test_uc_session_is_exited_at_the_end(fetcher, urllib_tier, monkeypatch):
    seleniumbase = _FakeSeleniumBaseModule()
    monkeypatch.setitem(sys.modules, "seleniumbase", seleniumbase)
    urllib_tier(fetcher, "body")
    monkeypatch.setattr(
        fetcher, "_fetch_uc_with_session", lambda sb, url, mode, wait: "uc body"
    )
    fetcher.fetch_batch(
        ["https://a.test"], FetchOptions(transport=Transport.HEADLESS, use_cache=False)
    )
    assert seleniumbase.context.exited is True


def test_empty_session_close_is_a_no_op(fetcher):
    # Per-URL mode holds nothing, so teardown must not assume it does.
    _BatchSession().close()


def test_close_closes_the_event_loop(fetcher, urllib_tier, monkeypatch):
    # The loop used to be abandoned rather than closed, leaking a selector
    # and its file descriptors on every batch — silently, because nothing
    # in the process complains about it.
    monkeypatch.setitem(sys.modules, "nodriver", _FakeNodriverModule())
    urllib_tier(fetcher, _BOT_BLOCKED)
    session = fetcher._open_batch_session(["https://a.test"], FetchOptions())
    loop = session.loop
    assert loop is not None
    assert loop.is_closed() is False
    session.close()
    assert loop.is_closed() is True


class _DeadBrowser:
    """A browser that has already gone away — stop() raises."""

    def stop(self):
        raise RuntimeError("browser already dead")


class _ExplodingLoop:
    def close(self):
        raise RuntimeError("loop already closed")


def test_close_closes_the_loop_even_when_the_browser_stop_fails(capsys):
    # #20: teardown was three unguarded statements, so the first failure
    # skipped the rest. A dead browser is the normal case after a crash
    # mid-batch — exactly when the cleanup matters most.
    loop = asyncio.new_event_loop()
    session = _BatchSession(nd_browser=_DeadBrowser(), loop=loop)

    session.close()

    assert loop.is_closed() is True
    assert "Could not release the Nodriver browser" in capsys.readouterr().err


def test_close_exits_the_uc_context_even_when_the_loop_close_fails(capsys):
    context = _FakeSbContext()
    session = _BatchSession(
        loop=_ExplodingLoop(), sb_session=object(), sb_context=context
    )

    session.close()

    assert context.exited is True
    assert "Could not release the event loop" in capsys.readouterr().err


def test_close_never_raises_out_of_the_batch(capsys):
    # close() runs in _run_batch's finally, so raising would replace the
    # results the batch had already collected.
    context = _FakeSbContext()
    monkey = _BatchSession(
        nd_browser=_DeadBrowser(),
        loop=_ExplodingLoop(),
        sb_session=object(),
        sb_context=context,
    )

    monkey.close()

    assert context.exited is True
    assert capsys.readouterr().err.count("Could not release") == 2


def test_a_dead_browser_does_not_lose_the_batch_results(
    fetcher, urllib_tier, monkeypatch
):
    nodriver = _FakeNodriverModule(browser=_DeadBrowser())
    monkeypatch.setitem(sys.modules, "nodriver", nodriver)
    urllib_tier(fetcher, _BOT_BLOCKED)

    async def fake_fetch(browser, url, mode, wait_ms):
        return "body"

    monkeypatch.setattr(fetcher, "_nodriver_fetch_with_browser", fake_fetch)

    results = fetcher.fetch_batch(["https://a.test"], FetchOptions(use_cache=False))

    assert results[0].content == "body"


def test_failed_nodriver_launch_does_not_strand_a_loop(
    fetcher, urllib_tier, monkeypatch
):
    # The loop is created before the browser, so a launch failure has no
    # session object to clean up — it has to close its own loop.
    created = []
    real_new_event_loop = asyncio.new_event_loop

    def recording_new_event_loop():
        loop = real_new_event_loop()
        created.append(loop)
        return loop

    monkeypatch.setattr(asyncio, "new_event_loop", recording_new_event_loop)
    monkeypatch.setitem(sys.modules, "nodriver", _FakeNodriverModule(fail=True))
    monkeypatch.setitem(sys.modules, "seleniumbase", None)
    urllib_tier(fetcher, _BOT_BLOCKED)

    session = fetcher._open_batch_session(["https://a.test"], FetchOptions())

    assert created, "expected the nodriver path to create a loop"
    assert all(loop.is_closed() for loop in created)
    assert session.drives_nodriver is False


def test_browser_is_stopped_even_when_a_fetch_raises(fetcher, urllib_tier, monkeypatch):
    # A crash mid-batch must not leave a headed Chrome running.
    browser = _FakeBrowser()
    monkeypatch.setitem(sys.modules, "nodriver", _FakeNodriverModule(browser))
    urllib_tier(fetcher, _BOT_BLOCKED)

    async def exploding(b, url, mode, wait_ms):
        raise RuntimeError("mid-batch failure")

    monkeypatch.setattr(fetcher, "_nodriver_fetch_with_browser", exploding)
    with pytest.raises(RuntimeError):
        fetcher.fetch_batch(["https://a.test"], FetchOptions(use_cache=False))
    assert browser.stopped is True
