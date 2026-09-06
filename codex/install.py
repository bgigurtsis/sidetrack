#!/usr/bin/env python3
"""Install Sidetrack's native Codex agents using only the Python standard library."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tomllib
from datetime import datetime, timezone
from uuid import uuid4

SOURCE = Path(__file__).resolve().parent
ASSETS = (
    "agents/sidetrack_luna_bulk_reader.toml",
    "agents/sidetrack_luna_code_writer.toml",
    "skills/sidetrack-luna/SKILL.md",
)
STATE = "sidetrack/install.json"
START = "<!-- sidetrack:codex:start -->"
END = "<!-- sidetrack:codex:end -->"
BLOCK = f"""{START}
## Sidetrack: Luna delegation

Use the `sidetrack-luna` skill to proactively delegate substantial file exploration
to `sidetrack_luna_bulk_reader` and predictable generation from reference files to
`sidetrack_luna_code_writer`. This is a standing request for bounded native Luna
subagents, regardless of the main model. Keep the selected main model for planning,
reasoning, integration, and review. Delegate before reading bulk source into the
main conversation, pass paths and a focused task, and use fresh worker contexts.
Prefer direct targeted reads for small tasks. Skip recursive delegation and skip
automatic routing when the main model is Luna. Current user instructions take
precedence. If Luna is unavailable, report that and proceed directly; never switch
to an API-key service or another worker model silently.
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
    if (state.get("version") != 1 or set(state.get("hashes", {})) != set(ASSETS)
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


def save(root, changes):
    """Back up every replaced file before the first write. Never delete backups."""
    backup = backup_path(root)
    for relative in changes:
        path = target(root, relative)
        if path.exists():
            dest = backup / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
    for relative, content in changes.items():
        path = target(root, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    if backup.exists():
        print(f"Backups: {backup}")


def install(root, dry_run=False):
    state = read_state(root)
    if state:
        check_owned(root, state)
    assets = {name: (SOURCE / name).read_bytes() for name in ASSETS}
    for name in ASSETS[:2]:
        agent = tomllib.loads(assets[name].decode("utf-8"))
        if agent.get("model") != "gpt-5.6-luna" or not agent.get("developer_instructions"):
            raise InstallError(f"Invalid Luna agent: {name}")
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
        if not state and dest.exists():
            raise InstallError(f"Refusing to overwrite an unowned file: {dest}")
    record = {"version": 1, "instructions": instructions, "separator": separator,
              "block": BLOCK, "hashes": {name: digest(content) for name, content in assets.items()}}
    proposed = {**assets, instructions: updated.encode("utf-8"),
                STATE: (json.dumps(record, indent=2) + "\n").encode("utf-8")}
    changes = {name: data for name, data in proposed.items()
               if not target(root, name).exists() or target(root, name).read_bytes() != data}
    if not changes:
        print("Sidetrack is already installed and up to date.")
        return
    for name in changes:
        print(f"{'Would write' if dry_run else 'Install'}: {root / name}")
    if not dry_run:
        save(root, changes)
        print("Installed. Start a new Codex task. Your main model, config, and sign-in are unchanged.")


def uninstall(root, dry_run=False):
    state = read_state(root)
    if not state:
        print("Sidetrack is not installed.")
        return
    check_owned(root, state)
    relative = state["instructions"]
    path = target(root, relative)
    text = route_text(path)
    check_markers(text, state["block"])
    # Remove only our block and the separator we appended; preserve later user text.
    chunk = state.get("separator", "") + state["block"]
    updated = text.replace(chunk if chunk in text else state["block"], "", 1)
    for name in (*ASSETS, STATE):
        print(f"{'Would archive' if dry_run else 'Archive'}: {root / name}")
    if dry_run:
        return
    backup = backup_path(root)
    dest = backup / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    path.write_bytes(updated.encode("utf-8"))
    for name in (*ASSETS, STATE):
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
    print(f"Installed: two Luna agents and sidetrack-luna skill under {root}")
    print(f"Routing: {state['instructions']} (advisory; no blocking hooks)")
    print("Account/model availability is not checked. Run codex login status and a live test.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "status", "uninstall"), nargs="?", default="install")
    parser.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex"))
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing")
    args = parser.parse_args(argv)
    try:
        globals()[args.action](args.codex_home.expanduser().resolve(), args.dry_run)
    except (InstallError, OSError, ValueError) as exc:
        print(f"Sidetrack: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
