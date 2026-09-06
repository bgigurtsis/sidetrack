#!/usr/bin/env python3
"""sidetrack: send bulk file reading and boilerplate generation to Claude Haiku instead of your main model.

Works with a Claude Code subscription alone: the worker is invoked through `claude -p --model haiku`, so no API key
is needed and usage is billed to your existing plan.

Subcommands
  hook-read    PreToolUse hook for Read.  Blocks whole-file reads of large files (stdin: hook JSON).
  hook-bash    PreToolUse hook for Bash.  Blocks cat/less/more (and untargeted head/tail) on large files.
  read         --question Q --paths P [P ...]           Ask Haiku about files; prints bullets.
  write        --spec S --reference R [R ...] [--target T] [--context C ...] [--force]
               Generate a file matching the reference's patterns; writes to T or stdout.

Environment (all optional)
  SIDETRACK_MIN_LINES   line threshold above which reads are redirected (default 350)
  SIDETRACK_MODEL       worker model passed to `claude --model` (default haiku)
  SIDETRACK_CLAUDE_BIN  path to the claude executable (default: CLAUDE_CODE_EXECPATH, then `claude` on PATH)
  SIDETRACK_DISABLE=1   hooks allow everything (escape hatch)
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MIN_LINES = int(os.environ.get("SIDETRACK_MIN_LINES", "350"))
MODEL = os.environ.get("SIDETRACK_MODEL", "haiku")
SCRIPT = str(HERE / "sidetrack.py").replace("\\", "/")
INVOKE = f'python "{SCRIPT}"'

TEXT_SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".pdf", ".ipynb",
                 ".zip", ".gz", ".tar", ".7z", ".exe", ".dll", ".so", ".dylib", ".woff", ".woff2", ".ttf"}

READER_SYSTEM = (
    "You are a precise code analyst. Read the provided files and answer the question concisely. "
    "Output structured bullets only. No greetings, no prose, no preambles. Lead every bullet with the exact "
    "name, type, or line number. Use nested bullets for details. Skip anything the caller did not ask for. "
    "If the answer requires an exact location, quote the surrounding line verbatim so it can be searched for."
)
WRITER_SYSTEM = (
    "You generate code files based on a spec and reference files. Match the existing patterns, conventions, "
    "naming, and style exactly. Output only the code: no explanations, no markdown fences. If the spec is "
    "ambiguous, make reasonable choices that match the reference code's patterns."
)


# ----------------------------------------------------------------------------- helpers
def count_lines(path: str) -> int:
    try:
        with open(path, "rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def is_text_candidate(path: str) -> bool:
    p = Path(path)
    return p.is_file() and p.suffix.lower() not in TEXT_SKIP_EXT


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def expand_paths(paths: list[str]) -> list[str]:
    out: list[str] = []
    for p in paths:
        hits = glob.glob(p, recursive=True) if any(c in p for c in "*?[") else [p]
        for h in hits:
            if Path(h).is_file() and h not in out:
                out.append(h)
            elif not Path(h).exists():
                sys.stderr.write(f"sidetrack: no such file: {h}\n")
    return out


def claude_bin() -> list[str]:
    cand = os.environ.get("SIDETRACK_CLAUDE_BIN") or os.environ.get("CLAUDE_CODE_EXECPATH") or shutil.which("claude")
    if not cand:
        sys.exit("sidetrack: cannot find the `claude` executable. Set SIDETRACK_CLAUDE_BIN.")
    if os.name == "nt" and cand.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", cand]
    return [cand]


def ask_worker(system: str, user: str) -> str:
    """Run one non-interactive Haiku turn through the Claude Code CLI. No tools, nothing persisted."""
    # --setting-sources "" and --strict-mcp-config matter: without them the nested CLI loads the user's skills,
    # plugins, MCP tool descriptions and CLAUDE.md, which can be >100k tokens per call and would erase the savings.
    cmd = claude_bin() + [
        "-p", "--model", MODEL, "--tools", "", "--max-turns", "1",
        "--setting-sources", "", "--strict-mcp-config",
        "--no-session-persistence", "--output-format", "json",
        "--system-prompt", system,
    ]
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE",)}  # allow nesting inside a session
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, input=user, capture_output=True, text=True, encoding="utf-8",
                              timeout=300, env=env)
    except subprocess.TimeoutExpired:
        sys.exit("sidetrack: worker timed out after 300s. Send fewer files or a narrower question.")
    if proc.returncode != 0 and not proc.stdout.strip():
        sys.exit(f"sidetrack: claude exited {proc.returncode}: {proc.stderr.strip()[:500]}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        sys.exit(f"sidetrack: unexpected output from claude: {proc.stdout[:500]}")
    if data.get("is_error"):
        sys.exit(f"sidetrack: worker error: {data.get('result', '')[:500]}")
    usage = data.get("usage", {})
    sys.stderr.write(
        f"sidetrack: model={MODEL} in={usage.get('input_tokens', '?')} "
        f"cache_write={usage.get('cache_creation_input_tokens', 0)} cache_read={usage.get('cache_read_input_tokens', 0)} "
        f"out={usage.get('output_tokens', '?')} "
        f"cost=${data.get('total_cost_usd', 0):.4f} ({time.time() - t0:.1f}s)\n"
    )
    return data.get("result") or ""


def wrap_files(paths: list[str]) -> str:
    parts = []
    for p in paths:
        parts.append(f'<file path="{p}" lines="{count_lines(p)}">\n{read_text(p)}\n</file>')
    return "\n\n".join(parts)


def strip_fences(text: str) -> str:
    t = text.strip()
    m = re.match(r"^```[a-zA-Z0-9_+-]*\n(.*?)\n```\s*$", t, re.S)
    return (m.group(1) if m else t) + "\n"


def block(msg: str) -> None:
    sys.stderr.write(msg)
    sys.exit(2)


# ----------------------------------------------------------------------------- hooks
def hook_read() -> None:
    if os.environ.get("SIDETRACK_DISABLE"):
        return
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    ti = payload.get("tool_input", {}) or {}
    path = ti.get("file_path") or ""
    if not path or ti.get("offset") is not None or ti.get("limit") is not None:
        return  # targeted read: allowed
    if not is_text_candidate(path):
        return
    n = count_lines(path)
    if n <= MIN_LINES:
        return
    block(
        f"sidetrack: {path} is {n} lines (> {MIN_LINES}). Do not read it whole. Either:\n"
        f"  1. Delegate understanding to the cheap worker (preferred):\n"
        f'     {INVOKE} read --question "<what you need to know>" --paths "{path}"\n'
        f"  2. Or read only the section you need: Read with offset/limit (targeted reads are always allowed).\n"
        f"See the sidetrack-read skill. Set SIDETRACK_MIN_LINES to change the threshold."
    )


BASH_READERS = {"cat", "less", "more", "head", "tail", "type"}


def hook_bash() -> None:
    if os.environ.get("SIDETRACK_DISABLE"):
        return
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    cmd = (payload.get("tool_input", {}) or {}).get("command") or ""
    if not cmd or "|" in cmd or ">" in cmd:
        return  # piped / redirected: treated as targeted
    for segment in re.split(r"\s*(?:&&|\|\||;)\s*", cmd):
        try:
            toks = shlex.split(segment, posix=True)
        except ValueError:
            continue
        if not toks:
            continue
        prog = Path(toks[0]).name
        if prog not in BASH_READERS:
            continue
        args = toks[1:]
        if prog in ("head", "tail") and any(a.startswith("-") for a in args):
            continue  # head -n 40 style: targeted
        for a in args:
            if a.startswith("-"):
                continue
            if is_text_candidate(a):
                n = count_lines(a)
                if n > MIN_LINES:
                    block(
                        f"sidetrack: `{prog} {a}` would dump {n} lines (> {MIN_LINES}) into context. Instead:\n"
                        f'  {INVOKE} read --question "<what you need to know>" --paths "{a}"\n'
                        f"or use a targeted read (grep, sed -n, head -n, or Read with offset/limit)."
                    )


# ----------------------------------------------------------------------------- commands
def cmd_read(a: argparse.Namespace) -> None:
    paths = expand_paths(a.paths)
    if not paths:
        sys.exit("sidetrack: no readable files given")
    user = f"<question>\n{a.question}\n</question>\n\n{wrap_files(paths)}"
    print(ask_worker(READER_SYSTEM, user))


def cmd_write(a: argparse.Namespace) -> None:
    refs = expand_paths(a.reference)
    if not refs:
        sys.exit("sidetrack: at least one existing --reference file is required")
    ctx = expand_paths(a.context) if a.context else []
    if a.target and Path(a.target).exists() and not a.force:
        sys.exit(f"sidetrack: {a.target} exists; pass --force to overwrite")
    user = (
        f"<spec>\n{a.spec}\n</spec>\n\n"
        f"<reference_files note=\"match these patterns exactly\">\n{wrap_files(refs)}\n</reference_files>\n"
        + (f"\n<context_files note=\"for reference only\">\n{wrap_files(ctx)}\n</context_files>\n" if ctx else "")
        + (f"\nOutput the complete contents of the file {a.target}." if a.target else "\nOutput the complete file.")
    )
    code = strip_fences(ask_worker(WRITER_SYSTEM, user))
    if a.target:
        Path(a.target).parent.mkdir(parents=True, exist_ok=True)
        Path(a.target).write_text(code, encoding="utf-8", newline="\n")
        print(f"sidetrack: wrote {a.target} ({code.count(chr(10))} lines)")
    else:
        sys.stdout.write(code)


def main() -> None:
    ap = argparse.ArgumentParser(prog="sidetrack", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("hook-read")
    sub.add_parser("hook-bash")
    rd = sub.add_parser("read")
    rd.add_argument("--question", required=True)
    rd.add_argument("--paths", nargs="+", required=True, help="files or globs")
    wr = sub.add_parser("write")
    wr.add_argument("--spec", required=True)
    wr.add_argument("--reference", nargs="+", required=True, help="file(s) whose patterns to match")
    wr.add_argument("--context", nargs="*", help="extra files the generated code depends on")
    wr.add_argument("--target", help="write here instead of stdout")
    wr.add_argument("--force", action="store_true")
    a = ap.parse_args()
    {"hook-read": lambda _: hook_read(), "hook-bash": lambda _: hook_bash(),
     "read": cmd_read, "write": cmd_write}[a.cmd](a)


if __name__ == "__main__":
    main()
