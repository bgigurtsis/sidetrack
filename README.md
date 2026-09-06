# sidetrack

sidetrack sends substantial file reads and predictable code generation to a smaller model, keeping your chosen main model for reasoning and review. It supports Claude Code with Haiku and Codex with Luna.

Use your existing subscription sign-in. No Portal, API key, or extra model service is required. Model access and subscription usage limits still apply.

## Codex + Luna

For Codex subscribers, the [Codex version](codex/README.md) provides both modes
using native GPT-5.6 Luna subagents and your existing ChatGPT/Codex sign-in. Your
selected main model stays in charge. No Portal or API key is needed.

```sh
git clone https://github.com/bgigurtsis/sidetrack.git
cd sidetrack
python3 codex/install.py install
```

Windows: use `py -3` instead of `python3`. Requires Python 3.11+, a current Codex
client, and Luna access. Start a new task after installation. Codex routing is
instruction-based; the Claude Code hooks described below apply to Claude only.
See [Codex setup and removal](codex/README.md), [validation](codex/TESTING.md), and
[the live smoke test](codex/smoke-test.md). Subscription limits still apply.

## Claude Code + Haiku

The Claude Code plugin calls Haiku through `claude -p`, using the plan you are signed in with.

### Setup

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
