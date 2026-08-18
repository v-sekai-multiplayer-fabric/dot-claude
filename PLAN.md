# Plan

Written 2026-08-18, closing the macOS side before the workspace moves to Windows for the
4090. It is here rather than in the logbook because it is about what an agent should pick up
next, which is what this repository is for.

Delete a section when it is done. A plan that outlives its work is the drift the gates exist
to catch.

## Unbuilt: the scope gate

Asked for and not written. The design, so it is not lost:

A branch declares `Scope:` in its first commit message, as a list of path globs. A check fails
the branch when its diff touches a path outside that list. Widening scope is then an edit to
that line — visible in the diff, visible in review — rather than something that happens by
accretion. A second check that a branch touches exactly one repository, since the cross-repo
hop is where creep hides best.

**Allow list, never a block list.** The declaration names what may be touched. Enumerating what
may not is unbounded and goes stale silently.

Two things it must not do, both learned the hard way today. It must not pass when it scanned
nothing — a branch with no `Scope:` line is a finding, not a skip. And it needs a negative
control that genuinely breaks it: two of four controls written for `test_hrr.py` did not break
their properties, and a control that passes without breaking anything is the green nobody
should trust.

Lives in `0-infrastructure/logbook/misc/checks/lib/check/scope.ex`, registered like `words.ex`,
with a `break:` clause for `mix check --self-test`. Roughly an hour.

## Red, and not from the branch that surfaced it

`every project is writable by us or listed read-only` fails on `main`:

    geogram is in BrunoLevy, which this project may not write to, and is not listed read-only
    pmp-library is in pmp-library, which this project may not write to, and is not listed read-only

From `fabric#61`, which added those two as manifest projects. The peer session could not
reproduce it and this one could, consistently, from the real workspace with `FABRIC_MANIFEST`
at `.repo/manifests`.

**Start with case.** The failure says `BrunoLevy`; the peer's passing run quoted `brunolevy`.
A case-sensitive org comparison explains both results at once. Check that before anything else.

## Open pull requests

| | |
| --- | --- |
| `infrastructure-logbook#3` | one property-testing framework per language |
| `manuals#214` | RFD 0132, armed on auto-merge, waiting on its base |
| `ecto_foundationdb#1` | draft: conflicting against `vsk`, needs a real rebase |
| `zone-guest-godot#2` | draft: its own `guest-riscv64-musl-boot` job fails |

Both drafts were marked ready while red and were put back. Ready means ready to merge.

## The memory plugin

`plugins/hrr-memory/` holds the store, the algebra, the hook and `/remember`. It does **not**
enable itself — a hook that runs on every prompt is capability, and capability here arrives as a
diff somebody approved:

    /plugin marketplace add <workspace>/.claude
    /plugin install hrr-memory@fabric

`memory.py verify` shells out to `usdcat`, which reaches this workspace through the flow
adapters at `6-datasource/flow`, not a pip wheel. That is why CI runs the property tests and
leaves `verify` on the desk. Do not "fix" CI by installing a second copy of USD.

## Notes for the Windows side

**`repo start` before committing.** `repo sync` leaves a project on a detached HEAD, and the
remote is named for the organisation rather than `origin`. Both bit us today.

**"ahead N" is not "unsaved".** `repo start` points a topic branch at the manifest revision, so
31 of 39 topic branches read as ahead of something they were never meant to merge into. The only
test that holds is whether the tip is reachable from any remote ref; `git log @{u}..` is a proxy
that goes wrong in a new way each time. `repo prune <project>` lists before it acts and removes
only branches with nothing unmerged.

**Two `fabric` names are stale, ungated, and safe to fix.** `service-zone`'s README still titles
itself `fabric-zone-domain` and `service-behaviour`'s `fabric-behaviour-domain`; neither name
exists on the org.

**`5-repository/entity-store/`** holds real content, has no `.git`, and is in no manifest.
`repo sync` will not touch it and nothing backs it up. Do not tidy it — find out what it is.

## Where the work was going

`7-service/see-through`. Everything above is what got in the way of it.
