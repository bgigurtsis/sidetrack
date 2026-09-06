#!/usr/bin/env python3
"""PreToolUse guard for recognizable large whole-file reads; never executes input."""

import json
import os
from pathlib import Path
import re
import sys

TOKEN = re.compile(r"'[^']*'|\"(?:`.|\\\"|[^\"])*\"|&&|\|\||[\n|;()]|[^\s|;()]+")
READERS = {"cat", "type", "get-content", "gc", "less", "more", "bat", "head", "tail"}


def unquote(value):
    return value[1:-1] if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'" else value


def limit_value(tokens, names):
    for i, token in enumerate(tokens[:-1]):
        if token.lower() in names:
            try:
                return int(tokens[i + 1])
            except ValueError:
                return None
    return None


def shell_paths(command, threshold, depth=0):
    """Conservative literal command recognition, not a shell interpreter."""
    if depth > 3:
        return []
    tokens = TOKEN.findall(command)
    paths = []
    # Handle common shell -Command/-c wrappers without executing the inner text.
    for i, token in enumerate(tokens[:-1]):
        if token.lower() in ("-command", "-c", "-lc"):
            inner = unquote(tokens[i + 1])
            if inner != tokens[i + 1]:
                paths.extend(shell_paths(inner, threshold, depth + 1))
    segments, current = [], []
    for token in tokens:
        if token in (";", "&&", "||", "\n"):
            segments.append(current)
            current = []
        else:
            current.append(token)
    segments.append(current)
    for segment in segments:
        cleaned = [unquote(t) for t in segment]
        for i, token in enumerate(cleaned):
            name = token.lower()
            if name not in READERS:
                continue
            rest = cleaned[i + 1:]
            before = rest[:rest.index("|")] if "|" in rest else rest
            after = rest[rest.index("|") + 1:] if "|" in rest else []
            bound_flags = {"-totalcount", "-head", "-tail"}
            if name in {"head", "tail"}:
                bound_flags |= {"-n", "--lines"}
            bounded = limit_value(before, bound_flags)
            if name in {"head", "tail"} and not any(t.startswith("-") for t in before):
                bounded = 10
            if bounded is not None and 0 < bounded <= threshold:
                continue
            if after:
                reducer = after[0].lower()
                count = limit_value(after[1:], {"-first", "-last", "-n", "--lines"})
                if reducer in {"rg", "grep", "select-string", "where-object", "wc"}:
                    continue
                if reducer in {"head", "tail"} and len(after) == 1:
                    continue
                if reducer in {"select-object", "head", "tail"} and count is not None and 0 < count <= threshold:
                    continue
            skip_next = False
            for arg in before:
                if skip_next:
                    skip_next = False
                    continue
                if arg.lower() in bound_flags | {"-encoding"}:
                    skip_next = True
                elif not arg.startswith("-") and arg not in {"(", ")", "&"}:
                    paths.append(arg)
    # Literal Python full reads often used instead of cat. Dynamic code is out of scope.
    paths.extend(re.findall(r"(?:Path|open)\(\s*['\"]([^'\"]+)['\"]\s*\)\.(?:read_text|read_bytes|read)\(", command))
    return paths


def large_file(cwd, name, threshold):
    if not isinstance(name, str) or not name or "\0" in name:
        return False
    path = Path(name).expanduser()
    if not path.is_absolute():
        path = cwd / path
    try:
        with path.open("rb") as stream:
            for index, _ in enumerate(stream, 1):
                if index > threshold:
                    return True
    except OSError:
        pass
    return False


def decision(event, threshold=350):
    if os.environ.get("SIDETRACK_CODEX_DISABLE") == "1" or event.get("model") == "gpt-5.6-luna":
        return {}
    if event.get("hook_event_name") != "PreToolUse":
        return {}
    data = event.get("tool_input") or {}
    if not isinstance(data, dict):
        return {}
    name = event.get("tool_name", "")
    paths = []
    if name in ("Bash", "exec_command", "shell_command"):
        paths = shell_paths(data.get("command", data.get("cmd", "")), threshold)
    elif name in ("Read", "read_file") or name.endswith("__read_file"):
        if any(data.get(key) is not None for key in ("offset", "limit", "start_line", "end_line", "head", "tail")):
            return {}
        paths = [data.get("file_path", data.get("path"))]
    cwd = Path(data.get("workdir") or event.get("cwd") or os.getcwd())
    blocked = [p for p in dict.fromkeys(paths) if large_file(cwd, p, threshold)]
    if not blocked:
        return {}
    reason = (f"Sidetrack blocked a whole-file read exceeding {threshold} lines: "
              + json.dumps(blocked) + ". Use $sidetrack-luna's installed CLI read command with "
              "a focused question and these paths. Targeted search or a bounded excerpt is allowed. "
              "Do not bypass this guard by reading the same file through another command.")
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
            "permissionDecision": "deny", "permissionDecisionReason": reason}}


def main():
    try:
        threshold = int(os.environ.get("SIDETRACK_CODEX_MIN_LINES", "350"))
        if threshold < 1:
            threshold = 350
        result = decision(json.load(sys.stdin), threshold)
        print(json.dumps(result))
    except (ValueError, TypeError, AttributeError) as exc:
        # Bad input is visible to Codex; no claim of universal command enforcement.
        print(f"Sidetrack hook input error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
