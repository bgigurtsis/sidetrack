# Test results

The current Codex implementation uses CLI workers. See the
[CLI/subagent comparison](CLI-COMPARISON.md) for timings and measurement limits.

## Offline tests

```sh
python3 -m unittest discover -s codex/tests -v
```

The suite covers subscription-authentication checks, source paths and input limits,
stdin-only prompt transport, target overwrite protection, incomplete/failed replies,
timeouts, metrics, installation, migration from native agents, backups, and removal.
Tests do not call models. They retain temporary test directories for inspection.

On the local Windows host, 25 tests ran: 24 passed and the symlink test was skipped
because the host does not permit symlink creation. GitHub Actions runs the suite
on Windows, macOS, and Linux with Python 3.11 and 3.13; see the latest Actions result.

## Live tests

Verified ChatGPT sign-in with Codex CLI 0.153.4 on Windows. Two CLI reader trials
correctly identified both exceptions and their line references in a 601-line file.
Two CLI writer trials generated the requested code, with 16 independent checks
passing per output. Native-subagent trials provided the comparison baseline;
Sidetrack no longer installs that method.

These are correctness and workflow checks, not a guarantee of savings or account
eligibility. Follow [the smoke test](smoke-test.md) to verify your installation.
