# ADR-025: A building block names the module that implements it

**Status:** Accepted
**Date:** 2026-08-07

## Context

Chapter 5 names seven building blocks for the role each plays — Contract,
Classification, Transport, Store, Host cleanup, Test double, Entry point.
The package has seven corresponding modules. Not one of the seven block
names is a module name.

Across all thirteen chapters a module filename appeared exactly once:
`network.py`, in chapter 9's index row for ADR-014. The README's project
structure table does list every module against a one-line purpose, but it
never uses the block names, so getting from **Store** to `cache.py` meant
inferring it through "`FileCache` — on-disk cache and junk sweep" in a
different document. The join was one inference away and stated nowhere.

The chapter is internally coherent, which is why it passed review
repeatedly — nothing in it is wrong. It simply does not connect to the tree
it describes.

Two effects made it worse than a missing convenience:

- **A role name collided with a real identifier.** "Transport" named both
  the building block implemented by `network.py` and the enumeration
  defined in `source.py`, in the same chapter, with nothing distinguishing
  them. `source.py`'s own docstring opened "Transport abstraction for page
  fetching", making it three uses of one word.
- **A role name forked the vocabulary.** The block is **Store**; the
  module, the three CLI flags and the README all say "cache".

Nothing decided any of this. There is no record establishing that blocks
are named for roles, and none establishing what the relationship to the
module tree is.

`base/core/docs.md` `[ID: docs-arc42]` bans source-file paths in chapter 3
and says nothing about chapter 5. Its concept-section rule — describe the
idea in prose, then map it to concrete identifiers in a table — is the
shape that was missing, but it is scoped to chapter 8.

## Decision

**1. Building blocks keep role names, and the chapter states the module.**

The level 1 table gains a `Module` column and each level 2 heading gains
its filename in parentheses. A role name is the right name for a document
explaining a design; what was missing was the join, not a better noun.

**2. The modules keep their names. The documents moved, not the code.**

The direction was settled by which set of names is load-bearing rather than
by which is better. Module names are cited 103 times across the records,
the chapters, the guides and `CLAUDE.md` — `network.py` alone 38 times —
and ADR-014 is titled "Keep network as one module". A rename would leave an
immutable record's own title naming a file that does not exist.

Two of the role names would also be worse as filenames than what they
replace. A `transport.py` that does not define `Transport` deepens the
collision it was meant to fix, and a `store.py` disagrees with
`--no-cache`, `--cache-dir`, `--clean-cache` and every README mention.

**3. Store and cache are two vocabularies, and the chapter says why.**

**Store** is the glossary term for a directory of retained bodies with no
expiry, chosen to avoid promising the expiry semantics "cache" implies.
arc42 uses it 38 times across nine chapters against two uses of "cache",
and it carries FR07, FR10 and FR11. `cache.py` is named for the word the
command line and the README use. Both are correct for their audience; the
defect was that nothing said so, and an undocumented deliberate split is
indistinguishable from an oversight.

**4. Where a block and its module disagree on a word, the chapter states
the reason.** Rule 3 generalised — it is the only part of this record that
constrains a chapter not yet written.

## Alternatives considered

| Alternative | Why rejected |
| -- | -- |
| Rename the modules to the block names | Makes the diagram and the tree agree by moving the side that is cited 103 times, including in ADR-014's title, which cannot be edited. Two of the seven names are also worse as files than what they replace. |
| Rename **Store** to **Cache** throughout arc42 | One word for one thing across code, CLI, README and chapters. Rejected: it is a defined glossary term distinguishing a store with no expiry from a cache, and it carries FR07, FR10 and FR11 — three numbered requirements would be reworded to match a filename. |
| Put the mapping in chapter 12, the glossary | The glossary already defines Store, so the module could hang off that entry. Rejected: the glossary defines terms, and this is a fact about the building block view. A reader of chapter 5 should not have to reach chapter 12 to learn what they are reading about. |
| Name the modules only in the diagram | Cheapest, and the diagram is what a reader looks at first. Rejected: the diagram is an export, so the mapping would live only in a PNG and its source — unsearchable from the prose that depends on it. |
| Leave it; the mapping is obvious from the tree | Six of seven are guessable with the source open. Rejected: **Store** to `cache.py` is not, "Transport" is actively ambiguous, and "obvious to someone who already knows" is the property that let this survive review. |

## Consequences

| Consequence | Detail |
| -- | -- |
| A new module means two edits, not one | The level 1 table and a level 2 heading. ADR-014 already requires re-reading before a fifth tier is added; this is another thing that moves with it. |
| The diagram carries filenames, so it changes more often | A rename that would previously have touched only the tree now needs a re-export. Accepted: renames are rare here, and the export procedure is PLAYBOOK 4.7. |
| The vocabulary split is now load-bearing prose | The sentence explaining Store against cache has to survive editing. If it is deleted, the split silently reverts to looking like an oversight. |
| Chapter 5 now contains source-file paths | Deliberate, and consistent with `[ID: docs-arc42]`, which scopes that prohibition to chapter 3. |

**Upstream:** the generic rule — an architecture document naming components
by role states where each role meets the implementation, and says why when
the words differ — is reusable and does not depend on this project's
domain. `base/core/docs.md` `[ID: docs-arc42]` is the candidate file, where
the equivalent rule for concept sections already exists and is scoped to
chapter 8. Filed as
[braboj/solid-ai-templates#1003](https://github.com/braboj/solid-ai-templates/issues/1003).

## Related

- ADR-014, whose title is the reason the modules were not renamed.
- ADR-020, which governs where a chapter diagram lives and requires the
  export be read before committing.
- Chapter 9 gains a row per this record.
