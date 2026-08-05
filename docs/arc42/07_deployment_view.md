# Deployment View

## What Deployment Means Here

There is nothing to deploy in the operational sense: no server, no
scheduled run, no artefact published to an index. What varies between
installations is which transports exist, and that is decided entirely by
which optional engines a consumer installed. This chapter covers the
installation profiles that follow from that, the environments the package
runs in, and the pipeline that gates a change.

## Installation Profiles

The package sits under a source directory rather than at the repository
root, so a bare checkout cannot import it. The install is what resolves the
import — not the working directory — and it is a prerequisite rather than a
convenience.

| Profile | What it installs | Transports available |
| --------- | ------------------ | ---------------------- |
| Base | The package alone; no third-party package is pulled in | Plain HTTP only |
| Browsers | The three engines as an optional extra, plus a browser download step for one of them | All four |
| Development | Linter, type checker, test runner, coverage and the hook manager | Plain HTTP only, unless the browsers extra is added as well |

The development profile deliberately does not include the engines. The
suite runs with no network and no browser, so installing them would change
nothing about what is tested and would add three large dependencies to
every contributor's environment.

## Runtime Environments

```text
+------------------------------+--------------------------------------+
| desktop, display available   | headless host: server, container, CI |
+------------------------------+--------------------------------------+
| http                         | http                                 |
| js                           | js                                   |
| headed      <- needs the     | headed      SKIPPED, no display      |
| headless       display       | headless                             |
+------------------------------+--------------------------------------+
| default install, either host: http only, the rest skipped and named |
+---------------------------------------------------------------------+
```

| Environment | Notes |
| ------------- | ------- |
| Developer desktop | The full ladder, and the only place the headed transport can run. The browser-driving code paths are exercised here by hand |
| Headless host | Three rungs. A URL behind a wall that only the headed transport clears does not come back, and the skip is reported rather than silent |
| Continuous integration | Base and development profiles only. No engine is installed and no request leaves the runner |

Consumers are expected to keep the retained-body store on a local
filesystem. Its location is a caller-selectable path defaulting under the
working directory, so a consumer running several entry points points them
all at one directory through a single environment variable.

## Pipeline

A change passes the same checks three times, at three costs.

| Layer | Runs | Covers |
| ------- | ------ | -------- |
| Editor | Continuously, while typing | Lint, format and type feedback from the same configuration the other two layers read |
| Commit hooks | On every commit, locally | Lint, format, comment layout and a secret scan |
| Continuous integration | On every pull request and every push to the protected branch | Everything the hooks cover, plus the version and platform matrix, coverage measurement, the executable examples and static analysis |

The middle layer can be bypassed with a flag, which is why the third
repeats it rather than trusting it.

The matrix builds both ends of the supported Python range and both
platforms. Both platforms are there because the process-cleanup module
takes a genuinely different path on each: on one it queries and signals,
on the other every call falls through to a no-op. Building only one would
leave the platform-specific module untested on the platform it targets.

Examples are executed rather than read. They install the package without
the development extra, because an example is what a consumer runs after
installing the library — so it has to work with the library alone, with no
test runner, no engines and no network.

One aggregate check is the required one for branch protection. Naming each
job individually in the ruleset would mean a job added later is not
required until somebody remembers to add it there too.

## Release

There is none. No version is published, no tag gates a distribution, and
consumers track the default branch of the repository. Publishing to an
index would bring documentation obligations that are currently recorded as
deferred rather than met.
