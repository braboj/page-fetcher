# Examples

Runnable usage patterns, one file each. Every command below is shown with
the output it actually produces.

Prerequisites: Python 3.10 or later and the package installed. Nothing
else — no browsers, no dev extras.

```bash
py -m pip install -e .
```

None of these constructs a `NetworkFetcher`, so nothing here reaches the
network: they drive `FakeFetcher`, `FileCache` and the detection
predicates directly, against canned bodies and the captured page in
`tests/fixtures/`. That is what makes the output below reproducible. CI
runs every file in this directory on every pull request, so they cannot
rot.

| Example                                      | Shows                                            |
| -------------------------------------------- | ------------------------------------------------ |
| [`fake_fetcher.py`](fake_fetcher.py)         | Testing consuming code with no network           |
| [`batch_fetch.py`](batch_fetch.py)           | Many URLs in one call, and grading the outcome   |
| [`cache_lifecycle.py`](cache_lifecycle.py)   | Cache keys, hits, misses, and the junk sweep     |
| [`detect_bot_walls.py`](detect_bot_walls.py) | Which responses count as pages, walls, or errors |

## fake_fetcher.py

Inject a `PageSource` into your own code and it can be tested without a
network or a browser. The assertions are the demonstration — this is the
test a consumer would write, run as a script.

```bash
py examples/fake_fetcher.py
```

```text
visible text mentions '40MP': True
visible text mentions 'href': False
unmapped URL: ok=False tier_used='fake' content=''
HTML mode returns the body verbatim: True
calls: ['https://example.com/x100vi', 'https://example.com/x100vi', 'https://example.com/nope', 'https://example.com/x100v']
```

`href` appears in the canned page's markup and not in its visible text,
which is the difference between TEXT and HTML mode. An unmapped URL is
how a failed fetch reads: `ok=False` and empty content, never an
exception.

## batch_fetch.py

`fetch_batch` returns one result per input URL, in the input order,
whether or not each one succeeded. One URL in the list is deliberately
unmapped, so the batch lands on the partial-failure case.

```bash
py examples/batch_fetch.py
```

```text
url                                    ok     tier   chars
https://example.com/x100vi             True   fake   11
https://example.com/x100v              True   fake   11
https://example.com/nothing-here       False  fake   0
https://example.com/gfx100             True   fake   13
order preserved: True
exit code: 2
```

Exit code 2 is "some pages are missing", which the CLI reports separately
from "nothing came back" (1). The `chars` column counts stripped text,
not the HTML the map holds.

## cache_lifecycle.py

Cache keys are derived from the URL, one entry per content mode, and a
sweep removes bodies that should never be re-served. Runs in a temporary
directory, so it leaves your own cache alone.

```bash
py examples/cache_lifecycle.py
```

```text
text entry: 1002e41fbd8c1d1a.txt
html entry: 1002e41fbd8c1d1a.html
hit:  'Fujifilm X100VI A 40MP sensor in a fixed-lens compact.'
miss: None
entries: ['1002e41fbd8c1d1a.html', '1002e41fbd8c1d1a.txt', 'a84a16aeebe5ad31.html']
dry run: would remove [('a84a16aeebe5ad31.html', 'bot-blocked')]
dry run: kept 2, files still on disk 3
sweep:   removed [('a84a16aeebe5ad31.html', 'bot-blocked')]
sweep:   kept 2, files still on disk 2
```

Both keys for one URL share a stem and differ only in suffix. The dry run
reports what it would delete and deletes nothing — three files before,
three after — which is what `--clean-cache --dry-run` does from the
command line.

## detect_bot_walls.py

The predicates that decide, inside `NetworkFetcher`, whether a response is
returned, escalated to a browser, or given up on. The first sample is a
real captured page; the rest are the smallest bodies that reach each
verdict.

```bash
py examples/detect_bot_walls.py
```

```text
real-content floor: 10000 bytes

sample                             bytes bot    error  real
captured page (dpreview)          135253 False  False  True
cloudflare interstitial              120 True   False  False
soft 404                              68 False  True   False
'no longer available' stub            67 False  True   False
same sentence, real page           13598 False  False  True

de-tagged text: 13744 chars, starting:
Nikon Z6III Specs: DPReview | Photography News, Gear Reviews &amp; Community Instagram TikTok
```

The last two rows are the same sentence in two pages. "No longer
available" means a gone page on a stub and one variant being out of stock
in real body copy, so it counts only below the 10,000-byte floor: an error
verdict is terminal, and a real page lost to one sentence is the worst
failure this package has.

The captured page's byte count is smaller than the file on disk because
the file is read as text, and its de-tagged text keeps `&amp;` — nothing
here decodes HTML entities.
