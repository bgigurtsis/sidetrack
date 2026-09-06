# Sidetrack for Codex

Use **Luna through the Codex CLI** for substantial file reading and routine code
generation. Your selected main model handles reasoning and review. Uses your
existing ChatGPT/Codex subscription sign-in, without Portal, API keys, or subagents.

## Install or update

Requires Python **3.11+**, a current Codex CLI, and subscription access to Luna.
Run `codex login status` to check that you are signed in with ChatGPT.

```sh
python3 codex/install.py install
```

Run from this checkout. Windows: use `py -3` instead of `python3`. Start a new task
after installation. Existing Sidetrack subagent installations are migrated: old
agent files are archived and routing switches to the CLI.

## Use

Ask Codex to work normally, or invoke `$sidetrack-luna`. The installed skill calls
the script before loading bulk source into your main conversation.

You can also run it directly from this checkout:

```sh
python3 codex/cli.py --workspace /path/to/project read --question "Which services retry?" --paths src/services.py
python3 codex/cli.py --workspace /path/to/project write --spec "Generate the specified tests" --reference tests/test_users.py --target tests/test_orders.py
```

The script reads files, sends their contents to Luna, and returns a short answer.
In write mode it saves code to a **new target file**. Your main model reviews and
validates the result. Small tasks stay local; routing is advisory.

## Manage

```sh
python3 codex/install.py status
python3 codex/install.py uninstall
```

Settings and sign-in are preserved. Removal archives managed files in recoverable
backups. Workers consume subscription allowance; model availability and limits apply.

[Detailed setup](setup.md) · [CLI options](CLI.md) ·
[Comparison with subagents](CLI-COMPARISON.md) · [Tests](TESTING.md)
