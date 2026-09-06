---
name: sidetrack-write
description: Delegate generation of predictable boilerplate (tests that mirror existing tests, config stubs, type stubs, fixtures, repetitive adapters) to a cheap worker model (Claude Haiku by default), writing the result straight to disk so the generated code never enters your context. Use when the output is fully determined by a spec plus an existing reference file.
---

# sidetrack-write

The worker model (Haiku by default, or Luna via the openai backend) generates a file that matches a reference file's patterns. The code is written to disk directly.

## Invocation

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/sidetrack.py" write --spec "<what to generate>" --reference <pattern-file> [--context <dep-file> ...] --target <output-path>
```

- `--reference` is required: one or more existing files whose style, imports, naming and structure the output must copy.
- `--context` (optional): files the generated code depends on, such as the module under test. Sent for reference only.
- `--target`: output path. Refuses to overwrite an existing file unless `--force`. Omit to print to stdout.
- Markdown fences are stripped automatically.

## When to use

- Test files that follow the same shape as the tests next to them.
- Config, fixture, stub, or schema files derived mechanically from an existing one.
- Repetitive adapters or wrappers where a sibling already shows the exact pattern.

## When NOT to use

- Anything requiring judgment about design, edge cases, or correctness of non-trivial logic.
- Edits to existing files. sidetrack-write creates whole files only. Use Edit for changes.
- Safety-critical or security-sensitive code.

## After generating

Run the tests or a syntax check on the target rather than reading it back. Only read it if something fails, and then read the failing section with a targeted `Read`.
