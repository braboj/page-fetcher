# Introduction and Goals

pagefetch retrieves the content of a web page and hands it back as text or
HTML. What distinguishes it from a plain HTTP request is that it reads what
came back before accepting it: a bot wall, a throttle stub and a "page not
found" body all arrive looking like a page, often with a success status.
pagefetch recognizes those from the body alone and escalates through
progressively more capable and more expensive transports until one returns
something that is actually a page.

It is built for research use — reading a handful of product or reference
pages and keeping them on disk — not for bulk collection.

## Goals

- Return the content of a page by the cheapest transport that works, so
  the common case costs a single HTTP request
- Recognize a failed response from its body, because the status code does
  not distinguish a bot wall or a soft-404 from a real page
- Never hand back, or store, something that is not a page
- Install and run with nothing but the standard library, so a consumer
  takes on no dependency to get the common case
- Stay substitutable in a consumer's tests, so code that fetches pages can
  be tested without a network or a browser

## Stakeholders

Roles and people, not systems: everyone who has to work with the package,
decide about it, or live with what it does to them.

| Role | Expectation |
| ------ | ------------- |
| **Researcher at a terminal** | Gets page content on standard output and nothing else there, so the output can be redirected into a file: a failed fetch writes nothing and exits non-zero, rather than leaving an empty file that reads like a result |
| **Developer integrating the library** | Writes against a small, stable interface, substitutes it in their own tests, and takes on no dependency by installing it |
| **Maintainer** | Adds a detection pattern or a transport in one place, and can tell from the record why the current shape is what it is |
| **Operator of a fetched site** | Sees requests one at a time from a single machine, and no more than the caller asked for: no concurrency, no retry loop, no scheduler. Escalation is the only reason one URL is requested more than once |

## Functional Requirements

Requirements state observable behaviour only: what the package does, not
which library does it, where anything is kept, or how a body is judged to
be one thing rather than another.

| ID | Description |
| ---- | ------------- |
| FR01 | The package shall fetch the content of an HTTP or HTTPS URL and return it either as raw markup or as markup stripped to text. |
| FR02 | The package shall reject a URL whose scheme is neither HTTP nor HTTPS, at every entry point, before any request is issued or any browser is launched. |
| FR03 | The package shall classify a response body as a bot wall, as a not-found or gone page, or as too short to be a real page, without reference to the transport that produced it. |
| FR04 | The package shall retry a classified-failed response through a more capable transport, and shall stop at the first transport that returns a body it does not classify as failed. |
| FR05 | The package shall treat a not-found or gone verdict as final and shall not retry it through another transport. |
| FR06 | The package shall let a caller name one transport, in which case a classified-failed response is a failure rather than a reason to escalate. |
| FR07 | The package shall report which transport produced the returned content, including when it came from the store rather than the network. |
| FR08 | The package shall fetch a list of URLs through one browser session and return one result per URL in the order requested. |
| FR09 | The package shall store a returned body on disk under the URL and the requested form, and shall serve a later request for the same pair from that store. |
| FR10 | The package shall neither store nor serve a body it classifies as failed, and shall remove such an entry from the store when it encounters one. |
| FR11 | The package shall sweep the store of such entries on request, and shall be able to report what it would remove without removing it. |
| FR12 | The package shall run when no optional browser library is installed, skipping each transport whose library is absent and reporting the skip. |
| FR13 | The package shall terminate only browser processes it started, and only those whose descent from the running process can be established. |
| FR14 | The command-line entry point shall distinguish, in its exit status, every URL returning content from none returning content from some returning content. |
| FR15 | The package shall expose a substitutable page source so that consuming code can be exercised with neither a network nor a browser. |

## Quality Goals

Goals are in priority order, highest first.

| ID | Quality | Goal | Motivation |
| ------ | --------- | ------ | ------------ |
| QG01 | Correctness | A page that exists and is reachable is never reported as absent | A wrong "failed" verdict is silent and terminal: the caller gets an empty result and a non-zero status for a page that was there, with nothing to distinguish it from a page that genuinely is not, and no cheaper way to find out than fetching it by hand |
| QG02 | Functional Correctness | A body that is a bot wall, a throttle stub or a not-found page is never returned to the caller and never survives in the store | These bodies are large enough and well-formed enough to pass for content, so a consumer cannot tell one from a page by inspecting it — and once stored, one poisons every later fetch of that URL until something deletes it |
| QG03 | Portability | The package installs and runs with the standard library alone, on Linux and on Windows, from Python 3.10 upwards | The default install is the one every consumer gets, and it is also the one with no browser to escalate to — so any behaviour that assumes a browser is available fails exactly where there is no fallback |
| QG04 | Reliability | A failure inside one transport ends that transport and no more: the next one still runs, and a browser that was launched is still released | Each transport is a third-party engine with its own failure modes, and one that raises through the ladder converts a recoverable fetch into a total failure while leaving a Chrome process behind |
| QG05 | Security | A URL can only ever cause an HTTP or HTTPS request, and a running process is only ever signalled when it descends from this one | Both boundaries protect against a caller's input, not the caller: a URL from a redirect chain or a scraped list reaches the fetcher unexamined, and a sampling-based cleanup would kill a browser window somebody was using |
| QG06 | Performance Efficiency | A static page costs one HTTP request, a browser is launched only when the response says one is needed, and a repeated fetch of an unchanged page costs no request at all | The transports differ by more than an order of magnitude in cost, so launching a browser speculatively — or once per URL in a batch — dominates the runtime of everything else the package does |
| QG07 | Maintainability | A detection pattern, a transport, or a configuration value is added in one place, and the definition of a failed body has exactly one home | The classification rules are the part that changes most, because the sites change; two copies of the rule that decides what is junk would drift, and the drift would show up as a cache that keeps what a sweep deletes |
