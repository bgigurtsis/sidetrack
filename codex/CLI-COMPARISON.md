# Historical CLI versus native subagent comparison

These trials were measured on 6 September 2026. For these small, fully specified
tasks, the CLI workflow was faster and produced correct results. Kirby now uses
native Luna subagents by default; the CLI is optional and requires an explicit
request and source-processing authorization. The timings do not assess today's
approval behavior or verify the migrated installation.

| Task | CLI trial 1 / 2 | Native trial 1 / 2 |
| --- | --- | --- |
| Find exceptions in a 601-line file | 6.2 / 6.0 seconds | about 36.1 / 20.8 seconds |
| Generate two typed arithmetic functions | 6.7 / 5.2 seconds | about 44.3 / 26.3 seconds |

All four generated files passed 16 independent integer-input checks each. Both
methods identified the correct exceptional services. One native reader run cited
line 85 instead of line 90 for the disabled service; both CLI runs cited correctly.
Two trials cannot establish a general accuracy advantage.

## Why the paths differ

The CLI script reads and numbers the selected files before invoking Luna. Luna
receives the source in its first request and returns an answer or code. The script
writes generated code itself. Native agents had to read files through tools and,
for generation, write through tools. One native writer also ran its own checks.
Those extra steps plausibly explain some of the observed difference; this test
does not isolate the overhead of the underlying subagent mechanism.

The CLI needs known input files. For discovery, the main model must first locate
relevant paths or provide additional context in another call. It works without
requiring an independent parallel task and appears as an ordinary shell call.

## Usage

Codex reported these Luna token counts for the CLI trials:

| Task | Input per trial | Cached input per trial | Output trial 1 / 2 |
| --- | --- | --- | --- |
| Read | 25,570 | 9,984 | 119 / 135 |
| Write | 15,431 | 9,984 | 75 / 98 |

Cached input is included in input, not additional to it. These runs retained normal
user configuration, skills, and extensions, so even the tiny writer request had
substantial context overhead. The available native-subagent interface did not
expose comparable per-worker usage; no token-cost or subscription-credit reduction
is established by this comparison.

## Method and limits

Measured on 6 September 2026, Windows, Codex CLI 0.153.4, ChatGPT sign-in, Luna with
medium reasoning effort, fresh sessions. The same source bytes and task requirements
were used in two trials per method. Reader fixture: 120 service settings, with
service-17 disabled and service-91 using retry_limit 9 instead of 3. Writer reference:
a typed double function; requested outputs were triple and quadruple.

CLI timing uses a monotonic timer around login checking, invocation, parsing, and
writing. Native timing runs from the parent's ready-to-spawn timestamp to a clock
reading immediately before the worker's final answer. It includes dispatch and an
extra timing-tool call, but excludes final-answer delivery. Native timings are
therefore approximate and not instrumented identically. A brief overlap between
one native writer and a CLI repeat, warm caches, network variation, and this user's
installed configuration can affect results. This is an exploratory comparison of
the complete workflows, not an isolated model-speed or production benchmark.
