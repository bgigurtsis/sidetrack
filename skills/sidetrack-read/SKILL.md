---
name: sidetrack-read
description: Delegate reading of large files (or many files) to a cheap worker model (Claude Haiku by default) and receive a short bulleted answer instead of loading the files into context. Use when a Read is blocked by the sidetrack hook, when a question spans several files, or when you need to understand what a large file does before deciding which section to read.
---

# sidetrack-read

Send files plus a question to the worker model (Haiku by default, or Luna via the openai backend). Only the answer enters your context. The files never do.

## Invocation

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/sidetrack.py" read --question "<question>" --paths <file> [<file> ...]
```

Globs are accepted in `--paths` (for example `src/**/*.py`). Token usage and cost are printed to stderr.

## When to use

- The sidetrack hook blocked a whole-file Read of a large file.
- The question is about *what* code does: structure, call graph, which functions touch X, how a module is organised.
- The same question spans several files. Send them all in one call.
- Follow-up questions: call again with the same paths. Re-sending is cheap because the files never enter your context.

## When NOT to use

- You need exact line numbers to edit. Ask *where* something lives (the worker quotes the surrounding line), then `Grep` for that line and do a targeted `Read` with `offset`/`limit`.
- Debugging subtle bugs, concurrency, security-sensitive logic, or architectural decisions. Read those yourself.
- Files under the threshold (default 350 lines). Just read them.

## Good questions

Be specific and ask for structure:

- "List every public function with a one-line purpose and its parameters."
- "Which functions perform network I/O, and what do they call?"
- "Where is retry/backoff implemented? Quote the def line."
- "Summarise the data model: classes, fields, relationships."

## Escape hatch

`SIDETRACK_DISABLE=1` in the environment makes the hooks allow everything. `SIDETRACK_MIN_LINES` changes the threshold.
