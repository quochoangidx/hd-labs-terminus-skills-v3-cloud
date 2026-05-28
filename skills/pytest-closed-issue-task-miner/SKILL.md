---
name: pytest-closed-issue-task-miner
description: Use when designing hard Terminus Regular Python tasks from closed pytest-dev/pytest GitHub issues or pull requests. Helps select suitable bug domains, transform an upstream regression into a benchmark task, and avoid tasks that are too easy or too close to docs-only fixes.
---

# Pytest Closed Issue Task Miner

Use this skill when sourcing task ideas from `pytest-dev/pytest` closed issues or PRs.

## Source Selection

Prefer closed bugs or PRs involving pytest internals:

- fixture setup/finalization ordering
- `--maxfail`, `--lf`, `--ff`, `-x`, or interrupt handling
- assertion rewriting and traceback rendering
- parametrization ID generation and collection
- plugin hooks and report lifecycle
- JUnit XML, terminal summary, or warnings integration
- path/import mode edge cases
- xdist-facing behavior only if the task can run without needing xdist

Avoid as Hard tasks:

- documentation-only fixes
- typo or message-only changes
- single-line option validation
- release metadata, dependency bumps, or typing-only PRs
- issues requiring external plugins, network, or unavailable OS services

## Hardness Filter

A good Hard candidate should require the agent to understand at least two pytest subsystems. Examples:

- fixture finalization plus JUnit XML reporting
- collection tree plus import/path mode
- assertion rewriting plus traceback formatting
- warning capture plus terminal reporting
- hook ordering plus test outcome propagation

Reject candidates solvable by only matching the issue title or changing one expected string.

## Transformation Pattern

1. Pin `environment/repo/` to a pytest commit before the fix.
2. Remove upstream tests that reveal the exact patch if needed.
3. Write a prompt describing user-visible pytest behavior only.
4. Put reproducer projects inside verifier tests, not in the prompt.
5. Verify the starting state fails by behavior.
6. Write oracle as `solution/fix.patch` plus `solution/solve.sh`.
7. Test both the regression and normal behavior.

## Prompt Template

```md
Pytest in `/app` mishandles <observable scenario>. A user project that <setup> currently <bad behavior>.

Fix pytest so `python -m pytest <command shape>` <required behavior>. The run should <preserve important existing behavior>. Do not change the user project's tests.
```

Keep issue URLs and PR IDs out of `instruction.md`.

## Verifier Patterns

Verifier tests should create temporary user projects and run:

```python
subprocess.run(
    ["python", "-m", "pytest", "<test file>", "...options..."],
    cwd="/app",
    capture_output=True,
    text=True,
)
```

Assert externally visible behavior:

- return code category
- no `INTERNALERROR` unless explicitly expected
- terminal output includes or excludes key user-facing text
- JUnit XML structure when relevant
- side-effect files prove skipped or unexecuted tests did not run
- behavior without the edge case remains unchanged

## Example Hard Candidate

Issue domain: fixture teardown under `--maxfail=1` with JUnit XML.

Why hard:

- requires runner/session stop logic
- requires fixture teardown reporting
- requires JUnit XML plugin outcome mapping
- cannot be fixed by changing one output string

Expected task behavior:

- first failing test is reported
- already-started fixture teardown error is also reported
- later tests are not executed because maxfail is honored
- no internal traceback
- XML records both failure and error
