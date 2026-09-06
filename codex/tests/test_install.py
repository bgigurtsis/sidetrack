"""Offline installer tests. Test artifacts stay in a temporary directory."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("sidetrack_install", Path(__file__).parents[1] / "install.py")
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="sidetrack-test-")).resolve()

    def run_action(self, action, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return installer.main([action, "--codex-home", str(self.root), *args])

    def test_install_preserves_config_and_auth(self):
        for name in ("config.toml", "auth.json"):
            (self.root / name).write_bytes(b"untouched")
        self.assertEqual(self.run_action("install"), 0)
        self.assertEqual(self.run_action("status"), 0)
        for name in ("config.toml", "auth.json"):
            self.assertEqual((self.root / name).read_bytes(), b"untouched")
        for name in installer.ASSETS:
            self.assertTrue((self.root / name).is_file())

    def test_reinstall_is_idempotent(self):
        self.run_action("install")
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(self.run_action("install"), 0)
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_uninstall_preserves_existing_instruction_bytes(self):
        original = b"# User preferences\r\n\r\nKeep my settings.\r\n"
        (self.root / "AGENTS.md").write_bytes(original)
        self.run_action("install")
        self.assertEqual(self.run_action("uninstall"), 0)
        self.assertEqual((self.root / "AGENTS.md").read_bytes(), original)
        self.assertFalse((self.root / installer.STATE).exists())
        for name in installer.ASSETS:
            self.assertFalse((self.root / name).exists())
            self.assertTrue(list((self.root / "sidetrack/backups").glob(f"*/{name}")))

    def test_override_file_is_used(self):
        (self.root / "AGENTS.override.md").write_text("User override")
        self.run_action("install")
        state = json.loads((self.root / installer.STATE).read_text())
        self.assertEqual(state["instructions"], "AGENTS.override.md")
        self.assertFalse((self.root / "AGENTS.md").exists())

    def test_new_override_is_detected(self):
        self.run_action("install")
        (self.root / "AGENTS.override.md").write_text("Shadowing instructions")
        self.assertEqual(self.run_action("status"), 1)
        self.assertEqual(self.run_action("install"), 1)
        self.assertEqual(self.run_action("uninstall"), 0)
        self.assertEqual(self.run_action("install"), 0)

    def test_dry_run_writes_nothing(self):
        self.assertEqual(self.run_action("install", "--dry-run"), 0)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_refuses_unowned_file_without_partial_install(self):
        dest = self.root / installer.ASSETS[1]
        dest.parent.mkdir(parents=True)
        dest.write_text("User agent")
        self.assertEqual(self.run_action("install"), 1)
        self.assertFalse((self.root / installer.ASSETS[0]).exists())
        self.assertEqual(dest.read_text(), "User agent")

    def test_modified_worker_prevents_uninstall_and_upgrade(self):
        self.run_action("install")
        dest = self.root / installer.ASSETS[0]
        dest.write_text("User edits")
        self.assertEqual(self.run_action("uninstall"), 1)
        self.assertEqual(self.run_action("install"), 1)
        self.assertTrue((self.root / installer.ASSETS[1]).exists())
        self.assertEqual(dest.read_text(), "User edits")

    def test_user_text_added_after_install_survives(self):
        self.run_action("install")
        path = self.root / "AGENTS.md"
        path.write_bytes(path.read_bytes() + b"\nLater preference\n")
        self.run_action("uninstall")
        self.assertEqual(path.read_bytes(), b"\nLater preference\n")

    def test_modified_routing_prevents_uninstall(self):
        self.run_action("install")
        path = self.root / "AGENTS.md"
        path.write_text(path.read_text().replace("Keep the selected", "Keep your selected"))
        self.assertEqual(self.run_action("uninstall"), 1)
        self.assertTrue((self.root / installer.STATE).exists())

    def test_symlink_destination_rejected(self):
        outside = Path(tempfile.mkdtemp(prefix="sidetrack-outside-"))
        try:
            (self.root / "skills").symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("Symlink creation unavailable on this host")
        self.assertEqual(self.run_action("install"), 1)
        self.assertEqual(list(outside.iterdir()), [])

    def test_uninstall_dry_run_preserves_files(self):
        self.run_action("install")
        self.assertEqual(self.run_action("uninstall", "--dry-run"), 0)
        self.assertEqual(self.run_action("status"), 0)

    def test_upgrade_backs_up_old_worker(self):
        self.run_action("install")
        source = Path(tempfile.mkdtemp(prefix="sidetrack-source-"))
        for name in installer.ASSETS:
            dest = source / installer.SOURCES[name]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((installer.SOURCE / installer.SOURCES[name]).read_bytes())
        name = installer.ASSETS[0]
        original = (self.root / name).read_bytes()
        (source / installer.SOURCES[name]).write_bytes(original + b"\n# Updated release\n")
        with patch.object(installer, "SOURCE", source):
            self.assertEqual(self.run_action("install"), 0)
        self.assertEqual((self.root / name).read_bytes(), original + b"\n# Updated release\n")
        backups = list((self.root / "sidetrack/backups").glob(f"*/{name}"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)
        self.assertEqual(self.run_action("status"), 0)

    def test_path_escape_is_rejected(self):
        with self.assertRaises(installer.InstallError):
            installer.target(self.root, "../outside.toml")

    def legacy_install(self):
        files = {name: b"legacy managed content" for name in installer.LEGACY_ASSETS}
        for name, data in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        block = installer.START + "\nOld native routing\n" + installer.END
        (self.root / "AGENTS.md").write_bytes(("User preference\n\n" + block).encode("utf-8"))
        path = self.root / installer.STATE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"version": 1, "instructions": "AGENTS.md", "separator": "\n\n",
                                   "block": block, "hashes": {n: installer.digest(v) for n, v in files.items()}}), encoding="utf-8")

    def test_native_install_migrates_to_cli_and_archives_agents(self):
        self.legacy_install()
        self.assertEqual(self.run_action("install"), 0)
        self.assertEqual(json.loads((self.root / installer.STATE).read_text())["version"], 3)
        for name in installer.LEGACY_ASSETS[:2]:
            self.assertFalse((self.root / name).exists())
            self.assertTrue(list((self.root / "sidetrack/backups").glob(f"*/{name}")))
        self.assertIn("User preference", (self.root / "AGENTS.md").read_text())
        self.assertNotIn("Old native routing", (self.root / "AGENTS.md").read_text())
        self.assertEqual(self.run_action("uninstall"), 0)
        self.assertEqual((self.root / "AGENTS.md").read_text(), "User preference")

    def test_migration_does_not_overwrite_unowned_cli_script(self):
        self.legacy_install()
        path = self.root / installer.ASSETS[0]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("My script")
        self.assertEqual(self.run_action("install"), 1)
        self.assertEqual(path.read_text(), "My script")
        self.assertTrue((self.root / installer.LEGACY_ASSETS[0]).exists())


if __name__ == "__main__":
    unittest.main()
