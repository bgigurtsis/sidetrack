# Codex setup details

Install Python 3.11+ and use a Codex client with native subagent support. Luna
must be available through your existing ChatGPT/Codex sign-in. Kirby never changes
your selected main model or falls back to API-key billing.

## Destination and installed files

Run `python3 codex/install.py install` from the checkout. The destination is
`$CODEX_HOME`, or `~/.codex` when unset. Use `--codex-home /path/to/home` to choose
another home. Install separately on remote hosts. Start a new task afterward.

```text
agents/kirby_luna_bulk_reader.toml
agents/kirby_luna_code_writer.toml
skills/kirby-luna/SKILL.md
skills/kirby-luna/scripts/kirby.py
kirby/install.json
```

The reader and writer use `gpt-5.6-luna` with medium reasoning effort. One marked
routing block is added to global `AGENTS.md`, or an existing nonempty
`AGENTS.override.md`. Existing instructions, `config.toml`, and sign-in are
preserved. No blocking hooks are installed.

The skill requests native delegation for bounded, independent work while the
main model makes useful progress. If delegation is unavailable or blocked, the
main model reports the limitation and proceeds with targeted direct work. It
must not automatically send the same material through the optional CLI.

## Updates and migration

Pull the latest checkout and run the installer again. Identical installs are a
no-op. Recorded v1 native, v2 CLI, and v3 CLI-with-hook installations migrate to
v4 native routing. Changed and retired files are backed up under dated
`kirby/backups/` directories. The CLI remains available for explicit optional use.

For v3, migration removes only the exact recorded Kirby hook entry and archives
the retired read-hook script. Unrelated hooks survive. Ownership is checked before
files change; unowned targets or user edits to managed files cause a conflict
instead of being overwritten. Custom agents outside the record are not removed.

Run `python3 codex/install.py uninstall` to remove active Kirby files and its
routing block. Backups remain recoverable. `--dry-run` previews install or removal.
Empty directories can remain. Avoid simultaneous installs or edits to managed
files. On filesystem errors, inspect the error and backups before retrying.

## Optional direct-command approval

The CLI requires an explicit request to use it plus authorization for Luna to
process the selected task-relevant source through the signed-in Codex CLI.
Installing Kirby or encountering a native-agent failure is not that consent.

For users who additionally want a persistent direct-command permission:

```sh
python3 codex/install.py install --allow-luna
```

Choose this only if you authorize the installed script to send task-relevant
source, including private repository source, to OpenAI Luna through your signed-in
CLI. Agents must obtain that authorization before adding the flag. The rule at
`rules/kirby-luna.rules` matches the exact installing Python executable and absolute
installed script path. Restart Codex to load it. Reinstalling normally preserves
an existing managed rule; uninstalling archives it.

This permission trusts the installed script and its future updates. It does not
override other rules, managed policies, sandbox restrictions, or automatic approval
review. It is not a fix for an unauthorized-transfer rejection. Do not broaden
permissions or retry the transfer through another route to evade that rejection.

**Windows desktop limitation:** the direct rule did not match the app's
`pwsh.exe -Command "..."` wrapper in the historical local check. Do not allow all
PowerShell calls to compensate. Validate actual matching with `codex execpolicy
check --rules <codex-home>/rules/kirby-luna.rules -- <command and arguments>`.
See [Codex rules](https://learn.chatgpt.com/docs/agent-configuration/rules).

## Troubleshooting

- Use `python3 codex/install.py status` to verify installed files.
- Check that the client exposes native subagents and Luna. Start a new task after
  installation. Use direct work if the required capability is unavailable; do not
  silently change transport, model, or authentication.
- Keep normal sandbox and approval controls. Native agents still use model
  services and must respect the task's source-access and data-processing scope.
- `AGENTS.override.md` can shadow routing. The installer detects this; uninstall
  and reinstall to move routing into the active instruction file.
- Review cited source sections and generated diffs; summaries can omit details.
  CLI-specific limits and prerequisites are in [CLI options](CLI.md).

## Official references

- [Native subagents and custom agent configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Authentication](https://learn.chatgpt.com/docs/auth)
- [Global instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

Kirby was previously named Sidetrack. The skill name remains `kirby-luna`.
The rename and migration do not expand authorization to read or send data, change
destinations, or bypass approval review. Claude Code is unaffected.
