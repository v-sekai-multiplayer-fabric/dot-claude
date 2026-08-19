---
description: The critical path through the plan, computed from the planned books
allowed-tools: Bash(python3:*)
---

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ledger.py" path`

That has already run. Report it as printed.

Every figure is HYPOTHETICAL: three-point estimates of work nobody has done, booked as
liabilities in `PLANNED-SECONDS` against a chart the spent ledger does not share. Do not add
them to anything `/ledger:report` prints, and do not present a planned second as progress.

The three points are quantiles of a posterior predictive, so `99% done by` is wide exactly
where the evidence is thin — that width is the finding, not a defect to round away. The
chain's total is sampled, so it is not the sum of the per-task p99s and will not reconcile
with one.
