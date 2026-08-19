---
description: Rebook every session from git into the spent books and the chart. Exclusive; rewrites files.
allowed-tools: Bash(python3:*), Bash(ps:*), Bash(git:*)
---

!`L=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ledger.py" where) && if ps -Ao args | grep -qEi "^[^ ]*python[0-9.]* .*ledger\.py (build|verify)"; then echo "a build or verify is already running; not starting a second"; else python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ledger.py" build; echo "--- git status of $L ---"; git -C "$L" status --porcelain -- .; fi`

That has already run. Report how many sessions were booked into how many books, and then
what the `git status` shows — an empty status means the books were already what git says and
this build changed nothing, which is the ordinary outcome and worth saying outright.

**This is exclusive.** It rewrites every book under `ledger/spent/` and the generated chart
beside them, so a second one running concurrently would have the two fighting over the same
files. The guard above checks for a peer and refuses instead of racing; it cannot see an
agent that is about to start one, so if another agent is working in this workspace, say
you are about to build and wait to be told to go ahead.

The books are tracked files in another repository. A build that changes them is a commit on
a branch there and a pull request, reviewed like any other — never a local write left
sitting. A project that has left the manifest keeps its book: those hours were spent and
there is no git left to read them back out of.
