import importlib.util
import json
from io import StringIO
from pathlib import Path

import pytest


def load_sidetrack(monkeypatch):
    """Load scripts/sidetrack.py fresh so module-level env reads pick up monkeypatched values."""
    sidetrack_path = Path(__file__).resolve().parent.parent / "scripts" / "sidetrack.py"
    spec = importlib.util.spec_from_file_location("sidetrack", str(sidetrack_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_payload(path, **extra):
    return StringIO(json.dumps({"tool_input": {"file_path": str(path), **extra}}))


def _bash_payload(command):
    return StringIO(json.dumps({"tool_input": {"command": command}}))


@pytest.fixture
def big_file(tmp_path):
    f = tmp_path / "big.py"
    f.write_text("\n" * 20)
    return f


def test_hook_read_blocks_large_files(monkeypatch, big_file):
    monkeypatch.setenv("SIDETRACK_MIN_LINES", "10")
    sidetrack = load_sidetrack(monkeypatch)
    monkeypatch.setattr("sys.stdin", _read_payload(big_file))
    with pytest.raises(SystemExit) as exc_info:
        sidetrack.hook_read()
    assert exc_info.value.code == 2


def test_hook_read_allows_offset_limit(monkeypatch, big_file):
    monkeypatch.setenv("SIDETRACK_MIN_LINES", "10")
    sidetrack = load_sidetrack(monkeypatch)
    monkeypatch.setattr("sys.stdin", _read_payload(big_file, offset=0, limit=50))
    sidetrack.hook_read()  # must not raise


def test_hook_read_allows_small_files(monkeypatch, tmp_path):
    monkeypatch.setenv("SIDETRACK_MIN_LINES", "10")
    sidetrack = load_sidetrack(monkeypatch)
    small = tmp_path / "small.py"
    small.write_text("\n" * 5)
    monkeypatch.setattr("sys.stdin", _read_payload(small))
    sidetrack.hook_read()


def test_hook_read_respects_sidetrack_disable(monkeypatch, big_file):
    monkeypatch.setenv("SIDETRACK_MIN_LINES", "10")
    monkeypatch.setenv("SIDETRACK_DISABLE", "1")
    sidetrack = load_sidetrack(monkeypatch)
    monkeypatch.setattr("sys.stdin", _read_payload(big_file))
    sidetrack.hook_read()


def test_hook_bash_blocks_cat_of_large_file(monkeypatch, big_file):
    monkeypatch.setenv("SIDETRACK_MIN_LINES", "10")
    sidetrack = load_sidetrack(monkeypatch)
    monkeypatch.setattr("sys.stdin", _bash_payload(f'cat "{big_file}"'))
    with pytest.raises(SystemExit) as exc_info:
        sidetrack.hook_bash()
    assert exc_info.value.code == 2


@pytest.mark.parametrize("template", [
    'cat "{f}" | grep x',   # piped: targeted
    'head -n 5 "{f}"',      # bounded head
    'sed -n 1,5p "{f}"',    # not a dump command
    'git status',           # unrelated
])
def test_hook_bash_allows_targeted_commands(monkeypatch, big_file, template):
    monkeypatch.setenv("SIDETRACK_MIN_LINES", "10")
    sidetrack = load_sidetrack(monkeypatch)
    monkeypatch.setattr("sys.stdin", _bash_payload(template.format(f=big_file)))
    sidetrack.hook_bash()  # must not raise


def test_backend_defaults_to_claude(monkeypatch):
    monkeypatch.delenv("SIDETRACK_BACKEND", raising=False)
    sidetrack = load_sidetrack(monkeypatch)
    assert sidetrack.BACKEND == "claude"


def test_backend_openai_is_selected_and_routed(monkeypatch):
    monkeypatch.setenv("SIDETRACK_BACKEND", "openai")
    sidetrack = load_sidetrack(monkeypatch)
    assert sidetrack.BACKEND == "openai"
    monkeypatch.setattr(sidetrack, "ask_openai", lambda s, u: f"openai:{u}")
    monkeypatch.setattr(sidetrack, "ask_claude", lambda s, u: "claude")
    assert sidetrack.ask_worker("sys", "hi") == "openai:hi"


def test_backend_unknown_exits(monkeypatch):
    monkeypatch.setenv("SIDETRACK_BACKEND", "bogus")
    sidetrack = load_sidetrack(monkeypatch)
    with pytest.raises(SystemExit):
        sidetrack.ask_worker("sys", "hi")


def test_openai_key_from_file(monkeypatch, tmp_path):
    keyfile = tmp_path / "k"
    keyfile.write_text("sk-test\n")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("SIDETRACK_OPENAI_KEY_FILE", str(keyfile))
    sidetrack = load_sidetrack(monkeypatch)
    assert sidetrack.load_openai_key() == "sk-test"


def test_strip_fences(monkeypatch):
    sidetrack = load_sidetrack(monkeypatch)
    assert sidetrack.strip_fences("```python\nx = 1\n```") == "x = 1\n"
    assert sidetrack.strip_fences("x = 1") == "x = 1\n"
