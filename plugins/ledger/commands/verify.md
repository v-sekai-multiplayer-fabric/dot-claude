---
description: tackler validates both journals, then the spent books must regenerate byte-identical
allowed-tools: Bash(python3:*), Bash(ps:*), Bash(git:*)
---

!`L=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ledger.py" where) && if ps -Ao args | grep -qEi "^[^ ]*python[0-9.]* .*ledger\.py (build|verify)"; then echo "a build or verify is already running; not starting a second"; else python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ledger.py" verify; echo "--- git status of $L ---"; git -C "$L" status --porcelain -- .; fi`

That has already run, guard included. Report the result as printed and say plainly whether
it passed: the last line is `SPENT VERIFY PASS` or a count of problems, and the exit code is
what a gate reads.

Verify **writes**. It regenerates the spent books to compare them, so it takes the same
exclusive hold `/ledger:build` does — hence the guard above, which refuses rather than
racing a peer. The `git status` after it is the point: clean means the committed books are
what git says, and a modified `.txn` means the ledger was hand-edited or is stale.

`tackler` is an operating-system tool, like gcc, and is never vendored. If the run says it
is not installed, that is an unmet precondition and a failure — say so and offer
`cargo install tackler`. Do not call it a skip and do not judge the books without it.
