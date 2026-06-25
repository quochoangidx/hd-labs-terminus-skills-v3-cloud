---
name: terminus-hard-python-verifier
description: Use when writing pytest verifier suites and oracle solutions for hard Python debugging tasks in Terminus. Focuses on behavioral subprocess tests, anti-cheating coverage, edge cases, and making tasks hard enough that coding agents may fail.
---

# Terminus Hard Python Verifier

Use this skill after choosing a Python debugging task.

This skill is a gate, not just a test-writing checklist. It should reject or
redesign tasks that are likely to be rated Medium, and it should prevent
quality-check failures caused by verifier behavior that is missing from
`instruction.md`.

## When To Stop

Stop and return a redesign recommendation instead of writing verifier code if
any of these are true:

- the expected oracle patch is probably a single obvious branch or <=10
  meaningful LOC in one obvious file
- the prompt keywords point directly to the exact function/class to edit
- all verifier tests exercise the same condition with only renamed inputs
- the task has already shown frontier-agent pass rate >=80%, or any frontier
  agent passes 5/5 runs
- the core bug is message-only, typo-only, docs-only, dependency-only, or config
  plumbing without cross-behavior interaction
- the verifier needs live internet, credentials, a real external service, GPU,
  browser automation, or long/flaky sleeps

Timeouts alone do not prove Hard. A task is Hard only when wrong or incomplete
fixes fail for semantic reasons.

## Hardness Target

Prefer tasks where the correct fix requires coordinating at least two concepts:

- parser state plus error recovery
- cache invalidation plus file system changes
- import/package discovery plus metadata/config parsing
- CLI option interaction plus lifecycle cleanup
- async cancellation plus cleanup/reporting
- serialization schema plus backward compatibility
- dependency resolution plus environment markers
- editable/build backend behavior plus legacy fallback preservation
- stateful idempotency (e.g., executing a command multiple times to verify state transitions)
- complex environment topologies (e.g., symlinks, read-only dirs, conflicting dependencies)

Avoid repeating the same ecosystem too often. If recent tasks from one repo
were rated Medium, mine a different source before making another task from the
same subsystem.

## Test Design

Write verifier tests that exercise the system from the outside:

- CLI: run `subprocess.run([...], capture_output=True, text=True)`.
- Library: import only public APIs unless the task is explicitly internal.
- Framework: create temporary user projects and invoke the framework command.
- File outputs: parse JSON/XML/CSV with real parsers.

Avoid reading source to assert implementation choices.

Do not assert exact internal helper names, exact source layout, or code shape.
Only assert observable behavior, structured outputs, process status, generated
files, and public API results.

## Coverage Shape

For hard tasks, include:

- one direct regression reproducer
- one boundary condition
- one normal-behavior preservation test
- one anti-shortcut test
- one test proving the failure mode is recoverable, not just hidden

For stronger Hard calibration, prefer 5-7 focused tests:

- 2 regression variants using different names/layouts/options
- 1 edge or boundary case
- 1 preservation test for normal or legacy behavior
- 1 strong anti-shortcut test using dynamically randomized inputs (e.g., `random` choices, random lengths) rather than static hardcoded variants
- 1 stateful test running the tool multiple times to verify side-effects, idempotency, or cache correctness
- 1 crash-resistance or structured-output test when relevant

Do not inflate difficulty with many near-duplicate tests. If two tests fail for
the same shallow reason, merge or redesign.

## Instruction/Test Symmetry

Map every prompt requirement to at least one test, and every tested behavior
back to `instruction.md`.

Quality checks often fail when a verifier tests preserved behavior that the
instruction never mentions. Preservation tests are not exempt.

Before finalizing, audit:

- every CLI flag asserted by tests appears naturally in `instruction.md`
- every mode/alias/fallback/legacy behavior asserted by tests is mentioned
- every structured field/XML tag/JSON key/order guarantee asserted by tests is
  stated in the instruction
- every required output file/path is named in the instruction
- no test asserts behavior that is only implied by upstream history

Example fix:

```text
Fix the `--import-mode=importlib` collection case. Keep the existing `prepend`
and `append` import modes working for the same shadowed-layout projects, and
preserve assertion rewriting for nested package tests.
```

If the instruction should stay narrower, remove the extra test instead of
silently checking hidden behavior.

## Making Python Tasks Hard

Prefer bugs involving interactions:

- datetime/timezone plus deduplication
- Decimal rounding plus aggregation order
- parser state plus error recovery
- cache invalidation plus file system changes
- pytest collection plus fixture teardown/reporting
- async cancellation plus cleanup

Avoid tasks where the fix is a single obvious if-statement unless the surrounding framework behavior is subtle.

## Anti-Shortcut Rules

Use verifier inputs that make hardcoding practically impossible for AI agents:

- generate temp projects under `tmp_path` and use complex topologies (symlinks, nested folders)
- use dynamically varied inputs (for example `uuid`-based names) for package names, strings, and data structures so agents cannot guess expected outputs from test traces; compute expectations from the generated values so tests stay deterministic and non-flaky
- use at least one unseen variant that the oracle patch must generalize to
- parse structured output instead of matching a whole file
- assert both positive and negative behavior where possible (e.g., asserting that unintended files were NOT created, processes did NOT leak)
- verify statefulness by running commands sequentially and ensuring state mutations are handled correctly (e.g., run -> modify -> run again)
- avoid leaking upstream issue URLs, PR numbers, commit hashes, upstream test
  names, or private helper names through test names or instruction text

The verifier can use descriptive local test names, but they should describe
behavior, not expose the upstream implementation strategy.

## Subprocess Test Pattern

```python
def run_cmd(args, cwd, timeout=20):
    return subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
```

On failure, include stderr/stdout in assertion messages. For generated files, assert both existence and parsed content.

Recommended helper:

```python
def combined_output(result):
    return result.stdout + "\n" + result.stderr
```

Use short timeouts for each subprocess. A verifier that regularly approaches
the task timeout is a bad verifier, even if it is semantically correct.

## XML/JSON Output Checks

Use parsers:

```python
import json
import xml.etree.ElementTree as ET

data = json.loads(path.read_text())
tree = ET.parse(path)
```

Check semantic fields rather than full formatting unless sorted key order or exact serialization is a prompt requirement.

If XML/JSON schema details are asserted, `instruction.md` must explicitly state
those fields/tags and whether ordering or multiplicity matters.

## Verifier Quality Gate

Before accepting the verifier, answer these questions:

- Does `nop` fail for the intended behavioral reason only?
- Does `oracle` pass every test deterministically?
- Does each test have a docstring naming the behavior it validates?
- Would a source-grep patch or prompt-keyword search lead directly to the fix?
- Are there at least two independent failure modes for incomplete fixes?
- Are preservation tests explicitly described in `instruction.md`?
- Are verifier dependencies available before `tests/test.sh` starts?
- Does `tests/test.sh` avoid runtime setup and network access?

If any answer is no, repair the task before running real agents.

Before handoff, write a compact requirement-to-test map for the reviewer-facing
Verification Explanation. For each behavioral group, record:

- the observable requirement
- the direct, boundary, preservation, anti-shortcut, or recoverability role
- why the case fails on the buggy state or a plausible partial fix
- whether oracle/nop validation actually ran

Keep this map in external reports, not in `instruction.md`, `environment/`, or
the submission ZIP. The final explanation should describe behavioral coverage,
not test function names, hidden fixture details, or source-code shape.

## tests/test.sh

Use this pattern:

```bash
#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier

if [ "$PWD" = "/" ]; then
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi

python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
rc=$?
if [ "$rc" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
```

The final reward block must end the script. The current `check_test_sh` gate
accepts either `if [ $? -eq 0 ]` immediately after pytest or the preferred
defensive form above, where `rc=$?` is captured immediately after pytest and
used in `if [ "$rc" -eq 0 ]`. Do not wrap the block in a helper, add extra
commands between pytest and the capture/conditional, or rewrite it as
`pytest && echo 1`.
Do not add `exit $?` or any other trailing exit after the final `fi`. Harbor
reads `/logs/verifier/reward.txt` for pass/fail; the script's exit code is not
the reward signal.

Verifier dependencies must be available before `tests/test.sh` starts. Install
`pytest`, `pytest-json-ctrf`, and other verifier-only packages in the Docker
image with exact pins. Do not put dependency wheels in `tests/`, and do not run
`pip install` from `tests/test.sh`.

Keep project runtime dependencies separate from verifier-only packages.

## Oracle Pattern

For large repos:

```bash
#!/bin/bash
set -euo pipefail

cd /app
patch -p1 < /solution/fix.patch
python -m pytest <focused upstream or smoke test>
```

For small apps, `solve.sh` may rewrite files directly, but it must implement general behavior and not encode verifier outputs.

The oracle should pass at least one variant that was not copied directly from
the upstream regression. Reject oracle patches that only satisfy the exact
visible verifier strings, filenames, or fixture names.
