# .claude

The agent configuration for this workspace, as a repository. Checked out at `.claude/` at the workspace root, which is where Claude Code looks, so it applies to every project on every side of the hexagon.

```sh
repo sync .claude
```

| | |
|---|---|
| `settings.json` | the workspace's settings: tracked, shared, reviewed |
| `settings.local.json` | one desk's answers. Gitignored, and stays that way |
| `CLAUDE.md` | what this repository is, and the rule for adding a permission |

## Why a repository

It was going to be a `linkfile` into `0-infrastructure/logbook`, and that was refused: a symlink is invisible to every check here. `repo status` cannot see drift in it, nothing gates it, and one repository's permission settings would quietly become every project's.

A repository is ordinary instead. Permissions arrive in a diff somebody approved, a widening has a commit behind it, and `repo status` reports this like anything else. The manifest entry is `name=".claude" path=".claude"`, which recomposes to itself.

`0-infrastructure/logbook` holds the conventions — how work is done here, for people and agents both. This holds capability: what an agent may do without asking. `CLAUDE.md` says why the two are separate.
