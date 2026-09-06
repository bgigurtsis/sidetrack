# Live test

This test uses your existing Codex subscription allowance. First run
`codex login status` and confirm ChatGPT sign-in, then install Sidetrack and open a
new task in a scratch directory. The expected checks below are intentionally small;
this validates both workers, not the amount of savings or automatic routing on
large real-world projects.

Create `reference.py`:

```python
def double(value: int) -> int:
    """Return twice the input value."""
    return value * 2
```

Ask Codex:

> Test Sidetrack using two fresh-context Luna workers. Have
> `sidetrack_luna_bulk_reader` read reference.py and report its function, behavior,
> and line references. Independently have `sidetrack_luna_code_writer` create
> arithmetic.py with triple(value: int) -> int and quadruple(value: int) -> int,
> following reference.py. While they work, derive expected positive, negative, and
> zero input cases without reading the source. Review the generated file and run
> the checks afterward. Do not substitute the main model for missing workers.
> Report which workers actually ran and any limitation.

Expected: the reader identifies `double` on line 1 and multiplication by two on
line 3. The writer creates only `arithmetic.py`; your main model reviews it.
Verify the child model is `gpt-5.6-luna` in the client’s available subagent details.
Changing the main model should leave both worker models set to Luna.

Run these independent checks from the scratch directory:

```sh
python3 -c "from arithmetic import triple, quadruple; values=(-100,-2,-1,0,1,4,100,10**30); assert all(triple(v)==3*v and quadruple(v)==4*v for v in values); print('16 checks passed')"
```

If the workers are unavailable, check the installed files with
`python3 codex/install.py status` from the Sidetrack checkout, verify model access,
and update Codex. Managed workspace settings can disable subagents or restrict
model access. An existing long-running task may need to be replaced with a new one.
