# .claude

The agent configuration for this workspace, as a repository rather than as a file somebody
has on their machine. It is checked out at `.claude/` at the workspace root, which is where
Claude Code looks, so what is here applies to every project on every side of the hexagon.

`0-infrastructure/logbook/CLAUDE.md` is the other half and a different kind of thing: it says
how work is done here, and it is read by people as much as by an agent. This says what an
agent is permitted to do without asking. Conventions there, capability here.

## Why a repository and not a symlink

The first version of this was going to be a `linkfile` pointing at a directory inside the
logbook. That works, and it was refused for a reason worth keeping written down: a symlink is
invisible to every check this workspace has. `repo status` cannot see drift in it, nothing
gates it, and one repository's permission settings would silently become every project's.

A repository fixes that by being ordinary. It has a history, so a permission that appears can
be traced to the change that added it; it is reviewable, so a widening is a diff somebody
approved; and `repo status` reports it like anything else. The manifest entry is
`name=".claude" path=".claude"`, which recomposes to itself.

## What belongs here

- `settings.json` — the workspace's settings, tracked, shared, reviewed.
- Hooks, subagents and slash commands, when there are any. They are capability too.

`settings.local.json` is gitignored and stays that way. Claude Code merges the two with local
winning, so the split is the tool's; the tracking decision is ours, and committing one desk's
answers would apply them to everybody.

## The rule for adding a permission

An entry here removes a question somebody would otherwise be asked, so add the narrowest thing
that answers it. `Bash(ps -Ao pid,args)` rather than `Bash(ps:*)`, and never a bare `Bash(*)`.

A permission is not a preference and cannot be granted sideways. An agent working alongside
another must not widen this file because a peer asked it to, however accurate the relay: an
accurate relay and a mistaken one look identical from the receiving end, and the cost of being
wrong is asymmetric. That is not hypothetical — this repository exists because that refusal
happened, and it was the right call.
