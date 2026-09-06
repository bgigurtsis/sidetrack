# Claude Code setup

Stop paying frontier-model prices for grunt work. sidetrack is a Claude Code plugin that sends big file reads and boilerplate generation to Claude Haiku, so your main model only sees the answer.

Works with a Claude Code subscription alone. No API key, no extra service. Haiku is called through `claude -p`, so it bills against the plan you already have. If you do have an OpenAI key, you can switch the worker to GPT-5.6 Luna instead (see [Using Luna](#using-luna-with-an-openai-api-key)).

## Setup

Requires Claude Code and Python 3.10+ on your PATH.

```bash
claude plugin marketplace add bgigurtsis/sidetrack
claude plugin install sidetrack@sidetrack
```

Start a new Claude Code session. That's it.

## What it does

Two hooks and two skills.

**Hooks** run before every Read and Bash call. If Claude tries to read a whole file over 350 lines, or run `cat` on one, the hook blocks it and tells Claude to use sidetrack instead. Targeted reads always pass: Read with `offset`/`limit`, piped commands like `cat file | grep`, `head -n 40`, `sed -n`.

**`sidetrack read`** sends files plus a question to the worker and returns a short bulleted answer. Ask again with the same files for follow-ups. The files never enter your main context.

```bash
python "$CLAUDE_PLUGIN_ROOT/scripts/sidetrack.py" read --question "Which functions touch the database?" --paths src/service.py src/handler.py
```

**`sidetrack write`** generates boilerplate from a spec and a reference file, then writes it straight to disk. Claude never sees the generated code.

```bash
python "$CLAUDE_PLUGIN_ROOT/scripts/sidetrack.py" write --spec "Tests for UserService" --reference tests/test_orders.py --context src/users.py --target tests/test_users.py
```

Claude knows how and when to use both through the bundled skills. You don't have to call them yourself.

## Settings

Set these in your shell or in the `env` block of `~/.claude/settings.json`.

| Variable | Default | What it does |
|---|---|---|
| `SIDETRACK_MIN_LINES` | `350` | Files longer than this get redirected |
| `SIDETRACK_BACKEND` | `claude` | `claude` uses Haiku through your subscription. `openai` uses an API key, see below |
| `SIDETRACK_MODEL` | `haiku` | Worker model for the `claude` backend, any value `claude --model` accepts |
| `SIDETRACK_DISABLE` | unset | Set to `1` to switch the hooks off |
| `SIDETRACK_CLAUDE_BIN` | auto | Path to `claude` if it isn't on your PATH |

## Using Luna with an OpenAI API key

Not the default. Pick this if you have an OpenAI key and want GPT-5.6 Luna as the worker instead of Haiku. Luna is cheaper per token and answers in a couple of seconds, because the call goes straight to the API instead of through the Claude Code CLI.

1. Put your key on one line in `~/.claude/sidetrack/openai_key`, or export `OPENAI_API_KEY`.
2. Add to `~/.claude/settings.json`:

```json
{ "env": { "SIDETRACK_BACKEND": "openai" } }
```

Optional overrides: `SIDETRACK_OPENAI_MODEL` (default `gpt-5.6-luna`), `SIDETRACK_OPENAI_EFFORT` (default `low`), `SIDETRACK_OPENAI_BASE_URL` for any OpenAI-compatible endpoint, `SIDETRACK_OPENAI_KEY_FILE` to read the key from elsewhere.

## What it doesn't do

- **Edits.** The worker's summaries don't carry reliable line numbers. Ask it where something lives, then grep and do a targeted read before editing.
- **Reasoning.** Debugging, architecture, and security-sensitive code stay with your main model. The skills say so.
- **Small files.** Below the threshold, delegation costs more time than it saves.

Each call is a round trip through the Claude Code CLI. Reads take around 10 seconds. Generating a whole file can take a minute or two.

## Development

```bash
python -m pytest tests
```

The first three tests were generated with `sidetrack write` from the script itself, then tidied by hand.

## Manual install

If you'd rather not use the plugin system, clone the repo and add this to `~/.claude/settings.json`, replacing the path:

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Read", "hooks": [{ "type": "command", "command": "python \"/path/to/sidetrack/scripts/sidetrack.py\" hook-read", "timeout": 10 }] },
      { "matcher": "Bash", "hooks": [{ "type": "command", "command": "python \"/path/to/sidetrack/scripts/sidetrack.py\" hook-bash", "timeout": 10 }] }
    ]
  }
}
```

Then copy the two folders under `skills/` into `~/.claude/skills/`.

## Credit

The idea and hook design come from Spotify's [shunt](https://github.com/spotify/portal-ai-plugins) plugin, which routes through Portal by Spotify. sidetrack does the same thing with nothing but Claude Code.

MIT licensed.
