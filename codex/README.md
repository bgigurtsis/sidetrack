# Sidetrack for Codex

Use **GPT-5.6 Luna** for file exploration and predictable code generation, while
keeping whichever main model you select for reasoning, integration, and review.
Both modes run as native Codex subagents using your existing Codex sign-in.
No Portal, Gemini, API key, proxy server, or separate model subscription is needed.

| Mode | Luna does | Main model receives |
| --- | --- | --- |
| Bulk-reader | Searches and reads large or multiple files to answer a focused question | Concise findings with paths, symbols, and verified line references |
| Code-writer | Reads a specification and reference files, then writes directly to assigned workspace paths | Changed paths, validation results, and a short summary |

## Requirements

- A current local Codex client supporting custom agents and skills. Tested with
  Codex CLI **0.153.4** on Windows; older versions may use different agent schemas.
- A ChatGPT/Codex subscription **with access to `gpt-5.6-luna`** and native
  subagents. Account and workspace model restrictions still apply.
- Sign in with ChatGPT in Codex. For the CLI, run `codex login` and complete the
  browser sign-in; `codex login status` reports the current authentication method.
- Python **3.11+**, used only for installation and offline tests. No packages needed.

The installer never reads credentials or changes authentication. If you already
use API-key authentication, switch to ChatGPT sign-in yourself before using this
subscription workflow. It does not convert an API session into subscription usage.

## Install globally

Clone the repository and run the installer from its root:

```sh
git clone https://github.com/bgigurtsis/sidetrack.git
cd sidetrack
python3 codex/install.py install --dry-run
python3 codex/install.py install
```

On Windows, use `py -3` (or `python`) instead of `python3`:

```powershell
py -3 codex/install.py install
```

Start a **new Codex task** after installation. The app, CLI, and IDE must use the
same Codex home to see the same installation. On another machine or remote host,
install there too.

The default destination is `$CODEX_HOME`, or `~/.codex` when unset. To choose it:

```sh
python3 codex/install.py install --codex-home /path/to/codex-home
python3 codex/install.py status
```

The installer adds these namespaced files:

```text
~/.codex/
  agents/sidetrack_luna_bulk_reader.toml
  agents/sidetrack_luna_code_writer.toml
  skills/sidetrack-luna/SKILL.md
  sidetrack/install.json
```

It appends one marked routing block to global `AGENTS.md`, or to an existing
nonempty `AGENTS.override.md`, which takes precedence in Codex. It preserves
existing instructions and backs up changed files under `sidetrack/backups/`.
It does not edit `config.toml`, change your main model, set all subagents to Luna,
or modify any Claude Code configuration. Unowned files at its target paths cause
installation to stop instead of being overwritten.

## Use it

Continue asking your main model to work normally. The global instructions request
delegation before substantial bulk reads or predictable generation. You can also
request either mode explicitly:

> Use Sidetrack's bulk-reader to find which services retry failed requests.
> Return paths and relevant methods before deciding what to change.

> Use Sidetrack's code-writer to generate tests for the three specified success
> cases in `tests/test_orders.py`, following `tests/test_users.py`. Review the result.

Or invoke `$sidetrack-luna` directly in Codex.

Workers receive a focused task and file paths, then read the files themselves in
fresh contexts. The main model should not read the whole corpus before delegating.
It can read relevant sections afterward to verify findings or review the diff.
The code-writer needs a reference file and explicit owned output paths.

Small reads stay local. Roughly 350 lines for a full read or 100 lines of routine
generation are routing signals, not enforced thresholds. Architecture, difficult
debugging, security decisions, and final review stay with the main model. Automatic
delegation is skipped when the main model is already Luna and within workers.

**Routing is advisory.** This version does not install blocking hooks. Codex may
handle a task directly when delegation has no benefit, when its available tools
require independent concurrent work and none exists, or when task instructions
override the routing. If Luna is unavailable, it reports the limitation and works
directly rather than silently using a different worker or an API service.

## Subscription usage and expected savings

Native workers use the existing Codex session's authentication and consume its
applicable usage allowance. They are not free extra capacity. Savings depend on
model accounting, task size, worker context, retries, and how much source the main
model must reread. This project makes **no 90% savings claim** and does not equate
API token prices with subscription limits. Summaries can omit important details;
review and appropriate validation remain necessary.

## Update or remove

After pulling a new version, rerun the installer. Identical installs are a no-op.
Unmodified files from a recorded installation can be updated with backups.
If you edited a managed worker or its routing block, preserve those changes and
restore the installed version before updating or removing it.

```sh
python3 codex/install.py uninstall --dry-run
python3 codex/install.py uninstall
```

Removal strips only Sidetrack's routing block and moves its active files into a
dated backup directory. Existing instructions and unrelated files remain. Empty
directories may remain. Start a new task afterward. Do not run concurrent installs
or edit managed files while the installer is running. If a filesystem error
interrupts an operation, inspect the reported error and backups before retrying.

## Verify

Offline installer tests make no model calls and use disposable test homes:

```sh
python3 -m unittest discover -s codex/tests -v
```

Tests retain their `sidetrack-test-*` temporary directories for inspection.
For a live check using your subscription allowance, see [the smoke test](smoke-test.md).
The installer checks files, not account eligibility or runtime tool availability.

## Official references

- [Codex authentication](https://learn.chatgpt.com/docs/auth): ChatGPT subscription sign-in versus API-key sign-in.
- [Custom agents and subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents): personal agent files, model overrides, permissions, and usage.
- [Global AGENTS.md instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md): discovery and override precedence.

This directory implements the Codex/Luna version. It can coexist with a separate
Claude Code/Haiku implementation elsewhere in this repository.
