# Codex setup details

Install Python 3.11+ and a current Codex CLI. Sign in with ChatGPT using `codex login`.
`codex login status` must report ChatGPT sign-in. Luna must be available to the
account; subscription and managed-workspace restrictions still apply. Sidetrack
never reads credentials or falls back to API-key billing.

## Destination

Run `python3 codex/install.py install` from the checkout. The destination is
`$CODEX_HOME`, or `~/.codex` when unset. Supply `--codex-home /path/to/home` to choose
another home. Install separately on remote hosts. Start a new task afterward.

Installed files:

```text
skills/sidetrack-luna/SKILL.md
skills/sidetrack-luna/scripts/sidetrack.py
sidetrack/install.json
```

One marked routing block is appended to global `AGENTS.md`, or an existing
nonempty `AGENTS.override.md`. Existing instructions, config.toml, and sign-in
are preserved. The main model is never changed. Both modes call the CLI with Luna;
Sidetrack no longer installs native agents. No blocking hooks are installed.

## Updates and migration

Pull the latest checkout and run the installer again. Identical installs are a
no-op. Recorded native-agent installations automatically migrate: old agents move
into dated `sidetrack/backups/` directories, the skill is replaced, and the routing
block switches to the CLI. No permanent deletion is used.

Unowned target files or user edits to managed files cause a conflict instead of
being overwritten. Preserve edits and restore the installed version before
updating or removing. Custom, manually created agents outside Sidetrack's install
record are not removed automatically.

Run `python3 codex/install.py uninstall` to remove active Sidetrack files and its
routing block. Backups remain recoverable. `--dry-run` previews install or removal.
Empty directories can remain. Avoid simultaneous installs or edits to managed
files. On filesystem errors, inspect the error and backups before retrying.

## Troubleshooting

- Use `python3 codex/install.py status` to verify installed files.
- The CLI must be runnable from Codex's shell. On Windows the wrapper finds the
  desktop app's native executable; set `--codex-bin` to codex.exe if necessary.
- Keep normal sandbox and approval controls. A blocked subprocess may need a
  narrowly scoped execution approval. Sidetrack does not bypass those controls.
- `AGENTS.override.md` can shadow earlier routing. The installer detects this;
  uninstall and reinstall to move the routing into the active instruction file.
- Inputs must be UTF-8 text inside the selected workspace, totaling at most 500 KB.
  Targets must be new files in existing directories. See [CLI options](CLI.md).
- For missing evidence, pass additional context files in a new invocation. Summaries
  may be incomplete; review source sections and generated diffs before relying on them.

## Official references

- [Authentication](https://learn.chatgpt.com/docs/auth)
- [Non-interactive Codex](https://learn.chatgpt.com/docs/non-interactive-mode)
- [Global instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

The Claude Code implementation uses its own configuration and is unaffected.
