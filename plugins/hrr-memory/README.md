# hrr-memory

The memory in `infrastructure-logbook` is a set of ETNF relations in OpenUSD layers,
queried by phase cosine similarity over HRR vectors. It already had `memory.py`. What it
did not have was anything that read it without being asked, so a fact recorded on Monday
was only recalled if somebody remembered it was there — which is the one thing memory is
for.

This plugin closes that. It is two pieces and neither holds any memory of its own.

## What it does

**Recall runs on every prompt.** A `UserPromptSubmit` hook encodes the prompt the same way
the relations were encoded and prints what clears the floor. Anything it prints becomes
context for that turn.

**`/remember` writes one fact.** It is a command rather than a hook because writing is a
judgement — which kind, which entities, whether the fact is already there — and because
the relations are tracked files, so a write is a branch and a pull request.

## Install

```sh
/plugin marketplace add /path/to/workspace/.claude
/plugin install hrr-memory@fabric
```

Enabling it is a capability change and gets the same review as any other in this
repository, which is why it is two explicit commands rather than a line this pull
request added to `settings.json` on your behalf.

## What it will not do

**It never costs the turn.** No workspace, no `memory.py`, unreadable relations, a
subprocess that times out, malformed input on stdin — every one of them exits silent and
zero. A memory that cannot be read is not a reason to fail a prompt.

**It stays quiet.** Nothing clears the floor, nothing is printed. Prompts under twelve
characters — `continue`, `ok`, `go on` — are not queried at all, because there is nothing
in them to match on. A hook that speaks every turn is one nobody reads by the fourth time.

**It does not present memories as instructions.** What it prints says so: background, true
when written, verify any file, flag or number before relying on it.

## How it finds the memory

By climbing to the directory that holds `.repo`, which is how every project in this
workspace finds anything, and how `Check.Lib.workspace_root` already does it. No path is
configured here and none is hardcoded, so the plugin works from any checkout and is silent
outside a synced workspace.

The SQLite index is derived and gitignored. The hook rebuilds it when it is missing or
older than any `.usda` beside it — about a second — and otherwise leaves it alone. A stale
index does not fail; it silently answers from an older memory, which is worse, so the mtime
comparison is the point rather than an optimisation.

## Knobs

| variable | default | |
| --- | --- | --- |
| `FABRIC_MEMORY_FLOOR` | `0.10` | similarity below this is not shown |
| `FABRIC_MEMORY_N` | `3` | how many to ask for |

Measured on the 16 relations present when this was written: rebuild 1.2 s, warm recall
144 ms. The floor is set where it is because scores run about 0.25 for a direct hit and
0.07 for an unrelated one; 0.10 keeps the second kind out.
