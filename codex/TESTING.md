# Test results

The current Codex implementation uses CLI workers. See the
[CLI/subagent comparison](CLI-COMPARISON.md) for timings and measurement limits.

## Offline tests

```sh
python3 -m unittest discover -s codex/tests -v
```

The suite covers subscription-authentication checks, source paths and input limits,
stdin-only prompt transport, target overwrite protection, incomplete/failed replies,
timeouts, metrics, installation, migration from native agents and CLI-only installs,
hook deny/allow decisions, stdin protocol, preservation of unrelated hooks, backups,
and removal.
Tests do not call models. They retain temporary test directories for inspection.

On the local Windows host, 37 tests ran: 36 passed and the symlink test was skipped
because the host does not permit symlink creation. GitHub Actions runs the suite
on Windows, macOS, and Linux with Python 3.11 and 3.13; see the latest Actions result.

## Live tests

Verified ChatGPT sign-in with Codex CLI 0.153.4 on Windows. Two CLI reader trials
correctly identified both exceptions and their line references in a 601-line file.
Two CLI writer trials generated the requested code, with 16 independent checks
passing per output. Native-subagent trials provided the comparison baseline;
Sidetrack no longer installs that method.

A fresh Terra task with the trusted hook attempted `Get-Content -Raw` on the
601-line fixture. The hook denied it. The task then called the installed Luna CLI:
the reader identified both exceptions at lines 90 and 459 (6.563 seconds), and the
writer generated two functions (7.071 seconds) that passed six value checks.
Both CLI calls first failed to verify sign-in inside the sandbox, then succeeded
through normal scoped execution approval. No credentials were copied or controls
bypassed. CLI timings exclude the parent task and approval overhead.

The published repository was pulled into a separate clean checkout and used for
a real global install, repeat install, uninstall, and reinstall. Managed file
hashes matched; previous instructions and hooks were restored on removal;
config.toml was unchanged. A fresh Sol task after reinstall again received the
hook denial, successfully used both Luna CLI modes, and passed the value,
annotation, and docstring checks. All six GitHub Actions jobs passed for the
tested implementation (`0769913`).

These are correctness and workflow checks, not a guarantee of savings or account
eligibility. Follow [the smoke test](smoke-test.md) to verify your installation.
