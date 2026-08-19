---
description: What the hours went to, in seconds, read back from the books git generated
argument-hint: [--since N] [--by-project]
allowed-tools: Bash(python3:*)
---

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ledger.py" report $ARGUMENTS; echo "books: $(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ledger.py" where)"`

That is the whole answer and it has already run. Report the split as printed rather than
retyping the figures, and name the directory the last line gives, because the books are in
another repository than this plugin and a number nobody can locate is a number nobody can
check.

`--since` defaults to 90 days and `--by-project` breaks each lane into the repositories
under it. These are SPENT seconds — expenses, read back from the committed `.txn` files, not
recomputed. Nothing here is an estimate; the estimates are `/ledger:path`, in another
commodity against another chart, and the two are never added.

If the split is what was asked for, stop. Do not run `/ledger:build` to freshen it first:
build rewrites every book and is exclusive.
