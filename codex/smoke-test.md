# Live CLI test

This uses your existing Codex subscription allowance. Check `codex login status`
first, then create a scratch workspace with this `reference.py`:

```python
def double(value: int) -> int:
    """Return twice the input value."""
    return value * 2
```

From the Sidetrack checkout (replace the workspace path):

```sh
python3 codex/cli.py --workspace /path/to/scratch read --question "What does this function do? Cite its lines." --paths reference.py
python3 codex/cli.py --workspace /path/to/scratch write --spec "Generate triple and quadruple functions following the reference" --reference reference.py --target arithmetic.py
```

Expected: the reader identifies double at line 1 and multiplication by two at
line 3. The writer creates arithmetic.py. Inspect it, then from the scratch directory:

```sh
python3 -c "from arithmetic import triple, quadruple; assert all(triple(v)==3*v and quadruple(v)==4*v for v in (-100,-2,-1,0,1,4,100,10**30)); print('16 checks passed')"
```

To check installed routing, open a new Codex task and ask it to use `$sidetrack-luna`
on these files, with a different new output target. It should invoke the installed
Python script; it should not spawn a native subagent. Review the tool calls.

## Test the installed hook

After reviewing/trusting Sidetrack in `/hooks`, create a scratch fixture:

```sh
python3 -c "from pathlib import Path; Path('large_fixture.py').write_text('# fixture line\n' * 351)"
```

In a new Codex task with a main model other than Luna, ask for one intentional
`cat large_fixture.py` probe (Windows: `Get-Content -Raw large_fixture.py`). The
hook should deny the call before file content appears. Then ask for a 10-line
excerpt, which should succeed, and a focused summary using the installed Luna CLI.
If the probe runs, inspect `/hooks` for trust/enablement and check the client version.

For a complete installation check, run `uninstall`, confirm other settings and
hooks remain, then `install` again and repeat this probe in a fresh task.
