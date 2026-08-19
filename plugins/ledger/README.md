# ledger

The workspace's hours, booked from git and validated by tackler. Four commands, each one
motion: the shell has already run by the time the turn starts, so nothing here is a
conversation about what to run next.

    /ledger:report [--since N] [--by-project]   SPENT seconds, by lane or by project
    /ledger:path                                HYPOTHETICAL, the critical path
    /ledger:build                               rebook from git. Exclusive
    /ledger:verify                              tackler, then byte-identical regeneration

## The books are not in here

`ledger.py` is this plugin's. The books stay in `0-infrastructure/logbook/ledger`, where
they are tracked, reviewed and gated by `Check.Ledger`.

That split is the same one `CLAUDE.md` beside this directory draws. What an agent may do
without being asked twice is capability, and capability belongs with the agent
configuration. A spent second is a record of this workspace, and a record belongs to the
repository that keeps records — where a change to it arrives as a diff somebody approved,
which is exactly what a generated ledger needs and what a plugin directory would not give
it.

`_ledger_dir()` is the join. It takes `FABRIC_LEDGER` when set, the way `FABRIC_MANIFEST`
names the manifest and for the same reason; otherwise it climbs from this plugin to the
directory holding `.repo` and looks for the logbook checkout under it; otherwise it climbs
from the working directory. Finding nothing raises. There is no empty default, because a
ledger reader that quietly finds no books reports 0 s spent, and a gate cannot tell that
from a lull — the same climb, got wrong once before, cut the ledger from 326 sessions to 3.

## What one motion means here

Each command is a single `!` line that runs before the model sees anything, and the prose
under it says how to report what came back rather than what to run next. `/ledger:report`
prints the split and then the directory it read, because a number nobody can locate is a
number nobody can check.

`build` and `verify` both **write** — verify regenerates the books to compare them — so both
open with the same guard: if a `ledger.py build` or `verify` is already running anywhere on
this machine, they say so and do not start a second. The guard has both controls, and the
negative one matters more than it looks: the check itself contains the string it greps for,
so it is anchored at the start of the process line to keep it from matching the shell that
is running it. It catches a collision, not an intention. An agent about to start a build is
invisible to `ps`, so the handshake the conventions ask for still holds.

## Install

```sh
/plugin marketplace add /path/to/workspace/.claude
/plugin install ledger@fabric
```

## Requirements

`python3`, and `tackler` for `/ledger:verify` — an operating-system tool, like gcc, never
vendored and never imported: `cargo install tackler`. Missing it is a failure with a name,
not a skip.
