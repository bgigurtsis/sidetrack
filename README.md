# Sidetrack

Delegate substantial file reading and predictable code generation to a smaller
model while keeping your chosen main model for reasoning and review.

## Codex + Luna

The [Codex version](codex/README.md) uses native GPT-5.6 Luna subagents through your
existing ChatGPT/Codex subscription sign-in. It includes both bulk-reader and
code-writer modes, global routing instructions, and a portable installer.

```sh
git clone https://github.com/bgigurtsis/sidetrack.git
cd sidetrack
python3 codex/install.py install
```

Windows: use `py -3` instead of `python3`. Requires Python 3.11+ and a current Codex
client with Luna access. Start a new Codex task after installation.

No Portal or API key required. Routing is instruction-based; subscription usage
and model availability still apply. See [setup and limitations](codex/README.md)
and [testing](codex/TESTING.md).

The Codex implementation is contained under `codex/` so other client/model
implementations can coexist without sharing configuration.
