# ADR-024: Conflicting transport flags resolve to the most escalated tier

**Status:** Accepted
**Date:** 2026-08-07

## Context

The CLI has four transport flags, one per rung of the ladder. Passing more
than one has never been rejected: `_parse_transport` tests them in a fixed
order and returns the first it finds, so `--js --headed --headless` is
`HEADLESS`.

No test covered the combination until #36, which pinned it. The journal
recorded at the time that pinning was not deciding — whether the combination
should instead be an error was left as an open question, and carried forward
as an outstanding item ever since. ADR-006 later renamed the flags off their
libraries, so the item survived in the journal spelled `--js --uc
--nodriver`, in a vocabulary the CLI no longer has.

Since #57 the behaviour has carried a rationale: the `_parse_transport`
docstring says flags passed together resolve to the most escalated one
rather than being rejected, and the test comment gives the reason. That
describes what the code does. It is not the same as having decided that what
it does is right, which is the question the journal kept re-raising.

## Decision

**1. Combined transport flags are not an error.**

The most escalated of them wins and the fetch proceeds.

**2. Precedence is the AUTO ladder read from the top rung down.**

`HEADLESS` over `HEADED` over `JS` over `HTTP` — the reverse of the order
AUTO climbs them, since AUTO stops at the first rung that works and this
stops at the last rung asked for. Position in `argv` is irrelevant; the
parser's own order decides, so a flag assembled into the command line early
does not beat one appended later.

**3. The reason is what asking for a rung implies.**

Nobody reaches for `--headless` first. Asking for a bot-bypass tier at all
is evidence of having already been failed by something cheaper, so when two
flags disagree the more escalated one is the one carrying that evidence. The
weaker flag is at worst redundant.

**4. AUTO is the absence of a flag, so it is never in the conflict.**

There is no `--auto` to combine with anything, and nothing resolves *to*
AUTO except an empty flag set.

## Alternatives considered

**Reject conflicting flags as a usage error.** The obvious shape — the CLI
parses `argv` by hand rather than through argparse, so there is no mutually
exclusive group to declare and the check would have to be written. Rejected
on what it would buy: the mistake it catches is typing two flags, and under
a total order that is not a mistake with an ambiguous outcome. It is also a
breaking change to behaviour stable since the first version, in exchange for
failing a command whose intent is already determinate.

**Resolve to the cheapest flag instead.** Rejected: it makes `--http`
silently defeat every other flag on the line. Of the two directions this is
the one that loses a page — the caller asked for a browser and got a plain
request, which on a protected site returns a wall.

**Resolve by position — last flag wins.** Rejected because it makes the
result depend on how a wrapper assembles the command line, and a wrapper
appending a flag to a base command is exactly where combinations come from.
A total order gives the same answer to both spellings.

## Consequences

- `test_transport_precedence_is_slowest_wins` is the executable form of this
  record. Changing what it pins is superseding this decision.
- A fifth rung has to be placed in two orders that must stay in agreement:
  the AUTO ladder in `_escalate`, and the reverse of it in
  `_parse_transport`. ADR-014 already requires re-reading before a fifth
  tier is added; this is another thing that has to move with it.
- `--http` with anything else is the case where a caller most plausibly
  meant to restrict rather than escalate, and they get the browser instead.
  Accepted: the alternative loses pages silently, and `--http` alone still
  means exactly what it says.
- The usage text now states the rule, so the behaviour is discoverable at
  `--help` rather than only in a docstring and a test.

## Related

- ADR-006, which named the transports for what they require of the caller
  and gave these flags their current spelling.
- Chapter 9 gains a row per this record.
