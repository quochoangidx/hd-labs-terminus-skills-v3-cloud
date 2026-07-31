---
name: issue-to-regression-test
description: Use when converting a closed upstream issue or PR into behavioral pytest verifier tests for a hard Terminus task. Helps derive reproducer, normal behavior preservation, boundary cases, anti-shortcut checks, and instruction/test symmetry.
---

# Issue To Regression Test

> ⛔ **Lane gate (2026-07-19).** The upstream-issue→regression-test lane serves a
> mostly-dead shape: mechanical fixes of real upstream bugs collapse 3/3
> regardless of file spread (AGENTS.md §6), and the repair shape fires the
> repair-shape→debugging prediction rule (`task-miner/category_rules.md`). Run the
> collapse-law screen + rules-first category gate on the candidate FIRST. The
> test-design content below remains valid for verifier authoring generally.

Use this skill after selecting an upstream closed issue/PR and before writing `tests/test_outputs.py`.

## Goal

Turn upstream behavior into verifier tests that are:

- deterministic
- offline
- behavioral
- hard to shortcut
- fair from `instruction.md`

## Extraction Steps

1. Read the issue for user-visible symptom.
2. Read the fixing PR for changed tests and scope.
3. Identify the smallest public command/API that reproduces the pre-fix failure.
4. Rewrite the reproducer as a temporary project or input built inside the verifier.
5. Add tests for normal behavior that must not regress.
6. Add at least one anti-shortcut test that prevents a narrow hardcoded fix.

Do not paste upstream test names or PR details into `instruction.md`.

Every preservation test must map to a prompt sentence. If a test checks an unaffected mode, alias, fallback path, legacy layout, or normal case, add natural language to `instruction.md` such as "Keep `<mode>` behavior unchanged" or drop the test. Quality checks fail when verifier-only preservation requirements are missing from the prompt.

Do not move prompt requirements into environment README/spec files to satisfy
length or style limits. Environment docs can define realistic schemas,
protocols, and business rules, but they must not become hidden solution guides
or secondary instructions for the agent.

## Test Set Shape

For hard tasks, aim for 4-6 tests:

1. direct regression reproducer
2. boundary/ordering variant
3. normal behavior preservation
4. anti-shortcut or duplicate-path case
5. recoverability/no-internal-crash case
6. output format/schema case if relevant

Each test must have a docstring.

## Temporary Project Pattern

```python
def write_file(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_pytest(project, *args):
    return subprocess.run(
        ["python", "-m", "pytest", *args],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=30,
    )
```

For framework tasks, create a minimal user project in `tmp_path` and invoke the framework exactly as a user would.

## Assertions

Prefer semantic assertions:

- parse JSON/XML instead of comparing whole files
- assert return code category
- assert absence of `INTERNALERROR` for recoverable bugs
- assert side-effect files prove a test did or did not execute
- assert exact diagnostic string only when the prompt promises it

Avoid:

- inspecting source code
- importing private implementation details unless the task is explicitly internal
- tests that only check a new function/kwarg exists
- loose substring checks for exact error-message requirements

## Instruction Symmetry

Before finalizing tests, list every literal or public symbol asserted by tests:

- command names
- file paths
- function/class/constant names
- output keys
- exact error strings
- ordering guarantees
- boundary values

Ensure each appears in `instruction.md` in natural language. If it is not fair to put it in the prompt, remove or weaken the test.

Pay special attention to preservation cases: flags or modes that are not the main bug trigger still count as asserted behavior.

## Anti-Shortcut Ideas

Use whichever fits:

- duplicate scenario with different data to defeat hardcoded output
- boundary just below and just above threshold
- normal case without the bug trigger
- checksum for files the prompt forbids editing
- side-effect sentinel proving a later test did not run
- randomized-looking but deterministic fixture data

## Handoff

When writing the final verifier, include a short mapping for yourself:

```text
prompt requirement -> test function
```

Do not include this mapping in task files unless it is useful as comments; keep task files concise.
