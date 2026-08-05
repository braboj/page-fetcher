# Glossary

| Term | Definition |
| ------ | ------------ |
| **Ambiguous phrase** | Wording that means "this page is gone" on a stub and something innocent in ordinary body copy. Counts towards a not-found verdict only below the size floor |
| **Automatic mode** | The default: the transport is chosen by escalation rather than named by the caller |
| **Batch** | A list of URLs fetched in one call, sharing at most one browser and returning results in the order requested |
| **Bot wall** | A page a site serves to a client it believes is automated, in place of the page that was requested. Usually carries a success status |
| **Content form** | Whether content is returned as raw markup or as markup reduced to text. The two forms of one page are stored separately |
| **Escalation** | Retrying a request on a more capable and more expensive transport because the previous one returned something classified as failed |
| **Headed** | The transport requiring a visible browser window. Named for what it needs from the caller, not for the engine behind it |
| **Headless** | The bypass transport needing no display, at several times the cost of the headed one |
| **Junk** | A body that must never be served from the store: a wall, a throttle stub or a not-found page. Defined once and used by both the read path and the sweep |
| **Ladder** | The ordering of transports from cheapest to most expensive, and the rules for moving between them |
| **Narration** | The running commentary on standard error naming each escalation, skip and failure. Content never appears there |
| **Ownership by ancestry** | Deciding that a browser process belongs to this one by walking its parents, rather than by comparing process lists before and after a launch |
| **Page source** | The abstract interface every fetcher implements, and the type a consumer depends on so it can be substituted in tests |
| **Plain transport** | The first rung: a standard-library HTTP request with no browser involved |
| **Real content** | A body that is neither a wall nor a not-found page and clears the size floor. The condition for returning a body and for storing it |
| **Refresh** | Ignoring a stored body for one fetch. It governs whether a stored body is served, never whether a fresh one is stored, so the stale entry is replaced rather than left behind |
| **Rung** | One transport, considered as a position in the ladder |
| **Sentinel** | An internal marker the plain transport returns in place of a body to signal why it failed. It is what makes the body unavailable to any later rung |
| **Size floor** | The number of bytes of raw markup below which a body is not treated as a page whatever it contains |
| **Soft-404** | A not-found page served with a success status, typically a withdrawn product |
| **Store** | The on-disk directory of retained page bodies, keyed by URL and content form, with no expiry |
| **Sweep** | A pass over the whole store removing entries that are junk, optionally reporting without removing |
| **Throttle stub** | A short page served in place of content when a site decides a client is asking too often |
| **Transport** | One way of getting a page: the plain request or one of the three browser-driven rungs |
| **Under-rendering** | A page returned in full-looking form whose content is assembled in the browser, so what arrives is a shell. Not detected |
