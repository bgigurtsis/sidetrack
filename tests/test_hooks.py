import importlib.util
import json
from pathlib import Path
from io import StringIO
import pytest


def load_sidetrack(monkeypatch):
    """Load the sidetrack module with environment already set up."""
    sidetrack_path = Path(__file__).resolve().parent.parent / "scripts" / "sidetrack.py"
    if not sidetrack_path.exists():
        raise FileNotFoundError(f"Cannot find {sidetrack_path}")
    spec = importlib.util.spec_from_file_location("sidetrack", str(sidetrack_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_hook_read_blocks_large_files(monkeypatch, tmp_path):
    """Test that hook_read blocks a file over the threshold with SystemExit code 2."""
    monkeypatch.setenv("SIDETRACK_MIN_LINES", "10")
    sidetrack = load_sidetrack(monkeypatch)
    
    # Create a file with more lines than the threshold
    large_file = tmp_path / "large.py"
    large_file.write_text("\n" * 20)
    
    # Prepare a whole-file read payload (no offset/limit)
    payload = {"tool_input": {"file_path": str(large_file)}}
    monkeypatch.setattr("sys.stdin", StringIO(json.dumps(payload)))
    
    # Expect SystemExit with code 2
    with pytest.raises(SystemExit) as exc_info:
        sidetrack.hook_read()
    assert exc_info.value.code == 2


def test_hook_read_allows_offset_limit(monkeypatch, tmp_path):
    """Test that hook_read allows targeted reads with offset/limit."""
    monkeypatch.setenv("SIDETRACK_MIN_LINES", "10")
    sidetrack = load_sidetrack(monkeypatch)
    
    # Create a file with more lines than the threshold
    large_file = tmp_path / "large.py"
    large_file.write_text("\n" * 20)
    
    # Prepare a targeted read payload with offset/limit
    payload = {
        "tool_input": {
            "file_path": str(large_file),
            "offset": 0,
            "limit": 50
        }
    }
    monkeypatch.setattr("sys.stdin", StringIO(json.dumps(payload)))
    
    # Should not raise
    sidetrack.hook_read()


def test_hook_read_respects_sidetrack_disable(monkeypatch, tmp_path):
    """Test that SIDETRACK_DISABLE=1 disables hook blocking."""
    monkeypatch.setenv("SIDETRACK_MIN_LINES", "10")
    monkeypatch.setenv("SIDETRACK_DISABLE", "1")
    sidetrack = load_sidetrack(monkeypatch)
    
    # Create a file with more lines than the threshold
    large_file = tmp_path / "large.py"
    large_file.write_text("\n" * 20)
    
    # Prepare a whole-file read payload
    payload = {"tool_input": {"file_path": str(large_file)}}
    monkeypatch.setattr("sys.stdin", StringIO(json.dumps(payload)))
    
    # Should not raise even though the file is large
    sidetrack.hook_read()


def _bash_payload(command):
    return StringIO(json.dumps({"tool_input": {"command": command}}))


def test_hook_bash_blocks_cat_of_large_file(monkeypatch, tmp_path):
    monkeypatch.setenv("SIDETRACK_MIN_LINES", "10")
    sidetrack = load_sidetrack(monkeypatch)
    big = tmp_path / "big.txt"
    big.write_text("
" * 20)
    monkeypatch.setattr("sys.stdin", _bash_payload(f'cat "{big}"'))
    with pytest.raises(SystemExit) as exc_info:
        sidetrack.hook_bash()
    assert exc_info.value.code == 2


@pytest.mark.parametrize("template", [
    'cat "{f}" | grep x',   # piped: targeted
    'head -n 5 "{f}"',      # bounded head
    'sed -n 1,5p "{f}"',    # not a dump command
    'git status',           # unrelated
])
def test_hook_bash_allows_targeted_commands(monkeypatch, tmp_path, template):
    monkeypatch.setenv("SIDETRACK_MIN_LINES", "10")
    sidetrack = load_sidetrack(monkeypatch)
    big = tmp_path / "big.txt"
    big.write_text("
" * 20)
    monkeypatch.setattr("sys.stdin", _bash_payload(template.format(f=big)))
    sidetrack.hook_bash()  # must not raise


def test_strip_fences(monkeypatch):
    sidetrack = load_sidetrack(monkeypatch)
    assert sidetrack.strip_fences("```python
x = 1
```") == "x = 1
"
    assert sidetrack.strip_fences("x = 1") == "x = 1
"
