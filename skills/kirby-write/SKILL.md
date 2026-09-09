---
name: kirby-write
description: Delegate only basic boilerplate file generation to Haiku or Luna from an exact reference and explicit substitutions. Keep logic, design, debugging, and ambiguous work with the main model.
---

# kirby-write

The main model may delegate only basic mechanical boilerplate to Haiku or Luna.
The worker must copy an existing pattern with explicit substitutions.
The main model must keep all implementation decisions.

## Invocation

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/kirby.py" write --spec "<what to generate>" --reference <pattern-file> [--context <dep-file> ...] --target <output-path>
```

- `--reference` is required: one or more existing files whose style, imports, naming and structure the output must copy.
- `--context` (optional): files the generated code depends on, such as the module under test. Sent for reference only.
- `--target`: output path. Refuses to overwrite an existing file unless `--force`. Omit to print to stdout.
- Markdown fences are stripped automatically.

## Before delegating

1. The main model must identify an exact reference, target, and complete list of substitutions or literal values.
2. The main model must confirm that the worker needs no new logic, inferred behavior, or implementation choices.
3. The main model must handle the write directly if any requirement remains unclear.

Output size, low temperature, and a detailed spec must not qualify a task by themselves.
The main model must not split complex implementation into small worker assignments to bypass this limit.

## Allowed work

- The worker may copy a static fixture with supplied literal values.
- The worker may duplicate declarations or config entries with explicitly supplied names and values.
- The worker may copy an existing trivial function or test with exact substitutions and unchanged behavior or assertions.

## Work the main model must keep

- The main model must implement new logic, algorithms, validation, error handling, and edge cases.
- The main model must handle refactors, debugging, integrations, and changes that depend on behavior across files.
- The main model must choose test cases and expected results.
- The main model must handle security-sensitive code and config that changes access, deployment, or data handling.
- The main model must edit existing files directly because kirby-write creates whole files.

## Worker specification

The parent must require the worker to match the reference's patterns, conventions, naming, and style exactly.
The parent must supply every substitution and literal value.
The parent must forbid reasonable guesses when the spec is ambiguous.
The parent must resolve ambiguity before invoking this file-output CLI.
For eligible work, the worker must output only code without explanations or Markdown fences.

## After generating

The main model must review the generated diff against the reference and requested substitutions.
The main model must run relevant syntax checks or tests before accepting the result.
Passing checks must not replace review of the generated code.
