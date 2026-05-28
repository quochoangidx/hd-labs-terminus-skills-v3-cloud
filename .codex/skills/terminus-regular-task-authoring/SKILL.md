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

## Docker Rules

`environment/Dockerfile` must:

- Use `FROM ...@sha256:<digest>`.
- Install `tmux` and `asciinema`.
- Pin language dependencies exactly.
- Bake verifier dependencies into the image; `tests/test.sh` must not fetch from the network.
- Keep `environment/` under 100 MiB total and each file under 50 MiB.
- Include `.dockerignore` for non-trivial environments.

## Verifier Rules

Tests must:

- Be Python pytest tests, even for non-Python tasks.
- Test behavior, not source-code strings.
- Have docstrings on every test.
- Cover every explicit and important implicit prompt requirement.
- Include boundary cases and at least one regression guard.
- Assert no internal crash/traceback when the task is about recoverable behavior.

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
harbor tasks check -m openai/@openai/gpt-5.2 <task-folder>
```

For submission ZIPs, compress the contents of the task folder, not the folder itself.
