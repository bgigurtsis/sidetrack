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
