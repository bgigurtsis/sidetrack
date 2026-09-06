# Sidetrack for Codex

Use **Luna** for substantial file reading and routine code generation through your
existing Codex subscription sign-in. Your selected main model handles reasoning,
integration, and review. Both modes use native subagents; no API key or Portal.

## Install

Requires Python **3.11+**, a current local Codex client, and subscription access to
`gpt-5.6-luna`. Sign in with ChatGPT; `codex login status` checks your sign-in method.

From the Sidetrack checkout:

```sh
python3 codex/install.py install --dry-run
python3 codex/install.py install
```

Windows: use `py -3` instead of `python3`. Start a new Codex task afterward.

The installer adds two Luna agents, a skill, and a marked global routing block to
`~/.codex` (or `$CODEX_HOME`). It preserves your settings and sign-in. Use
`--codex-home /path/to/home` for another destination.

## Use

Ask Codex to work normally, or request a mode explicitly:

> Use Sidetrack's bulk-reader to find which services retry failed requests.

> Use Sidetrack's code-writer to generate tests in tests/test_orders.py,
> following tests/test_users.py, then review the changes.

The worker reads the source itself and returns a short summary. Your main model
can then read specific sections or review the generated diff. You can also invoke
`$sidetrack-luna` directly.

Routing is instruction-based, without blocking hooks. Small tasks and difficult
reasoning stay with the main model. Workers consume your subscription allowance;
model availability and usage limits apply. Already using Luna? Automatic
self-delegation is skipped.

## Manage

```sh
python3 codex/install.py status
python3 codex/install.py uninstall
```

Removal preserves unrelated instructions and archives managed files in recoverable
backups. Rerun the installer after pulling an update; it refuses to overwrite
user-edited managed files.

[Detailed setup and troubleshooting](setup.md) ·
[Test results](TESTING.md) · [Live test](smoke-test.md)
