#!/usr/bin/env python3
"""kirby: send bulk file reading and boilerplate generation to a cheap worker model instead of your main model.

Default backend ("claude"): Claude Haiku through `claude -p --model haiku`. Works with a Claude Code subscription
alone; no API key, usage billed to your existing plan.
Optional backend ("openai"): any OpenAI-compatible chat-completions endpoint with an API key, e.g. GPT-5.6 Luna.

Subcommands
  hook-read    PreToolUse hook for Read.  Blocks whole-file reads of large files (stdin: hook JSON).
  hook-bash    PreToolUse hook for Bash.  Blocks cat/less/more (and untargeted head/tail) on large files.
  read         --question Q --paths P [P ...]           Ask the worker about files; prints bullets.
  write        --spec S --reference R [R ...] [--target T] [--context C ...] [--force]
               Generate a file matching the reference's patterns; writes to T or stdout.

Environment (all optional)
  KIRBY_MIN_LINES        line threshold above which reads are redirected (default 350)
  KIRBY_BACKEND          "claude" (default) or "openai"
  KIRBY_DISABLE=1        hooks allow everything (escape hatch)
  -- claude backend --
  KIRBY_MODEL            worker model passed to `claude --model` (default haiku)
  KIRBY_CLAUDE_BIN       path to the claude executable (default: CLAUDE_CODE_EXECPATH, then `claude` on PATH)
  -- openai backend --
  KIRBY_OPENAI_MODEL     model name (default gpt-5.6-luna)
  KIRBY_OPENAI_EFFORT    reasoning_effort (default low)
  KIRBY_OPENAI_BASE_URL  endpoint (default https://api.openai.com/v1)
  OPENAI_API_KEY             API key; else read from KIRBY_OPENAI_KEY_FILE or ~/.claude/kirby/openai_key
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
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MIN_LINES = int(os.environ.get("KIRBY_MIN_LINES", "350"))
BACKEND = os.environ.get("KIRBY_BACKEND", "claude").lower()
MODEL = os.environ.get("KIRBY_MODEL", "haiku")
OPENAI_MODEL = os.environ.get("KIRBY_OPENAI_MODEL", "gpt-5.6-luna")
OPENAI_EFFORT = os.environ.get("KIRBY_OPENAI_EFFORT", "low")
OPENAI_BASE_URL = os.environ.get("KIRBY_OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_KEY_FILE = Path(os.environ.get("KIRBY_OPENAI_KEY_FILE") or Path.home() / ".claude" / "kirby" / "openai_key")
SCRIPT = str(HERE / "kirby.py").replace("\\", "/")
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
    "You may generate only basic mechanical boilerplate from an exact reference and explicit substitutions. "
    "You must match the reference's conventions, naming, and style exactly. "
    "You must not invent logic, infer behavior, choose test cases, or make implementation choices. "
    "You must return KIRBY_NEEDS_MAIN_MODEL if the task is ambiguous, complex, or requires those choices. "
    "You must use the same response for refactors, debugging, integrations, and security-sensitive changes. "
    "Output size and detailed specs must not override these limits. "
    "For eligible work, you must output only code without Markdown fences or explanations."
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
                sys.stderr.write(f"kirby: no such file: {h}\n")
    return out


def claude_bin() -> list[str]:
    cand = os.environ.get("KIRBY_CLAUDE_BIN") or os.environ.get("CLAUDE_CODE_EXECPATH") or shutil.which("claude")
    if not cand:
        sys.exit("kirby: cannot find the `claude` executable. Set KIRBY_CLAUDE_BIN.")
    if os.name == "nt" and cand.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", cand]
    return [cand]


def ask_worker(system: str, user: str) -> str:
    if BACKEND == "openai":
        return ask_openai(system, user)
    if BACKEND != "claude":
        sys.exit(f'kirby: unknown KIRBY_BACKEND "{BACKEND}" (use "claude" or "openai")')
    return ask_claude(system, user)


def load_openai_key() -> str:
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"]
    try:
        key = OPENAI_KEY_FILE.read_text(encoding="utf-8").strip()
        if key:
            return key
    except OSError:
        pass
    sys.exit(f"kirby: no OpenAI key. Set OPENAI_API_KEY, or put the key on one line in {OPENAI_KEY_FILE}")


def ask_openai(system: str, user: str, max_tokens: int = 16384, retries: int = 3) -> str:
    """One chat-completions call to an OpenAI-compatible endpoint. Standard library only."""
    body = {
        "model": OPENAI_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_completion_tokens": max_tokens,
        "reasoning_effort": OPENAI_EFFORT,
    }
    req = urllib.request.Request(
        f"{OPENAI_BASE_URL}/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {load_openai_key()}", "Content-Type": "application/json"},
    )
    t0 = time.time()
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = json.load(r)
            break
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            if e.code in (429, 500, 502, 503) and attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            sys.exit(f"kirby: HTTP {e.code} from {OPENAI_BASE_URL}: {detail}")
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            sys.exit(f"kirby: connection failed: {e}")
    u = data.get("usage", {})
    sys.stderr.write(
        f"kirby: backend=openai model={OPENAI_MODEL} effort={OPENAI_EFFORT} "
        f"in={u.get('prompt_tokens', '?')} out={u.get('completion_tokens', '?')} ({time.time() - t0:.1f}s)\n"
    )
    return data["choices"][0]["message"]["content"] or ""


def ask_claude(system: str, user: str) -> str:
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
        sys.exit("kirby: worker timed out after 300s. Send fewer files or a narrower question.")
    if proc.returncode != 0 and not proc.stdout.strip():
        sys.exit(f"kirby: claude exited {proc.returncode}: {proc.stderr.strip()[:500]}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        sys.exit(f"kirby: unexpected output from claude: {proc.stdout[:500]}")
    if data.get("is_error"):
        sys.exit(f"kirby: worker error: {data.get('result', '')[:500]}")
    usage = data.get("usage", {})
    sys.stderr.write(
        f"kirby: backend=claude model={MODEL} in={usage.get('input_tokens', '?')} "
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
    if os.environ.get("KIRBY_DISABLE"):
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
        f"kirby: {path} is {n} lines (> {MIN_LINES}). Do not read it whole. Either:\n"
        f"  1. Delegate understanding to the cheap worker (preferred):\n"
        f'     {INVOKE} read --question "<what you need to know>" --paths "{path}"\n'
        f"  2. Or read only the section you need: Read with offset/limit (targeted reads are always allowed).\n"
        f"See the kirby-read skill. Set KIRBY_MIN_LINES to change the threshold."
    )


BASH_READERS = {"cat", "less", "more", "head", "tail", "type"}


def hook_bash() -> None:
    if os.environ.get("KIRBY_DISABLE"):
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
                        f"kirby: `{prog} {a}` would dump {n} lines (> {MIN_LINES}) into context. Instead:\n"
                        f'  {INVOKE} read --question "<what you need to know>" --paths "{a}"\n'
                        f"or use a targeted read (grep, sed -n, head -n, or Read with offset/limit)."
                    )


# ----------------------------------------------------------------------------- commands
def cmd_read(a: argparse.Namespace) -> None:
    paths = expand_paths(a.paths)
    if not paths:
        sys.exit("kirby: no readable files given")
    user = f"<question>\n{a.question}\n</question>\n\n{wrap_files(paths)}"
    print(ask_worker(READER_SYSTEM, user))


def cmd_write(a: argparse.Namespace) -> None:
    refs = expand_paths(a.reference)
    if not refs:
        sys.exit("kirby: at least one existing --reference file is required")
    ctx = expand_paths(a.context) if a.context else []
    if a.target and Path(a.target).exists() and not a.force:
        sys.exit(f"kirby: {a.target} exists; pass --force to overwrite")
    user = (
        f"<spec>\n{a.spec}\n</spec>\n\n"
        f"<reference_files note=\"match these patterns exactly\">\n{wrap_files(refs)}\n</reference_files>\n"
        + (f"\n<context_files note=\"for reference only\">\n{wrap_files(ctx)}\n</context_files>\n" if ctx else "")
        + (f"\nOutput the complete contents of the file {a.target}." if a.target else "\nOutput the complete file.")
    )
    code = strip_fences(ask_worker(WRITER_SYSTEM, user))
    if code.strip().startswith("KIRBY_NEEDS_MAIN_MODEL"):
        sys.exit("kirby: worker returned the task to the main model; no file written")
    if a.target:
        Path(a.target).parent.mkdir(parents=True, exist_ok=True)
        Path(a.target).write_text(code, encoding="utf-8", newline="\n")
        print(f"kirby: wrote {a.target} ({code.count(chr(10))} lines)")
    else:
        sys.stdout.write(code)


def main() -> None:
    ap = argparse.ArgumentParser(prog="kirby", description=__doc__,
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
