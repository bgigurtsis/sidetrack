# Sidetrack

Send large file reads and routine code generation to a smaller model. Keep your
chosen main model for reasoning and review. Uses your existing subscription
sign-in, with no Portal or API key.

| Client | Worker | Routing |
| --- | --- | --- |
| Claude Code | Haiku, or Luna with an OpenAI key (opt-in) | Hooks redirect large reads; skills handle generation |
| Codex | Luna | Global instructions request native subagents |

## Install

**Claude Code** - requires Python 3.10+:

```sh
claude plugin marketplace add bgigurtsis/sidetrack
claude plugin install sidetrack@sidetrack
```

**Claude Code with Luna instead of Haiku** (optional, needs an OpenAI API key). After installing the plugin:

1. Save your key on one line in `~/.claude/sidetrack/openai_key`, or export `OPENAI_API_KEY`.
2. Add this to `~/.claude/settings.json` (merge into an existing `env` block if you have one):

```json
{ "env": { "SIDETRACK_BACKEND": "openai" } }
```

3. Start a new Claude Code session.

Luna calls go straight to the OpenAI API, so they take a couple of seconds and are billed to your OpenAI account rather than your Claude plan. To pick a different model or endpoint, set `SIDETRACK_OPENAI_MODEL` or `SIDETRACK_OPENAI_BASE_URL` in the same `env` block. Full details in [the Claude Code guide](docs/claude-code.md#using-luna-with-an-openai-api-key).

**Codex** - requires Python 3.11+, a current Codex client, and Luna access:

```sh
git clone https://github.com/bgigurtsis/sidetrack.git
cd sidetrack
python3 codex/install.py install
```

On Windows, use `py -3` instead of `python3`. Start a new task after installing.

## How it works

1. Your main model gives the worker a focused question or specification and file paths.
2. **Bulk-reader** reads the files and returns concise findings. **Code-writer** follows reference files and writes code directly to the workspace.
3. Your main model reviews the findings or changes and checks the result.

```text
+--------------+   (1) question or spec + file paths   +----------------+
|              | ------------------------------------> |                |
|  Main model  |                                       |     Worker     |
|   (yours)    | <------------------------------------ |  Haiku / Luna  |
|              |   (2) short findings, or a file       |                |
+--------------+       written straight to disk        +----------------+
```

Small tasks stay with the main model. Debugging, architecture, and final review
stay there too. Codex routing is advisory, so it may not delegate every eligible
task. Workers consume subscription allowance; savings vary and are not guaranteed.

## Guides

- [Claude Code setup, settings, and manual install](docs/claude-code.md)
- [Codex setup and removal](codex/README.md)
- [Codex test results](codex/TESTING.md) · [Run a live test](codex/smoke-test.md)

Inspired by Spotify's [shunt](https://github.com/spotify/portal-ai-plugins).
[MIT licensed](LICENSE).
