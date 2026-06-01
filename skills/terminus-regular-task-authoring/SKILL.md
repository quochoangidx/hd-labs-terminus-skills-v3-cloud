---
name: terminus-regular-task-authoring
description: Use when creating, reviewing, or repairing a Terminus-2nd-Edition Regular non-milestone task, especially from the Snorkel Platform Submission Guide. Covers required layout, Docker constraints, oracle/verifier expectations, CI readiness, and ZIP submission hygiene.
---

# Terminus Regular Task Authoring

Use this skill when the user asks to create or audit a Regular Terminus task.

## Required Layout

Regular tasks must contain:

```text
instruction.md
task.toml
environment/
  Dockerfile
  .dockerignore
  [agent-visible app/source files]
solution/
  solve.sh
  [optional fix.patch]
tests/
  test.sh
  test_outputs.py
  [optional fixtures]
```

Do not use root-level `steps/` unless the task is explicitly milestone-based. Do not put `tests/` or `solution/` inside the image.

## Authoring Workflow

1. Pick a real engineering bug with multi-step reasoning.
2. Write concise `instruction.md` using absolute paths only.
3. Configure `task.toml` with `version = "2.0"`, metadata, runtime limits, and `allow_internet = false`.
4. Build `environment/Dockerfile` with `tmux`, `asciinema`, pinned package versions, and digest-pinned `FROM`.
5. Put a deliberately buggy starting state under `environment/`.
6. Write deterministic `solution/solve.sh`; prefer `fix.patch` for large codebases.
7. Write Python `pytest` verifier tests in `tests/test_outputs.py`.
8. Make `tests/test.sh` run pytest and always write `/logs/verifier/reward.txt`.
9. Run oracle, CI checks, and real-agent trials before packaging.

## Prompt Rules

`instruction.md` should:

- Be short and human-styled.
- State observable behavior, not implementation hints.
- Mention all required paths and output files.
- Avoid issue URLs, PR numbers, exact test names, canaries, and rubrics.
- Include enough edge-case requirements that tests are fair.

Before finalizing, run an instruction/test symmetry audit:

- list every exact string, flag, command, file path, output key, XML/JSON field, and ordering guarantee asserted by tests
- ensure each asserted behavior appears naturally in `instruction.md`
- include preservation requirements explicitly, even when they test "unchanged" behavior outside the main bug path
- if tests cover non-target modes, aliases, legacy modes, fallback paths, or normal layouts, state that those modes must continue working
- remove tests for behavior that would be unfair to state in the prompt
- keep implementation symbols out of the prompt unless they are public API

Common quality-check failure: a test asserts that unaffected modes such as `prepend`/`append`, non-editable installs, normal parsers, or legacy fallbacks still work, but `instruction.md` only describes the target mode. Fix by adding one natural sentence like "Keep `<mode A>` and `<mode B>` behavior unchanged for the same layout" or remove that preservation test.

## Docker Rules

`environment/Dockerfile` must:

- Use `FROM ...@sha256:<digest>`.
- Install `tmux` and `asciinema`.
- Pin language dependencies exactly.
- Keep verifier dependency handling compatible with the active platform quality
  checker. Never fetch packages from the network at verifier runtime.
- Keep `environment/` under 100 MiB total and each file under 50 MiB.
- Include `.dockerignore` for non-trivial environments.

For Python tasks, separate project/runtime dependencies from verifier-only
dependencies.

If the active quality checker flags `test_deps_in_image`, put verifier-only
wheels under `tests/files/wheels` and install them in `tests/test.sh` with
`--no-index`. If the active docs/checker require baked verifier dependencies,
install `pytest`, `pytest-json-ctrf`, and verifier packages in the Docker image
instead. Pin exact versions either way.

## Verifier Rules

Tests must:

- Be Python pytest tests, even for non-Python tasks.
- Test behavior, not source-code strings.
- Have docstrings on every test.
- Cover every explicit and important implicit prompt requirement.
- Include boundary cases and at least one regression guard.
- Assert no internal crash/traceback when the task is about recoverable behavior.

Avoid quality-check failures:

- do not assert source-code shape, private helper names, or exact implementation
- parse structured outputs semantically
- include docstrings explaining the user behavior being tested
- keep randomization deterministic
- ensure `nop` fails for the intended behavior, not setup/tooling

## tests/test.sh

Use this shape:

```bash
#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile before running this script."
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi

cd /app

python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
```

The final reward block must be exactly this shape because the platform static
checker matches it literally. Do not store `$?` in a variable, wrap the block in
a helper, add extra commands after it, or rewrite it as `pytest && echo 1`.

Do not run `pip install`, `apt-get`, `npm install`, or network downloads in `tests/test.sh`.

## Oracle Rules

`solution/solve.sh` must:

- Start with `set -euo pipefail`.
- Be deterministic and self-contained.
- Avoid network access.
- Apply a real fix, not write hardcoded expected outputs.
- Rebuild or regenerate artifacts when the verifier invokes a built binary.

## Final Checks

Run, when available:

```bash
harbor run -a oracle -p <task-folder>
harbor run -a nop -p <task-folder>
harbor tasks check -m openai/@openai/gpt-5.2 <task-folder>
```

For submission ZIPs, compress the contents of the task folder, not the folder itself.

Quality preflight:

- no `.ruff_cache`, `.pytest_cache`, `__pycache__`, `.DS_Store`, `._*`, `__MACOSX`, reports, logs, or submissions in the ZIP
- no `tests/` or `solution/` copied into the Docker image
- no network dependency installation at verifier runtime; local wheel installs
  are allowed only when needed to satisfy the active platform checker
- oracle passes, nop fails, and failures are behavioral rather than infrastructure
