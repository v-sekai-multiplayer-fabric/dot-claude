# hrr-memory

A set of ETNF relations in OpenUSD layers, queried by phase cosine similarity over HRR
vectors, plus the two things that were missing: something that reads it without being
asked, and a gate over the algebra it depends on.

The store lives here. It was in `infrastructure-logbook`, which meant the memory was
split across two repositories and only worked inside a synced workspace. One store, in
the agent configuration, which is what reads it.

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

## Layout

    memory/      the relations -- the source, and the only thing committed
    scripts/     hrr.py (the algebra), memory.py (the store), recall.py (the hook)
    tests/       the algebra's properties, and a control for each
    commands/    /remember

`CLAUDE_PLUGIN_ROOT` locates it, falling back to the script's own parent so it stays
runnable by hand. Nothing climbs for `.repo` any more and no path is configured.

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

## The gate

`tests/test_hrr.py` states `hrr.py`'s prose claims as properties over all inputs, and pairs
each with a control that breaks one thing and asserts the property goes red. Twenty-nine
run in about two seconds; CI is `.github/workflows/hrr.yml`.

Writing the controls was worth more than writing the properties. Two of the first ones did
not break their properties: a truncating quantiser still gave order-independent bundles,
and a stranger never beat a member at dim 2. Both were the control being wrong rather than
the code being right — and a control that passes without breaking anything is exactly the
green nobody should trust.

One finding fell out of it. `hrr.py` says bundling is order-sensitive at the bit level and
that the vectors "agree to 1e-14 radians either way". Reversing the components was measured
at **exactly 0.0** difference for every n and dimension tried, so the note is conservative.
The property is stated at the documented tolerance anyway, because the claim is what is
being gated, not the measurement of the day.
