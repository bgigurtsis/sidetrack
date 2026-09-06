"""Test actual hook decisions and shared configuration ownership."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).parents[1]
sys.path.insert(0, str(SOURCE))
import read_hook
import hook_config
import test_install


class ReadHookTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="sidetrack-hook-")).resolve()
        (self.root / "large file.py").write_text("value = 1\n" * 351)
        (self.root / "small.py").write_text("value = 1\n" * 350)

    def event(self, command):
        return {"hook_event_name": "PreToolUse", "model": "gpt-5.6-terra",
                "cwd": str(self.root), "tool_name": "Bash", "tool_input": {"command": command}}

    def test_whole_reads_blocked(self):
        for command in ["cat 'large file.py'", 'Get-Content -Raw -LiteralPath "large file.py"',
                        "cat -n 'large file.py'", "head -n 999 'large file.py'",
                        "tail -n -1 'large file.py'", "Get-Content 'large file.py'\ncat small.py | head",
                        'powershell -Command "Get-Content -Raw \'large file.py\'"',
                        'python -c "print(Path(\'large file.py\').read_text())"']:
            with self.subTest(command=command):
                result = read_hook.decision(self.event(command))
                self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_targeted_reads_and_cli_allowed(self):
        for command in ["cat small.py", "head -n 30 'large file.py'",
                        "Get-Content 'large file.py' -TotalCount 20",
                        "Get-Content 'large file.py' | Select-Object -First 40",
                        "cat 'large file.py' | rg value", "rg value 'large file.py'",
                        "python sidetrack.py read --question test --paths 'large file.py'"]:
            with self.subTest(command=command):
                self.assertEqual(read_hook.decision(self.event(command)), {})

    def test_luna_and_other_events_skip(self):
        event = self.event("cat 'large file.py'")
        event["model"] = "gpt-5.6-luna"
        self.assertEqual(read_hook.decision(event), {})
        event["model"] = "gpt-6-astra"
        event["hook_event_name"] = "PostToolUse"
        self.assertEqual(read_hook.decision(event), {})

    def test_file_read_tool_and_workdir(self):
        event = self.event("cat 'large file.py'")
        event["cwd"] = str(self.root.parent)
        event["tool_input"]["workdir"] = str(self.root)
        self.assertTrue(read_hook.decision(event))
        event["cwd"] = str(self.root)
        event["tool_name"] = "Read"
        event["tool_input"] = {"file_path": "large file.py"}
        self.assertTrue(read_hook.decision(event))
        event["tool_input"]["limit"] = 20
        self.assertEqual(read_hook.decision(event), {})

    def test_real_stdin_protocol(self):
        result = subprocess.run([sys.executable, str(SOURCE / "read_hook.py")],
                                input=json.dumps(self.event("cat 'large file.py'")),
                                capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")


class HookInstallTests(unittest.TestCase):
    setUp = test_install.InstallerTests.setUp
    run_action = test_install.InstallerTests.run_action

    def test_checkout_newlines_do_not_change_hook_identity(self):
        self.run_action("install")
        installer = test_install.installer
        before = (self.root / "hooks.json").read_bytes()
        source = Path(tempfile.mkdtemp(prefix="sidetrack-crlf-"))
        for name in installer.ASSETS:
            dest = source / installer.SOURCES[name]
            dest.parent.mkdir(parents=True, exist_ok=True)
            data = (installer.SOURCE / installer.SOURCES[name]).read_bytes()
            dest.write_bytes(data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        with patch.object(installer, "SOURCE", source):
            self.assertEqual(self.run_action("install"), 0)
        self.assertEqual((self.root / "hooks.json").read_bytes(), before)

    def test_unrelated_hooks_restored_exactly(self):
        original = b'{"hooks":{"SessionStart":[{"hooks":[{"type":"command","command":"echo hello"}]}]}}\n'
        (self.root / "hooks.json").write_bytes(original)
        self.assertEqual(self.run_action("install"), 0)
        self.assertEqual(self.run_action("uninstall"), 0)
        self.assertEqual((self.root / "hooks.json").read_bytes(), original)

    def test_later_hooks_survive_uninstall(self):
        self.run_action("install")
        path = self.root / "hooks.json"
        document = json.loads(path.read_text())
        other = {"hooks": [{"type": "command", "command": "echo added"}]}
        document["hooks"]["PreToolUse"].append(other)
        path.write_text(json.dumps(document))
        self.assertEqual(self.run_action("uninstall"), 0)
        self.assertEqual(json.loads(path.read_text()), {"hooks": {"PreToolUse": [other]}})

    def test_modified_hook_refuses_mutation(self):
        self.run_action("install")
        path = self.root / "hooks.json"
        path.write_text(path.read_text().replace(hook_config.STATUS, "User changed"))
        before = path.read_bytes()
        self.assertEqual(self.run_action("install"), 1)
        self.assertEqual(self.run_action("uninstall"), 1)
        self.assertEqual(path.read_bytes(), before)

    def test_absent_original_hooks_leaves_valid_empty_config(self):
        self.run_action("install")
        self.run_action("uninstall")
        self.assertEqual(json.loads((self.root / "hooks.json").read_text()), {})

    def test_cli_v2_upgrade(self):
        self.run_action("install")
        import install
        state_path = self.root / install.STATE
        state = json.loads(state_path.read_text())
        state["version"] = 2
        state.pop("hook_entry")
        state.pop("hooks_before")
        state["hashes"].pop(hook_config.HOOK_PATH)
        state_path.write_text(json.dumps(state))
        (self.root / hook_config.HOOK_PATH).rename(self.root / "retired-hook.py")
        (self.root / "hooks.json").write_text("{}")
        self.assertEqual(self.run_action("install"), 0)
        self.assertEqual(json.loads(state_path.read_text())["version"], 3)
