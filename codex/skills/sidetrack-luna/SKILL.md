---
name: sidetrack-luna
description: Use Luna through the Codex CLI for substantial file reading and predictable code generation. Use before bulk reads or routine generation from reference files, while retaining the selected main model for reasoning and review.
---

# Sidetrack Luna CLI

Use the installed script at `scripts/sidetrack.py` relative to this skill directory.
Choose an available Python 3.11+ interpreter (`python3`, `python`, or `py -3`).
Use its absolute script path and pass the project root with `--workspace`.
This is a normal shell tool call, not a native-subagent workflow.

## Read

```sh
python3 /path/to/skill/scripts/sidetrack.py --workspace /path/to/project read --question "Which services retry failed requests?" --paths src/services.py src/config.py
```

Pass a focused question and relevant file paths before reading bulk source into
the main conversation. The script reads and numbers the source itself, sends it
to Luna, and returns only the final answer. Use direct searches to locate files
first when needed. Read specific sections afterward before edits or important
conclusions; summaries may omit details or contain incorrect line references.

## Write

```sh
python3 /path/to/skill/scripts/sidetrack.py --workspace /path/to/project write --spec "Generate tests for these specified success cases" --reference tests/test_users.py --context src/orders.py --target tests/test_orders.py
```

Provide a concrete specification, a reference file, and a new target path. Its
parent directory must exist. Luna returns code to the script, which writes it and
returns a short summary. Review the result and run appropriate checks. For an
existing file, generate to a new staging file and review/apply the intended edits;
do not overwrite user work or treat generated output as already verified.

## Routing

- Keep the selected main model unchanged. Use CLI calls for substantial reads or
  predictable generation. A trusted PreToolUse hook blocks supported whole-file
  reads over 350 lines. If denied, use this CLI with a focused question; do not
  evade the guard with another reader. Small tasks and targeted excerpts stay local.
- Keep architecture, difficult debugging, security decisions, and final review
  with the main model. Do not call native subagents for either Sidetrack mode.
- Skip recursive invocation and automatic routing when already using Luna. No
  independent parallel task is required for a CLI call.
- Inputs and outputs must stay in the workspace. Split inputs exceeding 500 KB.
  The CLI requires ChatGPT sign-in and Luna availability. If unavailable, report
  the limitation and work directly; do not switch worker models or authentication.
- Preserve normal sandbox and approval controls. If a CLI subprocess is blocked,
  request the normal narrowly scoped execution approval rather than bypassing
  permissions or switching to an API. If sign-in cannot be verified inside the
  sandbox, retry the exact script command through that approval flow before
  declaring Luna unavailable; do not ask the user to log in again based only on
  a sandbox failure. Never copy credentials into the workspace. No deployment or messaging is authorized
  by delegation alone.
- Stdout is the result; stderr contains elapsed time and Codex-reported usage.
  Use `--timeout 180` or `--report metrics.json` before the mode if needed. Reports
  require a new path. Never equate token counts with subscription credits.
