import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("sidetrack_cli", Path(__file__).parents[1] / "cli.py")
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


def events(answer="answer", complete=True):
    result = [json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": answer}})]
    if complete:
        result.append(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 123}}))
    return "\n".join(result)


class CLITests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="sidetrack-cli-test-"))
        (self.root / "ref.py").write_text("def double(x):\n    return x * 2\n")

    def invoke(self, args, outputs):
        with patch.object(cli, "executable", return_value="codex"), patch.object(cli.subprocess, "run", side_effect=outputs) as runner:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                result = cli.main(["--workspace", str(self.root), *args])
        return result, runner

    def login(self):
        return subprocess.CompletedProcess([], 0, "Logged in using ChatGPT", "")

    def test_write_uses_stdin_and_exclusive_target(self):
        response = subprocess.CompletedProcess([], 0, events("```python\ndef triple(x):\n    return x * 3\n```"), "")
        rc, runner = self.invoke(["write", "--spec", "triple; $(not-a-command)", "--reference", "ref.py", "--target", "out.py"], [self.login(), response])
        self.assertEqual(rc, 0)
        self.assertEqual((self.root / "out.py").read_text(), "def triple(x):\n    return x * 3\n")
        call = runner.call_args_list[1]
        self.assertIn("$(not-a-command)", call.kwargs["input"])
        self.assertNotIn("$(not-a-command)", str(call.args))
        self.assertNotIn("shell", call.kwargs)
        self.assertIn('forced_login_method="chatgpt"', call.args[0])
        self.assertIn("read-only", call.args[0])

    def test_api_session_is_rejected_before_model_call(self):
        login = subprocess.CompletedProcess([], 0, "Logged in using an API key", "")
        rc, runner = self.invoke(["read", "--question", "What?", "--paths", "ref.py"], [login])
        self.assertEqual(rc, 1)
        self.assertEqual(runner.call_count, 1)

    def test_existing_target_is_not_overwritten(self):
        rc, runner = self.invoke(["write", "--spec", "replace", "--reference", "ref.py", "--target", "ref.py"], [])
        self.assertEqual(rc, 1)
        self.assertEqual(runner.call_count, 0)

    def test_incomplete_response_never_writes(self):
        rc, _ = self.invoke(["write", "--spec", "triple", "--reference", "ref.py", "--target", "out.py"],
                            [self.login(), subprocess.CompletedProcess([], 0, events("partial", False), "")])
        self.assertEqual(rc, 1)
        self.assertFalse((self.root / "out.py").exists())

    def test_failed_turn_rejected(self):
        with self.assertRaises(ValueError):
            cli.parse_events('{"type":"turn.failed","error":"limit"}')

    def test_timeout_never_writes(self):
        rc, _ = self.invoke(["write", "--spec", "triple", "--reference", "ref.py", "--target", "out.py"],
                            [self.login(), subprocess.TimeoutExpired("codex", 1)])
        self.assertEqual(rc, 1)
        self.assertFalse((self.root / "out.py").exists())

    def test_path_escape_rejected(self):
        with self.assertRaises(ValueError):
            cli.within(self.root, "../elsewhere")

    def test_input_limit_and_line_numbers(self):
        files = cli.corpus(self.root, ["ref.py", "ref.py"])
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["lines"][1], {"line": 2, "text": "    return x * 2"})
        with patch.object(cli, "MAX_BYTES", 1), self.assertRaises(ValueError):
            cli.corpus(self.root, ["ref.py"])

    def test_read_reports_usage(self):
        rc, _ = self.invoke(["--report", "metrics.json", "read", "--question", "What?", "--paths", "ref.py"],
                            [self.login(), subprocess.CompletedProcess([], 0, events(), "")])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads((self.root / "metrics.json").read_text())["usage"]["input_tokens"], 123)


if __name__ == "__main__":
    unittest.main()
