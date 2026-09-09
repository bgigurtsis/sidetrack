# Kirby for Codex

Use **native Luna subagents** for substantial file reading and basic mechanical
boilerplate writes. Your selected main model handles reasoning, integration, and review.
The reader and writer use `gpt-5.6-luna` with medium reasoning effort.

## Install or update

Requires Python **3.11+**, a Codex client with native subagent support, and Luna
access through your existing ChatGPT/Codex sign-in.

```sh
python3 codex/install.py install
```

Run from this checkout. Windows: use `py -3` instead of `python3`. Start a new task
after installation. Recorded v1, v2, and v3 installations migrate to v4 native
routing. Migration removes the recorded Kirby read hook while preserving
unrelated hooks, settings, and sign-in.

## Use

Ask Codex to work normally, or invoke `$kirby-luna`. Codex delegates bounded read
or basic mechanical boilerplate work when it can run independently alongside useful main-model
work. The main model reviews findings or generated changes and validates them.

Small tasks and targeted reads stay with the main model. If native delegation or
Luna is unavailable or blocked, Codex reports the limitation and continues
directly. It does not automatically retry through the CLI, another model, or an
API key. Routing is advisory; no blocking read hook is installed.

The CLI remains installed as an optional tool. Use it only after an explicit CLI
request and authorization for the selected source to be processed by Luna through
the signed-in CLI. See [CLI options](CLI.md).

## Manage

```sh
python3 codex/install.py status
python3 codex/install.py uninstall
```

Removal archives managed files in recoverable backups. Workers consume account
allowance; model availability and limits apply. Native delegation remains subject
to normal permissions and approval review.

[Detailed setup](setup.md) - [Historical comparison](CLI-COMPARISON.md) -
[Tests](TESTING.md) - [Official subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents)
