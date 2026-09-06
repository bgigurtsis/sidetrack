---
name: sidetrack-luna
description: Delegate substantial file exploration and predictable code generation to Luna workers while retaining the selected main model for reasoning and review. Use before bulk reads or routine generation from reference files.
---

# Luna delegation

The user requests automatic delegation in both modes below regardless of the main model. Keep the selected main model unchanged. Skip automatic delegation if already a worker or if the main model is gpt-5.6-luna. Do not recursively delegate.

## Routing and context

- Use native subagents. Select the named custom agent when the tool supports it. Otherwise spawn with model `gpt-5.6-luna`, reasoning effort `medium`, and include the relevant mode instructions below in the task.
- Start with fresh context (`fork_turns="none"` when supported). Supply the question/specification, absolute workspace and file paths, relevant constraints, and permitted output paths. Have the worker read source files itself; do not copy the main conversation or bulk file contents into the task.
- Delegate only a concrete bounded task. While it runs, do useful independent planning or checks without duplicating its reads or editing its assigned files. If the available subagent tool requires independent concurrent work and none exists, handle the task directly.
- Prefer direct search and targeted reads when already sufficient. A full read exceeding roughly 350 lines, several substantial files, or predictable generation exceeding roughly 100 lines is a useful routing signal, not a hard cutoff.
- Keep debugging conclusions, architecture, security decisions, ambiguous implementation, and final review with the main model. Workers can gather evidence for these tasks.
- If Luna or subagents are unavailable, state the limitation briefly and continue directly. Do not add API credentials, external services, or substitute another worker model silently.

## Bulk-reader mode: sidetrack_luna_bulk_reader

Give a specific question and paths/search scope. Worker instructions: read-only; search and read source directly; return concise bullets with exact paths, symbols, verified line references, and just enough evidence to support the answer. Distinguish facts from inference and report uncertainty or missing coverage. Aim for at most 800 words unless explicitly necessary; never dump entire files. Do not edit files or spawn agents.

The main model reads relevant sections directly before edits or consequential conclusions. A summary is a navigation aid, not proof of completeness.

## Code-writer mode: sidetrack_luna_code_writer

Supply a concrete specification, at least one reference file, exact owned output paths, and relevant validation commands. Worker instructions: read references directly; match existing patterns; write code directly to assigned workspace paths; preserve unrelated work; do not edit outside the assignment, delete files, or spawn agents. If a missing requirement materially changes behavior, report it instead of inventing requirements. Run focused applicable checks and return changed paths, a brief behavior summary, check results, and unresolved issues. Do not paste generated files into the response.

The main model reviews the diff and validates behavior proportionate to the change. Do not let multiple workers write the same files concurrently. Delegation does not authorize deployment, messaging, or any external mutation beyond the user's task.
