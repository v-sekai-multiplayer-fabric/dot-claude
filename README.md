# .claude

The agent configuration for this workspace, as a repository. Checked out at `.claude/` at the workspace root, which is where Claude Code looks, so it applies to every project on every side of the hexagon.

```sh
repo sync .claude
```

The plugins are not here. They live in the private `fire/agent-plugins`, which is its own
marketplace and is not a manifest project, so nothing syncs it and a `repo sync` removes a
clone left at `plugins/`:

```sh
claude plugin marketplace add fire/agent-plugins
```

Registering a marketplace is per-desk: it is kept in user settings, not in any repository
here, so a fresh checkout has none. When one is missing Claude Code reports the failure
against the plugin's `plugin.json`, which parses fine and passes `claude plugin validate` —
the file it names is not the file that is wrong.

| | |
|---|---|
| `settings.json` | the workspace's settings: tracked, shared, reviewed |
| `plugins/hrr-memory` | the fabric's memory: recall on every prompt, `/remember` to write |
| `plugins/ledger` | the hours, booked from git: `/ledger:report`, `:path`, `:build`, `:verify` |
| `settings.local.json` | one desk's answers. Gitignored, and stays that way |
| `CLAUDE.md` | what this repository is, and the rule for adding a permission |

## Why a repository

It was going to be a `linkfile` into `0-infrastructure/logbook`, and that was refused: a symlink is invisible to every check here. `repo status` cannot see drift in it, nothing gates it, and one repository's permission settings would quietly become every project's.

A repository is ordinary instead. Permissions arrive in a diff somebody approved, a widening has a commit behind it, and `repo status` reports this like anything else. The manifest entry is `name="dot-claude" path=".claude"`. The path is fixed by Claude Code, which reads that and nothing else, so the name gave way instead: a repository called `.claude` is hidden from an ordinary listing and clones into a directory most shells will not show you. `fixed_names` in the logbook carries the pair.

`0-infrastructure/logbook` holds the conventions — how work is done here, for people and agents both. This holds capability: what an agent may do without asking. `CLAUDE.md` says why the two are separate.
