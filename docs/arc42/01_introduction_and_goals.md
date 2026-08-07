# Introduction and Goals

pagefetch retrieves the content of a web page and hands it back as text or
HTML. What distinguishes it from a plain HTTP request is that it reads what
came back before accepting it: a bot wall, a throttle stub and a "page not
found" body all arrive looking like a page, often with a success status.
pagefetch recognizes those from the body alone and escalates through
progressively more capable and more expensive transports until one returns
something that is actually a page. Escalation answers a response that
failed; a caller who needs a page assembled in the browser names that
transport instead.

It is built for reading a handful of pages at a time: research data, or a
site owner checking how far an automated client gets against their own
protection. It paces nothing itself — no rate limiting, no backoff, no
scheduling — so a caller needing those supplies them and drives pagefetch
one URL at a time.

## Requirements Overview

- Return the content of a page by the cheapest transport that works, so
  the common case costs a single HTTP request
- Recognize a failed response from its body, because the status code does
  not distinguish a bot wall or a soft-404 from a real page
- Never hand back, or store, something that is not a page
- Install and run with nothing but the standard library, so a consumer
  takes on no dependency to get the common case
- Stay substitutable in a consumer's tests, so code that fetches pages can
  be tested without a network or a browser

### Functional Requirements

Functional requirements state observable behaviour: what the package does,
not how it does it. A library, a file layout, or the rule behind a verdict
is design and belongs elsewhere.

| ID | Description |
| ---- | ------------- |
| FR01 | The package shall fetch the content of an HTTP or HTTPS URL and return it either as raw markup or as markup stripped to text. |
| FR02 | The package shall reject a URL whose scheme is neither HTTP nor HTTPS, at every entry point, before any request is issued or any browser is launched. |
| FR03 | The package shall classify a response body as a bot wall, as a not-found or gone page, or as too short to be a real page. |
| FR04 | The package shall retry a classified-failed response through a more capable transport, and shall stop at the first transport that returns a body it does not classify as failed. |
| FR05 | The package shall treat a not-found or gone verdict as final and shall not retry it through another transport. |
| FR06 | The package shall let a caller name one transport, in which case a classified-failed response is a failure rather than a reason to escalate. |
| FR07 | The package shall report which transport produced the returned content, including when it came from the store rather than the network. |
| FR08 | The package shall fetch a list of URLs and return one result per URL in the order requested. |
| FR09 | The package shall retain a returned body under the URL and the requested form, and shall serve a later request for the same pair from what it retained, without issuing a new request. |
| FR10 | The package shall neither store nor serve a body it classifies as failed, and shall remove such an entry from the store when it encounters one. |
| FR11 | The package shall sweep the store of such entries on request, and shall be able to report what it would remove without removing it. |
| FR12 | The package shall run when no optional browser library is installed, skipping each transport whose library is absent and reporting the skip. |
| FR13 | The package shall continue to the next transport when a transport raises, and shall release every browser, event loop and session it acquired, whatever the outcome. |
| FR14 | The package shall terminate only browser processes it started, and shall terminate none where it cannot establish that it started them. |
| FR15 | The command-line entry point shall distinguish, in its exit status, every URL returning content from none returning content from some returning content. |
| FR16 | The package shall expose a substitutable page source so that consuming code can be exercised with neither a network nor a browser. |

## Quality Goals

Requirements say what the package does; quality goals say how well. Only
the few that shape the design belong here. If a single test can settle it,
it is a requirement and belongs in the table above. Characteristics and
sub-characteristics are ISO/IEC 25010. Highest priority first.

| ID | Characteristic | Sub-characteristic | Goal |
| ---- | ---------------- | -------------------- | ------ |
| QG01 | Functional Suitability | Functional correctness | No page that exists is lost to a wrong verdict |
| QG02 | Functional Suitability | Functional completeness | Every wall and error page is recognised, not just the known ones |
| QG03 | Flexibility | Adaptability | Behaviour is correct on every supported operating system, Python version and set of installed engines |
| QG04 | Performance Efficiency | Resource utilization | No request or browser is spent that the response did not require |
| QG05 | Maintainability | Modifiability | Every rule has exactly one place to change |

## Stakeholders

Roles and people, not systems: everyone who has to work with the package,
decide about it, or live with what it does to them.

| Role | Expectation |
| ------ | ------------- |
| **Researcher at a terminal** | Gets page content on standard output and nothing else there, so the output can be redirected into a file: a failed fetch writes nothing and exits non-zero, rather than leaving an empty file that reads like a result |
| **Developer integrating the library** | Writes against a small, stable interface, substitutes it in their own tests, and takes on no dependency by installing it |
| **Maintainer** | Changes the package itself — a detection pattern, a transport, a configuration value — each in one place, and finds the reasoning behind the current shape written down rather than having to reconstruct it |
| **Site owner testing their protection** | Learns which transport got through, or that none did — a site no rung passes is a result, not a failure. A challenge needing a human gesture is the ceiling: nothing here attempts one |
| **Operator of a site someone else fetches** | Sees requests one at a time from a single machine, and no more than the caller asked for: no concurrency, no retry loop, no scheduler. Escalation is the only reason one URL is requested more than once |
