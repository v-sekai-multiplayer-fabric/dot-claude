# .claude

The agent configuration for this workspace, as a repository. Checked out at `.claude/` at the workspace root, which is where Claude Code looks, so it applies to every project on every side of the hexagon.

```sh
repo sync .claude
claude plugin marketplace add ./.claude
```

The second line is not optional and is easy to miss. `settings.json` enables
`hrr-memory@fabric` and `ledger@fabric`, and the marketplace they name is declared here in
`.claude-plugin/marketplace.json` — but registering it is per-desk, kept in user settings
rather than in this repository. Without it Claude Code cannot resolve `@fabric` and reports
the failure against `plugins/hrr-memory/.claude-plugin/plugin.json`, which parses fine and
passes `claude plugin validate`. The file it names is not the file that is wrong.

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
