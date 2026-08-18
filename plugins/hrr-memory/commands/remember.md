---
description: Write one fact to the fabric's HRR memory
argument-hint: [the fact, or nothing to be asked]
---

Record `$ARGUMENTS` in the fabric's HRR memory.

Run `memory.py` from the logbook — `0-infrastructure/logbook/misc/scripts/memory.py`,
found by climbing to the directory that holds `.repo`:

```sh
python3 <logbook>/misc/scripts/memory.py add "<content>" --kind <kind> --entities <names...>
```

Before writing it:

- **One fact per memory**, stated so it is true away from this conversation. Convert
  relative dates to absolute ones and name the decision rather than the discussion.
- **Pick the kind** from `memory/kinds.usda`: `feedback` for how work is done here,
  `project` for what is true of the work, `reference` for how to reach or run something.
- **Reuse entities** from `memory/entities.usda` rather than coining near-duplicates.
  Read that file first and pass existing names.
- **Do not record what the repository already says.** Code structure, git history and
  `CLAUDE.md` are read directly; memory is for what is not derivable from them.
- **Check it is not already there** with `memory.py recall "<the fact>"`. Update the
  existing relation instead of adding a second one that says the same thing.

Afterwards run `memory.py verify` — it must print `MEMORY VERIFY PASS` — and commit
only `memory/*.usda`. `fabric.sqlite3` is derived and gitignored; committing it would
store the same facts twice.

The relations are tracked files in a repository somebody reviews, so this is a commit
on a branch and a pull request, not a local write.
