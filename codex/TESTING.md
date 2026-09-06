# Validation record

Validated on 6 September 2026 using Windows, Python 3.14, and Codex CLI 0.153.4.

## Offline tests

`python -m unittest discover -s codex/tests -v` ran 14 installer tests:
13 passed; one filesystem symlink test was skipped because creating symlinks was
not permitted on the local test host. The suite covers dry runs, existing config
and auth preservation, idempotent installs, updates with backups, conflicting or
modified files, instruction override precedence, path containment, and removal.

The GitHub Actions workflow runs this suite on Windows, Linux, and macOS with
Python 3.11 and 3.13. Refer to Actions for current CI results; this local record
does not assert results for operating systems that were not tested locally.

## Live subscription test

- `codex login status` reported **Logged in using ChatGPT**.
- Installed the packaged agents and skill with `codex/install.py`.
- Started a fresh, ephemeral Codex session with **GPT-5.6 Terra** as main model.
- The session reported using both named packaged agents:
  `sidetrack_luna_bulk_reader` and `sidetrack_luna_code_writer`, each configured
  explicitly with `model = "gpt-5.6-luna"` and medium reasoning effort.
- The reader inspected a 601-line synthetic service configuration and correctly
  identified the disabled service and the sole nondefault retry limit, with
  matching source locations. Its answer was checked against the fixture.
- The writer generated two typed arithmetic functions directly in a scratch
  workspace, matching a reference file. Independent checks passed for eight
  positive, negative, zero, and large integer inputs per function: **16 checks**.
- Ran the packaged uninstaller; its added routing was removed and the original
  global instruction file was restored byte-for-byte. Removed managed files were
  retained in recoverable backups.

Codex rewrote its config during the live session, so the whole-session config
checksum was not unchanged. The main-model setting remained unchanged; the
installer's config/auth preservation is covered independently by the offline
tests. The installer never writes either file.

This validates installation and both requested worker modes. It is not a token
savings benchmark, a guarantee of automatic delegation on every task, or proof
that Luna is available to every subscription tier or managed workspace.

See [smoke-test.md](smoke-test.md) to reproduce a small live test with your own
account.
