"""NetworkFetcher — the real four-tier auto-escalating page fetcher.

Tier strategy (auto mode escalates on failure):
  1. http     (urllib)           — fastest (~1s), most static pages
  2. js       (Playwright)       — JS-rendered pages (~5-9s)
  3. headed   (Nodriver)         — bot bypass, needs a display (~6-8s)
  4. headless (SeleniumBase UC)  — bot bypass, no display (~18-24s)

Auto mode tries http first. If bot protection is detected, it skips js
(which would fail the same way) and goes straight to headed, then
headless. If http fails for another reason (404, timeout), it tries js,
then headed, then headless.

The tiers are named for what they require of the caller, not for the
library behind them; ADR-006 records why the two bot-bypass tiers both
exist and why headless is last despite the name.

Third-party browser libraries are imported lazily inside each tier so the
package works with only the standard library installed — unavailable tiers
are skipped gracefully.
"""

import asyncio
import gzip
import sys
import time
import urllib.parse
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cache import FileCache
from .chrome import ChromeReaper, default_reaper
from .detection import (
    html_to_text,
    is_bot_blocked,
    is_cacheable_junk,
    is_error_page,
    looks_like_real_content,
)
from .source import (
    DEFAULT_WAIT_MS,
    ContentMode,
    FetchOptions,
    FetchResult,
    PageSource,
    Transport,
)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# Sentinel: urllib detected bot protection (skip Playwright, go to Nodriver/UC).
_BOT_BLOCKED = "@@BOT_BLOCKED@@"
# Sentinel: response is a 404 / gone error page. Terminal — do not escalate
# (every tier returns the same error) and do not cache.
_ERROR_PAGE = "@@ERROR_PAGE@@"

# Compressions the urllib tier can undo, so it is honest to ask for them.
# Brotli and zstd are deliberately absent: neither ships in the standard
# library, and advertising an encoding we cannot decode is how a response
# becomes unreadable.
ACCEPT_ENCODING = "gzip, deflate"

# What ACCEPT_ENCODING asks for, as tokens. A response carrying anything
# else means the server ignored the request header, which happens — and a
# body we cannot undo must fail the tier rather than flow on as content.
DECODABLE_ENCODINGS = frozenset({"gzip", "deflate"})

# gzip streams start with these two bytes. Used to catch a server that
# compresses without saying so — see _decompress.
_GZIP_MAGIC = b"\x1f\x8b"

# This package fetches web pages. urllib will happily open file://, ftp://
# and a handful of other schemes, which for a page fetcher is never the
# intent — and when a caller passes a URL that came from somewhere else,
# file:// turns the fetcher into a file-read primitive.
ALLOWED_SCHEMES = frozenset({"http", "https"})


def require_supported_scheme(url: str) -> None:
    """Raise ValueError unless `url` is http or https.

    Called at every public entry point rather than deep in a tier, so a
    bad URL fails before any browser is launched or any request is made.

    This is a scheme allowlist and nothing more. It does NOT stop a
    request to a loopback or private address over http — a caller passing
    URLs that originate from untrusted input still has to filter those
    itself. See ADR-003 for why that is deliberately out of scope here.
    """
    scheme = urllib.parse.urlsplit(url).scheme.lower()
    if scheme in ALLOWED_SCHEMES:
        return
    allowed = ", ".join(sorted(ALLOWED_SCHEMES))
    if not scheme:
        # Plain ASCII on purpose: this reaches a terminal, and a Windows
        # console in a legacy code page renders anything else as garbage.
        raise ValueError(
            f"{url!r} has no scheme; pagefetch needs an absolute URL "
            f"({allowed}). Did you mean https://{url}?"
        )
    raise ValueError(
        f"{url!r} uses the {scheme!r} scheme; pagefetch only fetches {allowed}"
    )


def _decompress(raw: bytes, content_encoding: str) -> bytes:
    """Undo a response's Content-Encoding, returning the raw bytes.

    Also sniffs the gzip magic bytes when the header does not claim gzip.
    A server that compresses without declaring it is not hypothetical, and
    an undeclared gzip body is the worst case for this fetcher: decoded as
    text it becomes mojibake, which is comfortably larger than
    MIN_REAL_CONTENT_BYTES, so it passes the real-content gate and is
    written to the cache as if it were a page.

    Raises ValueError when the body declares an encoding this tier cannot
    undo. Handing those bytes back unchanged produces exactly the mojibake
    described above — the failure this function exists to prevent, arrived
    at from the other direction.
    """
    # A chain ("gzip, br") would have to be undone in reverse order, and
    # any link this tier cannot undo makes the whole body unreadable.
    # identity is the no-op encoding and carries no information.
    tokens = [t.strip() for t in content_encoding.lower().split(",")]
    tokens = [t for t in tokens if t and t != "identity"]
    if len(tokens) > 1:
        raise ValueError(f"chained Content-Encoding {content_encoding!r}")
    encoding = tokens[0] if tokens else ""

    if encoding == "gzip" or raw[:2] == _GZIP_MAGIC:
        return gzip.decompress(raw)
    if encoding == "deflate":
        try:
            return zlib.decompress(raw)
        except zlib.error:
            # Some servers send a raw deflate stream with no zlib header.
            return zlib.decompress(raw, -zlib.MAX_WBITS)
    if encoding and encoding not in DECODABLE_ENCODINGS:
        raise ValueError(f"unsupported Content-Encoding {encoding!r}")
    return raw


@dataclass
class _BatchSession:
    """The browser a batch holds open, and how to give it back.

    A batch pays the browser launch cost once instead of per URL, which
    means something stays alive across the whole run and has to be
    released whatever happens. Keeping the handles and the teardown in one
    place is the point: every field here is something that leaks if the
    batch exits without calling close().

    An empty instance is the per-URL mode — no persistent browser, every
    field None, and close() does nothing.

    Fields are typed Any because they are third-party handles (a nodriver
    Browser, a SeleniumBase context) that the package imports lazily and
    cannot reference in an annotation.
    """

    nd_browser: Any = None
    loop: Any = None
    sb_session: Any = None
    sb_context: Any = None

    @property
    def drives_nodriver(self) -> bool:
        """True when the batch loop should fetch through Nodriver."""
        return self.nd_browser is not None and self.loop is not None

    @staticmethod
    def _release(what: str, release) -> None:
        """Run one teardown step, reporting a failure instead of raising.

        Every step is independent. A browser that has already died raises
        from stop(), and letting that propagate skipped the steps after it
        — leaving exactly the leak this class exists to prevent, in the
        one situation where cleanup matters most. close() also runs in a
        finally, so raising here would replace whatever the batch was
        returning.
        """
        try:
            release()
        except Exception as e:
            print(f"[batch] Could not release {what}: {e}", file=sys.stderr)

    def close(self) -> None:
        """Release everything this session holds, in dependency order.

        The browser goes first because stopping it may need the loop, and
        the loop is closed rather than merely abandoned — a batch that
        left one open leaked a selector and its file descriptors on every
        run, invisibly, since nothing in the process complained.
        """
        if self.nd_browser is not None:
            self._release("the Nodriver browser", self.nd_browser.stop)
        if self.loop is not None:
            self._release("the event loop", self.loop.close)
        if self.sb_context is not None:
            self._release(
                "the UC session",
                lambda: self.sb_context.__exit__(None, None, None),
            )


def _scroll_page_js() -> str:
    """JavaScript to scroll a page for lazy-loaded content (Playwright)."""
    return """async () => {
        const delay = ms => new Promise(r => setTimeout(r, ms));
        const height = document.body.scrollHeight;
        const step = window.innerHeight;
        for (let y = 0; y < height; y += step) {
            window.scrollTo(0, y);
            await delay(200);
        }
        window.scrollTo(0, 0);
        await delay(500);
    }"""


class NetworkFetcher(PageSource):
    """Fetches pages over the network with auto-escalating transport."""

    def __init__(
        self,
        cache: FileCache | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
        reaper: ChromeReaper | None = None,
    ) -> None:
        self._cache = cache or FileCache()
        self._ua = user_agent
        # Shared by default: a reaper per fetcher registered an atexit
        # handler per fetcher, none of which were ever removed.
        self._reaper = reaper or default_reaper()

    # --- public PageSource interface ---------------------------------

    def fetch(self, url: str, options: FetchOptions | None = None) -> FetchResult:
        require_supported_scheme(url)
        opts = options or FetchOptions()
        content, tier = self._fetch_single(url, opts)
        return FetchResult(url=url, content=content, tier_used=tier, ok=bool(content))

    def fetch_batch(
        self, urls: list[str], options: FetchOptions | None = None
    ) -> list[FetchResult]:
        # Validate the whole list before starting: a batch launches a
        # browser and can run for minutes, so failing on URL 87 of 100
        # after all that work is worse than refusing up front.
        for url in urls:
            require_supported_scheme(url)
        opts = options or FetchOptions()
        return self._run_batch(urls, opts)

    def download_bytes(self, url: str, min_size: int = 0) -> bytes | None:
        import urllib.request

        require_supported_scheme(url)
        try:
            # S310 wants proof the scheme is safe; require_supported_scheme
            # above is that proof, but ruff cannot see across the call.
            req = urllib.request.Request(  # noqa: S310
                url, headers={"User-Agent": self._ua}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
                data = resp.read()
        except Exception as e:
            print(f"[download] {e}", file=sys.stderr)
            return None
        if len(data) < min_size:
            return None
        return data

    def screenshot(
        self, url: str, dest: Path, options: FetchOptions | None = None
    ) -> bool:
        require_supported_scheme(url)
        opts = options or FetchOptions()
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("[js] Not installed", file=sys.stderr)
            return False
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=self._ua)
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(opts.wait_ms)
                dest.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(dest), full_page=True)
                browser.close()
            return True
        except Exception as e:
            print(f"[js] {e}", file=sys.stderr)
            return False

    # --- tier 1: urllib ----------------------------------------------

    def _fetch_urllib(self, url: str, mode: ContentMode) -> str | None:
        """Fetch via plain urllib. Returns content, the _BOT_BLOCKED /
        _ERROR_PAGE sentinel, or None."""
        import urllib.error
        import urllib.request

        try:
            # S310 wants proof the scheme is safe. Every public entry point
            # calls require_supported_scheme before reaching this tier, but
            # ruff cannot see across those calls.
            req = urllib.request.Request(  # noqa: S310
                url,
                headers={
                    "User-Agent": self._ua,
                    "Accept-Encoding": ACCEPT_ENCODING,
                },
            )
            # S310 wants proof the scheme is safe. Every public entry point
            # calls require_supported_scheme before reaching this tier, but
            # ruff cannot see across those calls.
            with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
                raw = resp.read()
                content_encoding = resp.headers.get("Content-Encoding") or ""
        except urllib.error.HTTPError as e:
            # Non-200: never cached. A hard 404/410 is terminal (escalation
            # would hit the same error); other codes fall through to escalate.
            print(f"[http] HTTP {e.code}", file=sys.stderr)
            return _ERROR_PAGE if e.code in (404, 410) else None
        except Exception as e:
            print(f"[http] {e}", file=sys.stderr)
            return None

        try:
            html = _decompress(raw, content_encoding).decode("utf-8", errors="replace")
        # ValueError is _decompress rejecting an encoding it cannot undo;
        # the rest are a declared encoding whose body does not match it.
        except (OSError, EOFError, ValueError, zlib.error) as e:
            # A body we cannot decompress is not content. Escalating beats
            # handing back mojibake that would pass the size gate and be
            # cached as if it were a page.
            print(
                f"[http] Could not decompress "
                f"{content_encoding or 'response'} body: {e}",
                file=sys.stderr,
            )
            return None

        # A 404/gone body (incl. soft-404 served as HTTP 200) is terminal:
        # don't cache, don't escalate — the product page is genuinely gone.
        # Checked before the size/bot gate because error pages are also short.
        if is_error_page(html):
            print("[http] 404 / gone error page", file=sys.stderr)
            return _ERROR_PAGE

        # Treat bot-blocks AND implausibly short throttle/error stubs the
        # same: signal escalation rather than accept (and later cache) junk.
        # The size check runs on raw HTML — TEXT-mode content of a real page
        # can be much shorter than the threshold after tag stripping.
        if not looks_like_real_content(html):
            print(
                f"[http] Not real content ({len(html)} bytes) — escalating",
                file=sys.stderr,
            )
            return _BOT_BLOCKED

        if mode is ContentMode.HTML:
            return html
        return html_to_text(html)

    # --- tier 2: Playwright ------------------------------------------

    def _fetch_playwright(
        self, url: str, mode: ContentMode, wait_ms: int
    ) -> str | None:
        """Fetch via headless Chromium. Uses domcontentloaded (not
        networkidle) — faster on ad-heavy pages."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("[js] Not installed", file=sys.stderr)
            return None

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=self._ua)
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(wait_ms)
                page.evaluate(_scroll_page_js())

                html = page.content()
                if not looks_like_real_content(html):
                    print(
                        f"[js] Not real content ({len(html)} bytes)",
                        file=sys.stderr,
                    )
                    browser.close()
                    return None

                content = html if mode is ContentMode.HTML else page.inner_text("body")

                png = self._cache.screenshot_path(url)
                if not png.exists():
                    png.parent.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(png), full_page=True)

                browser.close()
                return content
        except Exception as e:
            print(f"[js] {e}", file=sys.stderr)
            return None

    # --- tier 3: Nodriver --------------------------------------------

    def _fetch_nodriver(self, url: str, mode: ContentMode, wait_ms: int) -> str | None:
        """Fetch via Nodriver (headed Chrome via CDP, no driver binary)."""
        try:
            import nodriver as uc_nd
        except ImportError:
            print("[headed] Not installed", file=sys.stderr)
            return None

        import asyncio

        async def _fetch() -> str | None:
            browser = None
            try:
                pids_before = self._reaper.running_chrome_pids()
                browser = await uc_nd.start(headless=False)
                self._reaper.track_new_since(pids_before)
                page = await browser.get(url)
                return await self._nodriver_read_page(page, mode, wait_ms)
            except Exception as e:
                print(f"[headed] {e}", file=sys.stderr)
                return None
            finally:
                if browser:
                    browser.stop()

        try:
            return asyncio.run(_fetch())
        except Exception as e:
            print(f"[headed] {e}", file=sys.stderr)
            return None

    async def _nodriver_read_page(
        self, page, mode: ContentMode, wait_ms: int
    ) -> str | None:
        """Wait for a Nodriver page to clear bot protection and read it.

        Shared by single-fetch and batch (persistent browser) paths.
        """
        import time as _time

        deadline = _time.monotonic() + 15
        while _time.monotonic() < deadline:
            try:
                if await page.evaluate("document.readyState") == "complete":
                    break
            except Exception:
                pass
            await page.sleep(0.3)

        interval = 0.5
        while _time.monotonic() < deadline:
            html = await page.get_content()
            if not is_bot_blocked(html):
                break
            await page.sleep(interval)
            interval = min(interval * 1.5, 2.0)
        else:
            print("[headed] Bot detection page still present", file=sys.stderr)
            return None

        if wait_ms > DEFAULT_WAIT_MS:
            await page.sleep(wait_ms / 1000)

        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.sleep(0.5)
        except Exception:
            pass

        html = await page.get_content()
        if not looks_like_real_content(html):
            print(
                f"[headed] Not real content ({len(html)} bytes)",
                file=sys.stderr,
            )
            return None

        return html if mode is ContentMode.HTML else html_to_text(html)

    async def _nodriver_fetch_with_browser(
        self, browser, url: str, mode: ContentMode, wait_ms: int
    ) -> str | None:
        """Fetch using an existing Nodriver browser (batch mode)."""
        try:
            page = await browser.get(url)
            return await self._nodriver_read_page(page, mode, wait_ms)
        except Exception as e:
            print(f"[headed] {e}", file=sys.stderr)
            return None

    # --- tier 4: SeleniumBase UC -------------------------------------

    def _fetch_uc(self, url: str, mode: ContentMode, wait_ms: int) -> str | None:
        """Fetch via SeleniumBase UC mode. Launches a new session per call;
        batch mode reuses one via _fetch_uc_with_session."""
        try:
            from seleniumbase import SB
        except ImportError:
            print("[headless] SeleniumBase not installed", file=sys.stderr)
            return None

        try:
            pids_before = self._reaper.running_chrome_pids()
            with SB(uc=True, headless=True) as sb:
                self._reaper.track_new_since(pids_before)
                return self._fetch_uc_with_session(sb, url, mode, wait_ms)
        except Exception as e:
            print(f"[headless] {e}", file=sys.stderr)
            return None

    def _fetch_uc_with_session(
        self, sb, url: str, mode: ContentMode, wait_ms: int
    ) -> str | None:
        """Fetch a page using an existing SeleniumBase UC session."""
        try:
            sb.open(url)
            if not self._uc_wait_for_page(sb):
                print(
                    "[headless] Bot detection page still present after timeout",
                    file=sys.stderr,
                )
                return None
            if wait_ms > DEFAULT_WAIT_MS:
                sb.sleep(wait_ms / 1000)
            self._uc_wait_for_scroll(sb)
            html = sb.get_page_source()
            if not looks_like_real_content(html):
                print(
                    f"[headless] Not real content ({len(html)} bytes)",
                    file=sys.stderr,
                )
                return None
            return html if mode is ContentMode.HTML else html_to_text(html)
        except Exception as e:
            print(f"[headless] {e}", file=sys.stderr)
            return None

    @staticmethod
    def _uc_wait_for_page(sb, timeout_s: int = 15) -> bool:
        """Wait past a bot-protection interstitial: first for readyState,
        then poll the page source for bot detection with backoff."""
        import time

        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            try:
                if sb.execute_script("return document.readyState") == "complete":
                    break
            except Exception:
                pass
            sb.sleep(0.3)

        interval = 0.5
        while time.monotonic() < deadline:
            try:
                if not is_bot_blocked(sb.get_page_source()):
                    return True
            except Exception:
                pass
            sb.sleep(interval)
            interval = min(interval * 1.5, 2.0)
        return False

    @staticmethod
    def _uc_wait_for_scroll(sb, timeout_s: int = 3) -> None:
        """Scroll to bottom and wait for DOM height to stabilize."""
        import time

        try:
            prev_height = sb.execute_script(
                "return document.body ? document.body.scrollHeight : 0"
            )
            if not prev_height:
                return
            sb.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            deadline = time.monotonic() + timeout_s
            while time.monotonic() < deadline:
                sb.sleep(0.3)
                new_height = sb.execute_script("return document.body.scrollHeight")
                if new_height == prev_height:
                    return
                prev_height = new_height
                sb.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        except Exception:
            pass

    # --- escalation orchestrator -------------------------------------

    def _read_cache(self, url: str, opts: FetchOptions) -> str | None:
        """Cached body for this URL, or None for a miss.

        The single place the cache is read. use_cache=False is a miss by
        definition: the flag gates serving, not storing — see _write_cache.

        Defends against a poisoned cache: a cached body that is a
        bot/throttle page OR a 404/gone error page is ignored, deleted, and
        reported as a miss — so a cache written before these guards (or
        before a product was discontinued) self-heals and the dead file
        does not linger. Only the pattern checks apply here, not the size
        threshold — cached TEXT-mode content of a real page can
        legitimately be short.
        """
        if not opts.use_cache:
            return None
        cached = self._cache.read(url, opts.mode)
        if cached is None:
            return None
        if is_cacheable_junk(cached):
            self._cache.delete(url, opts.mode)
            return None
        return cached

    def _write_cache(self, url: str, opts: FetchOptions, content: str) -> None:
        """Cache a fetched body, if there is one.

        The single place the cache is written. Deliberately NOT gated on
        use_cache: the flag decides whether a cached body is *served*, not
        whether a fresh one is stored, so use_cache=False is a refresh
        rather than a bypass — it replaces the stale entry instead of
        leaving it to be served next time. Pinned by
        test_use_cache_false_still_populates_the_cache.
        """
        if content:
            self._cache.write(url, opts.mode, content)

    def _fetch_single(
        self, url: str, opts: FetchOptions, sb_session=None
    ) -> tuple[str, str]:
        """Fetch one URL, escalating tiers as needed.

        Returns (content, tier_used). content is "" if every tier failed.
        Shared by single and batch modes. The batch loop drives a
        persistent Nodriver browser itself; sb_session lets a persistent
        UC session flow through to escalation.
        """
        cached = self._read_cache(url, opts)
        if cached is not None:
            return cached, "cache"

        content, tier = self._escalate(url, opts, sb_session)
        self._write_cache(url, opts, content)
        return content, tier

    def _escalate(self, url: str, opts: FetchOptions, sb_session) -> tuple[str, str]:
        """Run the tier strategy for opts.transport. Returns (content, tier)."""
        mode, wait_ms = opts.mode, opts.wait_ms

        if opts.transport is Transport.HEADLESS:
            content = self._uc_either(sb_session, url, mode, wait_ms)
            return content, "headless" if content else "none"

        if opts.transport is Transport.HEADED:
            content = self._nodriver_either(url, mode, wait_ms)
            return content, "headed" if content else "none"

        if opts.transport is Transport.JS:
            content = self._fetch_playwright(url, mode, wait_ms) or ""
            return content, "js" if content else "none"

        if opts.transport is Transport.HTTP:
            # No escalation: a caller forcing this tier is asking for the
            # cheap path only. A bot wall or error page is a failure here,
            # not a reason to launch a browser they ruled out.
            result = self._fetch_urllib(url, mode)
            if result and result not in (_BOT_BLOCKED, _ERROR_PAGE):
                return result, "http"
            return "", "none"

        # AUTO: urllib first, then escalate.
        result = self._fetch_urllib(url, mode)
        if result and result not in (_BOT_BLOCKED, _ERROR_PAGE):
            return result, "http"

        if result == _ERROR_PAGE:
            # Genuine 404/gone: terminal. No escalation (same error), no cache.
            print("[auto] 404 / gone — not escalating", file=sys.stderr)
            return "", "none"

        if result == _BOT_BLOCKED:
            # Bot protection: skip Playwright (it would fail too).
            print(
                "[auto] Skipping Playwright (bot protection), trying Nodriver...",
                file=sys.stderr,
            )
            content = self._nodriver_either(url, mode, wait_ms)
            if content:
                return content, "headed"
            print("[auto] Nodriver failed, escalating to UC...", file=sys.stderr)
            content = self._uc_either(sb_session, url, mode, wait_ms)
            return content, "headless" if content else "none"

        # Non-bot failure (404, timeout): Playwright, then Nodriver, then UC.
        print("[auto] Escalating to Playwright...", file=sys.stderr)
        content = self._fetch_playwright(url, mode, wait_ms) or ""
        if content:
            return content, "js"
        print("[auto] Escalating to Nodriver...", file=sys.stderr)
        content = self._nodriver_either(url, mode, wait_ms)
        if content:
            return content, "headed"
        print("[auto] Escalating to UC...", file=sys.stderr)
        content = self._uc_either(sb_session, url, mode, wait_ms)
        return content, "headless" if content else "none"

    def _nodriver_either(self, url, mode, wait_ms) -> str:
        """Nodriver fetch. The batch loop drives the persistent browser
        directly (see _run_batch); single/escalation fetches are standalone."""
        return self._fetch_nodriver(url, mode, wait_ms) or ""

    def _uc_either(self, sb_session, url, mode, wait_ms) -> str:
        """UC via a persistent batch session if given, else standalone."""
        if sb_session:
            return self._fetch_uc_with_session(sb_session, url, mode, wait_ms) or ""
        return self._fetch_uc(url, mode, wait_ms) or ""

    # --- batch -------------------------------------------------------

    def _wants_persistent_bot_tier(
        self, urls: list[str], opts: FetchOptions
    ) -> tuple[bool, bool]:
        """Decide which persistent browser, if any, the batch should hold.

        Returns (wants_nodriver, wants_uc). An explicit transport is taken
        at its word; only auto mode probes, and it probes the first URL
        alone — launching a headed browser for a batch that plain HTTP can
        serve costs far more than one wasted request.
        """
        if opts.transport is Transport.HEADED:
            return True, False
        if opts.transport is Transport.HEADLESS:
            return False, True
        if opts.transport is Transport.AUTO and urls:
            probe = self._fetch_urllib(urls[0], opts.mode)
            return probe == _BOT_BLOCKED, False
        return False, False

    def _start_nodriver_session(self, url_count: int) -> _BatchSession | None:
        """Launch a persistent Nodriver browser, or None if it cannot be."""
        loop = None
        try:
            import nodriver as uc_nd

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            pids_before = self._reaper.running_chrome_pids()
            browser = loop.run_until_complete(uc_nd.start(headless=False))
            self._reaper.track_new_since(pids_before)
            print(
                f"[batch] Persistent Nodriver session started for {url_count} URLs",
                file=sys.stderr,
            )
            return _BatchSession(nd_browser=browser, loop=loop)
        except ImportError:
            print("[batch] Nodriver not installed, falling back to UC", file=sys.stderr)
        except Exception as e:
            print(
                f"[batch] Nodriver failed to start: {e}, falling back to UC",
                file=sys.stderr,
            )
        # The loop is created before the browser, so a failed launch would
        # otherwise strand it — there is no session object to close yet.
        if loop is not None:
            loop.close()
        return None

    def _start_uc_session(self, url_count: int) -> _BatchSession | None:
        """Open a persistent SeleniumBase UC session, or None if absent."""
        try:
            from seleniumbase import SB

            pids_before = self._reaper.running_chrome_pids()
            context = SB(uc=True, headless=True)
            session = context.__enter__()
            self._reaper.track_new_since(pids_before)
            print(
                f"[batch] Persistent UC session started for {url_count} URLs",
                file=sys.stderr,
            )
            return _BatchSession(sb_session=session, sb_context=context)
        except ImportError:
            print(
                "[batch] SeleniumBase not installed, falling back to per-URL mode",
                file=sys.stderr,
            )
        return None

    def _open_batch_session(self, urls: list[str], opts: FetchOptions) -> _BatchSession:
        """Open whichever persistent browser the batch warrants.

        Nodriver is preferred for bot-protected batches and UC is the
        fallback, including when Nodriver is installed but will not
        launch. An empty session means per-URL mode, which is a working
        outcome rather than a failure.
        """
        wants_nodriver, wants_uc = self._wants_persistent_bot_tier(urls, opts)
        if wants_nodriver:
            session = self._start_nodriver_session(len(urls))
            if session is not None:
                return session
            wants_uc = True
        if wants_uc:
            session = self._start_uc_session(len(urls))
            if session is not None:
                return session
        return _BatchSession()

    def _fetch_one_in_batch(
        self, url: str, opts: FetchOptions, session: _BatchSession
    ) -> tuple[str, str]:
        """Fetch one URL using the batch's session, if it has one.

        The persistent-Nodriver path drives the browser directly instead of
        going through _escalate, so it has to read and write the cache
        itself. It used to do neither, which made a batch holding a headed
        browser re-fetch every URL it already had.
        """
        if not session.drives_nodriver:
            return self._fetch_single(url, opts, sb_session=session.sb_session)

        cached = self._read_cache(url, opts)
        if cached is not None:
            return cached, "cache"

        content = (
            session.loop.run_until_complete(
                self._nodriver_fetch_with_browser(
                    session.nd_browser, url, opts.mode, opts.wait_ms
                )
            )
            or ""
        )
        self._write_cache(url, opts, content)
        return content, "headed" if content else "none"

    def _run_batch(self, urls: list[str], opts: FetchOptions) -> list[FetchResult]:
        """Fetch many URLs through one persistent browser session.

        The browser launches once and stays open for every page. Results
        come back in input order.
        """
        session = self._open_batch_session(urls, opts)
        results: list[FetchResult] = []
        ok = fail = 0
        try:
            for i, url in enumerate(urls):
                started_at = time.monotonic()
                print(f"[batch] [{i + 1}/{len(urls)}] {url}", file=sys.stderr)

                content, tier = self._fetch_one_in_batch(url, opts, session)

                # No cache write here: _fetch_one_in_batch has already done
                # it on whichever path it took. Writing again duplicated
                # every entry, and rewrote a cache hit with its own bytes.
                elapsed = time.monotonic() - started_at
                if content:
                    ok += 1
                    print(
                        f"[batch]   -> {len(content)} bytes ({elapsed:.1f}s)",
                        file=sys.stderr,
                    )
                else:
                    fail += 1
                    print(f"[batch]   FAILED ({elapsed:.1f}s)", file=sys.stderr)

                results.append(
                    FetchResult(
                        url=url, content=content, tier_used=tier, ok=bool(content)
                    )
                )

            print(f"[batch] Done: {ok} ok, {fail} failed", file=sys.stderr)
        finally:
            session.close()

        return results
