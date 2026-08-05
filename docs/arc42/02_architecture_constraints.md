# Architecture Constraints

## Technical Constraints

| Constraint | Background |
| ------------ | ------------ |
| Runtime | Python 3.10 or later; both ends of the supported range are built, 3.10 and 3.13 |
| Dependencies | The declared dependency list is empty — the default install carries no third-party package |
| Dependencies | Browser engines are optional extras, imported inside the transport that uses them; an absent library skips its transport and is reported, never raised |
| Platform | The headed transport drives a visible browser window and cannot run on a host with no display, which includes every continuous-integration runner |
| Platform | Orphaned-browser cleanup is Windows-only; on other platforms the process query returns nothing and cleanup does nothing |
| Platform | Both platforms are built, because the process-cleanup module takes a different path on each |
| Testing | The suite runs with no network access and no browser installed |
| Testing | No test may enumerate or signal processes on the host it runs on |

## Organizational Constraints

| Constraint | Background |
| ------------ | ------------ |
| Distribution | Not published to a package index; consumed as a clone or a git submodule |
| Branch protection | `main` is protected and takes no direct commits; one required status check aggregates the whole gate |
| Quality conventions | Defined in a shared template repository, vendored as a git submodule and pinned to a revision; the pin governs, not the submodule's upstream head |
| Decision records | Immutable once merged — a decision is changed by superseding it, never by editing it |
| Maintenance | One maintainer, and no release cadence |

## Licensing

The package is MIT and stays MIT. The three browser engines it can drive
are third-party packages a consumer chooses to install; the README's
dependency table lists them and their licences.

One of them carries an obligation worth stating rather than tabulating.
The engine behind the headed transport is AGPL-3.0. It is not vendored,
bundled or redistributed here, and its import happens inside the transport
that needs it, so an install of this package alone pulls in no AGPL code
and the licence reaches nobody. It reaches a consumer who installs that
engine and then distributes a network service built on the headed
transport: section 13 of the AGPL obliges that consumer to offer their
service's source to its users. A consumer for whom that is unacceptable
installs the other two engines and leaves the headed transport out — the
ladder then has three rungs and reports the missing one.

## Conventions

| Convention | Reference |
| ------------ | ----------- |
| Coding standards | ruff for lint and format, mypy for types, 88-character lines including Python inside the README |
| Comments | A block comment sits directly above what it documents, never to its right, and is separated from the next group by one blank line; both rules are enforced by a repository check rather than left to review |
| Documentation | Architecture documentation follows the arc42 template; the README is the single source of truth for project structure |
| Testing | pytest, with a coverage floor that only ever rises |
| Git | Typed branch and commit prefixes, one concern per pull request |
