# Testing

The default uses native Luna subagents. The optional CLI remains covered by
offline tests; the [CLI/subagent timings](CLI-COMPARISON.md) are historical.

## Offline tests

```sh
python3 -m unittest discover -s codex/tests -v
```

The suite covers CLI authentication checks, source paths and input limits,
stdin-only prompt transport, target overwrite protection, failed replies,
timeouts, and metrics. Installer coverage includes native assets, migration from
recorded v1/v2/v3 states, managed-hook removal, preservation of unrelated settings,
backups, and uninstall. Tests do not call models. Temporary test directories are
retained for inspection.

Run the command for the current result. GitHub Actions also runs the suite on
Windows, macOS, and Linux with Python 3.11 and 3.13; consult the latest Actions run.

## Live checks

Follow [the smoke test](smoke-test.md) in a new Codex task to verify native routing,
the requested Luna model, source citations, generated changes, and direct fallback
when native delegation is unavailable. Offline tests do not establish that an
installed client exposes native agents or that an account can use Luna.

The historical 6 September 2026 trials used Codex CLI 0.153.4 on Windows with
ChatGPT sign-in. Two CLI reader trials identified exceptions in a 601-line file;
two writer trials passed 16 integer-input checks each. Native-agent trials were
the comparison baseline. These results do not verify the current migrated
installation or establish savings or account eligibility.
