# Optional CLI workers

Kirby's default workflow uses native Luna subagents. The installed CLI is an
optional tool that calls `codex exec` with Luna through your existing ChatGPT
sign-in. Use it only after an explicit request for CLI execution and authorization
for Luna to process the selected task-relevant source through that CLI. Do not
use it as an automatic fallback when native delegation is unavailable or blocked.

The optional CLI requires a current Codex CLI and ChatGPT sign-in. It runs as a
shell tool call and does not spawn a native subagent. Normal sandbox restrictions
and automatic approval review still apply. A direct-command allow rule is not
authorization to bypass a transfer rejection; see [setup](setup.md).

```sh
python3 codex/cli.py --workspace /path/to/project read --question "Which services retry?" --paths src/services.py
python3 codex/cli.py --workspace /path/to/project write --spec "Generate the specified tests" --reference tests/test_users.py --context src/orders.py --target tests/test_orders.py
```

On Windows use `py -3` instead of `python3`. The wrapper locates the desktop app's
native `codex.exe`; use `--codex-bin /path/to/codex` if needed. Windows batch
launchers are intentionally unsupported so source text never passes through a shell.

1. The script reads the specified UTF-8 files and sends numbered source lines to
   Luna through stdin. The parent model never receives the source contents.
2. Luna runs in a fresh, ephemeral, read-only Codex session with native subagents
   disabled. It is instructed to answer entirely from the supplied data.
3. The script returns the final answer. In write mode it saves the returned code
   to a new file and returns only the path and size. Review and test generated code.

The target must not exist, its parent directory must exist, and all source and
output paths must stay inside the selected workspace. Input is capped at 500 KB.
There is no overwrite mode. A failed, incomplete, or timed-out model response does
not get written as code. The default timeout is 180 seconds; use `--timeout` before
the `read` or `write` subcommand to change it.

Usage and elapsed seconds are printed to stderr. Add `--report metrics.json`
before the subcommand to save them in a new workspace file. Usage fields are the
values reported by Codex, not subscription credits or a monetary cost estimate.

The script verifies ChatGPT sign-in with `codex login status` and restricts the
run to that authentication method. It does not read credentials, fall back to an
API key, or change your saved main model. It retains normal Codex configuration,
instructions, hooks, and extensions; startup overhead can vary between users.
The read-only sandbox constrains local writes; inherited integrations still have
their normal permission controls. The worker is instructed not to call tools.

Use this for focused one-shot requests where all relevant files are known.
If more context is needed, locate additional files and make another CLI call.
