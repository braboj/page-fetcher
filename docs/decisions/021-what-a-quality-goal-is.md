# ADR-021: What a quality goal is, and how the register is keyed

**Status:** Accepted
**Date:** 2026-08-07

## Context

Chapter 1 held seven quality goals. Three of them were not quality goals.

`QG05 Security` read "a URL can only ever cause an HTTP or HTTPS request,
and a running process is only ever signalled when it descends from this
one". That is FR02 and FR13 conjoined, asserting nothing the two
requirements did not already state absolutely. `QG03 Portability` restated
three givens from chapter 2: the empty dependency list, both platforms
built, Python 3.10 upwards. `QG04 Reliability` described what happens when
an engine raises, which scenarios Q8 and Q9 settle with one case each.

None of that was visible while the goals were written as paragraphs. It
became visible when they were cut back to one statement, at which point the
remaining four read as requirements too — because a quality goal is the
accuracy or completeness constraint on a capability some requirement
already states, and shares subject matter with it by construction.

The categories were also mixed. Five named ISO 25010 top-level
characteristics; `Correctness` is in no edition of the standard, and
`Functional Correctness` is a sub-characteristic being compared against
peers a level above it.

## Decision

**1. A statement a single observation can confirm is a requirement.**

This is the test. A quality goal is a universal no one case settles, a
measure of what something costs, or a property of the source rather than
the running system. Fault tolerance failed it and became FR13. The scheme
allowlist and process ownership failed it and were already FR02 and FR13.

**2. A goal leads with its quantifier.**

*Every* wall is recognised, not just the known ones. *No* page is lost to a
wrong verdict. Without the quantifier the sentence is the capability
restated, and there is no phrasing that avoids this — arc42's own example
has the same property, where "every broken internal link is found" is a
requirement without the word every.

**3. Each goal names an ISO/IEC 25010:2023 characteristic and
sub-characteristic.**

The pair locates the goal in the standard instead of under a category
chosen by feel, and it decides questions taste kept reopening. Whether the
false negative and the false positive are one goal or two is settled by
their being Functional correctness and Functional completeness: two
sub-characteristics, two rows.

The 2023 edition governs. It retired Portability in favour of Flexibility,
which is why adaptability across operating systems, Python versions and
installed engines sits under the latter.

**4. The register carries no motivation column.**

Every motivation written for it restated a chapter that already owned the
reasoning — the risk register, the transport table, the deployment
profiles. arc42's own example table has no such column.

**5. Chapter 10 holds the quality requirements that do not drive the
architecture.**

Reliability and Security keep their branches and their scenarios there. A
goal removed from chapter 1 is not a quality abandoned; it is one the
architecture is not shaped around.

## Alternatives considered

**Keep Security in chapter 1 regardless.** Auditors look for the heading,
and its absence reads as an omission. Rejected because the register would
then contain a row that fails its own stated test, and the test is worth
more than the heading. Security is visible in chapter 10 and in two
requirements.

**Grade the goals with numeric targets.** Rejected: nothing here has an
SLA, wall-clock is dominated by the site and the engine rather than by the
package, and chapter 6's cost bands already disclaim themselves. arc42's
example carries a number in one goal of six.

**Keep the pre-2023 category names.** They match the template's
parenthetical list. Rejected because that list is not the standard it names
— it includes Correctness, which no edition defines.

## Consequences

- The template's rule naming ISO 25010 categories points at a list drawn
  from the 2011 edition. This repository follows the 2023 edition, so
  `Portability` and `Usability` in that list do not apply here.
- Section 1.2 cannot point at section 10 the way arc42 says it should,
  because chapter bodies may not forward-reference. The link runs the other
  way: chapter 10's tree names the goal identifiers.
- Five goals, which is arc42's maximum. A sixth needs one of the current
  five to stop driving the architecture.
- A goal added later has to pass the single-observation test before it gets
  a row, and name a characteristic and sub-characteristic that exist.

## Related

- Chapter 9 gains a row per this record.
- **Upstream:** candidate — `base/core/docs.md`, whose `IDs and register`
  subsection names the ISO 25010 categories from a superseded edition and
  says nothing about what separates a quality goal from a requirement.
  Filed as `solid-ai-templates#997`.
