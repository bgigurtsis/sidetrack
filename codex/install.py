#!/usr/bin/env python3
"""Install Sidetrack's subscription-backed Codex CLI worker and routing skill."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from datetime import datetime, timezone
from uuid import uuid4

SOURCE = Path(__file__).resolve().parent
sys.path.insert(0, str(SOURCE))
import hook_config

ASSETS = (
    "skills/sidetrack-luna/scripts/sidetrack.py",
    "skills/sidetrack-luna/SKILL.md",
    hook_config.HOOK_PATH,
)
SOURCES = {ASSETS[0]: "cli.py", ASSETS[1]: ASSETS[1], ASSETS[2]: "read_hook.py"}
LEGACY_ASSETS = (
    "agents/sidetrack_luna_bulk_reader.toml",
    "agents/sidetrack_luna_code_writer.toml",
    "skills/sidetrack-luna/SKILL.md",
)
STATE = "sidetrack/install.json"
START = "<!-- sidetrack:codex:start -->"
END = "<!-- sidetrack:codex:end -->"
BLOCK = f"""{START}
## Sidetrack: Luna delegation

Use the `sidetrack-luna` skill and its installed CLI script for substantial file
reading and predictable code generation. Invoke its `read` or `write` command
before loading bulk source into the main conversation. This is a standing request
for one-shot Luna CLI calls, not native subagents, regardless of the main model.
Keep the selected main model for reasoning, integration, and review. Prefer direct
targeted reads for small tasks. Skip recursive invocation and automatic routing
when the main model is Luna. Follow the current user's instructions. If Luna or
the CLI is unavailable, report that and proceed directly; never silently switch
to subagents, another worker model, or API-key authentication.
{END}"""


class InstallError(Exception):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def target(root, relative):
    """Keep all writes within the chosen home; refuse linked managed paths."""
    path = root / relative
    if not path.resolve().is_relative_to(root):
        raise InstallError(f"Path escapes Codex home: {path}")
    for part in (path, *path.parents):
        if part == root:
            break
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise InstallError(f"Linked installation path is unsupported: {part}")
    if path.exists() and not path.is_file():
        raise InstallError(f"Expected a file: {path}")
    return path


def read_state(root):
    path = target(root, STATE)
    if not path.exists():
        return None
    state = json.loads(path.read_text(encoding="utf-8"))
    expected = {1: set(LEGACY_ASSETS), 2: set(ASSETS[:2]), 3: set(ASSETS)}.get(state.get("version"))
    if (expected is None or set(state.get("hashes", {})) != expected
            or state.get("instructions") not in ("AGENTS.md", "AGENTS.override.md")
            or not isinstance(state.get("block"), str)
            or not state["block"].startswith(START)
            or not state["block"].endswith(END)):
        raise InstallError("Unrecognized Sidetrack installation record; no files changed.")
    return state


def check_owned(root, state):
    for name, expected in state["hashes"].items():
        path = target(root, name)
        if not path.exists() or digest(path.read_bytes()) != expected:
            raise InstallError(f"Installed file changed or missing: {path}. Preserve your changes before reinstalling/removing.")


def route_text(path):
    return path.read_bytes().decode("utf-8") if path.exists() else ""


def check_markers(text, expected=None):
    if expected is None:
        if START in text or END in text:
            raise InstallError("Found Sidetrack routing without an installation record.")
    elif text.count(START) != 1 or text.count(END) != 1 or text.count(expected) != 1:
        raise InstallError("Sidetrack routing was modified; preserve your changes before proceeding.")


def backup_path(root):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    relative = f"sidetrack/backups/{stamp}-{uuid4().hex[:8]}"
    target(root, relative + "/check")
    return root / relative


def save(root, changes, retired=()):
    """Back up every replaced file before the first write. Never delete backups."""
    backup = backup_path(root)
    for relative in changes:
        path = target(root, relative)
        if path.exists():
            dest = backup / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
    for relative, content in changes.items():
        if relative == STATE:
            continue
        path = target(root, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    for relative in retired:
        dest = backup / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(target(root, relative)), str(dest))
    if STATE in changes:
        path = target(root, STATE)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(changes[STATE])
    if backup.exists():
        print(f"Backups: {backup}")


def install(root, dry_run=False):
    state = read_state(root)
    if state:
        check_owned(root, state)
    assets = {name: (SOURCE / SOURCES[name]).read_bytes() for name in ASSETS}
    compile(assets[ASSETS[0]], ASSETS[0], "exec")
    compile(assets[ASSETS[2]], ASSETS[2], "exec")
    hook_path = target(root, "hooks.json")
    hooks_before = (state["hooks_before"] if state and "hooks_before" in state else
                    hook_path.read_bytes().decode("utf-8") if hook_path.exists() else None)
    hook_data, hook_entry = hook_config.prepare(root, state, assets[ASSETS[2]])
    override = target(root, "AGENTS.override.md")
    instructions = (state["instructions"] if state else
                    "AGENTS.override.md" if override.exists() and override.stat().st_size else "AGENTS.md")
    if state and instructions == "AGENTS.md" and override.exists() and override.stat().st_size:
        raise InstallError("AGENTS.override.md now shadows the installed routing. Uninstall first, then reinstall.")
    path = target(root, instructions)
    text = route_text(path)
    check_markers(text, state["block"] if state else None)
    if state:
        updated = text.replace(state["block"], BLOCK, 1)
        separator = state.get("separator", "")
    else:
        separator = "" if not text or text.endswith("\n\n") else "\n" if text.endswith("\n") else "\n\n"
        updated = text + separator + BLOCK
    for name, content in assets.items():
        dest = target(root, name)
        if dest.exists() and (not state or name not in state["hashes"]):
            raise InstallError(f"Refusing to overwrite an unowned file: {dest}")
    retired = tuple(name for name in state["hashes"] if name not in ASSETS) if state else ()
    record = {"version": 3, "instructions": instructions, "separator": separator,
              "hook_entry": hook_entry, "hooks_before": hooks_before,
              "block": BLOCK, "hashes": {name: digest(content) for name, content in assets.items()}}
    proposed = {**assets, instructions: updated.encode("utf-8"), "hooks.json": hook_data,
                STATE: (json.dumps(record, indent=2) + "\n").encode("utf-8")}
    changes = {name: data for name, data in proposed.items()
               if not target(root, name).exists() or target(root, name).read_bytes() != data}
    if not changes:
        print("Sidetrack is already installed and up to date.")
        return
    for name in changes:
        print(f"{'Would write' if dry_run else 'Install'}: {root / name}")
    for name in retired:
        print(f"{'Would archive' if dry_run else 'Archive legacy agent'}: {root / name}")
    if not dry_run:
        save(root, changes, retired)
        print("Installed. Open Codex /hooks and review/trust the Sidetrack hook, then start a new task.")
        print("The read guard is inactive until trusted. Main model, config, and sign-in are unchanged.")


def uninstall(root, dry_run=False):
    state = read_state(root)
    if not state:
        print("Sidetrack is not installed.")
        return
    check_owned(root, state)
    hook_data = None
    if state.get("hook_entry"):
        target(root, "hooks.json")
        hook_data, _ = hook_config.prepare(root, state)
    relative = state["instructions"]
    path = target(root, relative)
    text = route_text(path)
    check_markers(text, state["block"])
    # Remove only our block and the separator we appended; preserve later user text.
    chunk = state.get("separator", "") + state["block"]
    updated = text.replace(chunk if chunk in text else state["block"], "", 1)
    for name in (*state["hashes"], STATE):
        print(f"{'Would archive' if dry_run else 'Archive'}: {root / name}")
    if dry_run:
        return
    backup = backup_path(root)
    if hook_data is not None:
        hook_backup = backup / "hooks.json"
        hook_backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / "hooks.json", hook_backup)
        (root / "hooks.json").write_bytes(hook_data)
    dest = backup / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    path.write_bytes(updated.encode("utf-8"))
    for name in (*state["hashes"], STATE):
        archived = backup / name
        archived.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(target(root, name)), str(archived))
    print(f"Removed active Sidetrack files. Recoverable copies: {backup}")


def status(root, dry_run=False):
    state = read_state(root)
    if not state:
        print("Sidetrack is not installed.")
        return
    check_owned(root, state)
    check_markers(route_text(target(root, state["instructions"])), state["block"])
    override = target(root, "AGENTS.override.md")
    if state["instructions"] == "AGENTS.md" and override.exists() and override.stat().st_size:
        raise InstallError("Routing is shadowed by AGENTS.override.md; uninstall and reinstall.")
    if state.get("hook_entry"):
        target(root, "hooks.json")
        hook_config.prepare(root, state)
    method = "Luna CLI worker" if state["version"] >= 2 else "legacy native agents; run install to migrate"
    print(f"Installed: {method} and sidetrack-luna skill under {root}")
    print(f"Routing guidance: {state['instructions']}")
    print("Read guard: installed; verify enabled/trusted in /hooks." if state.get("hook_entry")
          else "Read guard: absent; run install to upgrade.")
    print("Account/model availability is not checked. Run codex login status and a live test.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "status", "uninstall"), nargs="?", default="install")
    parser.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex"))
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing")
    args = parser.parse_args(argv)
    try:
        globals()[args.action](args.codex_home.expanduser().resolve(), args.dry_run)
    except (InstallError, OSError, ValueError, SyntaxError) as exc:
        print(f"Sidetrack: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
