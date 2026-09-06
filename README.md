# sidetrack

Stop paying frontier-model prices for grunt work. sidetrack is a Claude Code plugin that sends big file reads and boilerplate generation to Claude Haiku, so your main model only sees the answer.

Works with a Claude Code subscription alone. No API key, no extra service. Haiku is called through `claude -p`, so it bills against the plan you already have.

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

**`sidetrack read`** sends files plus a question to Haiku and returns a short bulleted answer. Ask again with the same files for follow-ups. The files never enter your main context.

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
| `SIDETRACK_MODEL` | `haiku` | Worker model, any value `claude --model` accepts |
| `SIDETRACK_DISABLE` | unset | Set to `1` to switch the hooks off |
| `SIDETRACK_CLAUDE_BIN` | auto | Path to `claude` if it isn't on your PATH |

## What it doesn't do

- **Edits.** Haiku's summaries don't carry reliable line numbers. Ask it where something lives, then grep and do a targeted read before editing.
- **Reasoning.** Debugging, architecture, and security-sensitive code stay with your main model. The skills say so.
- **Small files.** Below the threshold, delegation costs more time than it saves.

Each call is a round trip through the Claude Code CLI. Reads take around 10 seconds. Generating a whole file can take a minute or two.

## Development

```bash
python -m pytest tests
```

The test file was itself generated with `sidetrack write` and then adopted with one path fix.

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
