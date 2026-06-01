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

## Metadata Rules

For new submissions:

- Set `codebase_size` to `small` or `large`; do not use `minimal`.
- Use `small` for roughly 20-199 useful files in `environment/`.
- Use `large` for roughly 200+ useful files in `environment/`.
- If the staged environment has fewer than 20 useful files, add realistic
  project context or redesign the task instead of padding with blank filler.

## Prompt Rules

`instruction.md` should:

- Be short and human-styled.
- State observable behavior, not implementation hints.
- Mention all required paths and output files.
- Avoid issue URLs, PR numbers, exact test names, canaries, and rubrics.
- Include enough edge-case requirements that tests are fair.

Environment files must not compensate for a short prompt:

- Do not hide step-by-step walkthroughs, TODO hints, commented solution guides,
  or prescriptive implementation notes in README, config, scripts, comments, or
  source files.
- `spec.md`, README, and architecture docs may define requirements, schemas,
  protocols, or business rules, but they must state what the system requires,
  not how to solve the task.
- Do not split the task's logical prompt or goals out of `instruction.md` into
  environment docs to dodge length limits. Supporting docs should read like
  realistic engineering artifacts, not prompt extensions.

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
- Use a sanctioned or explicitly exempt final runtime base image, such as
  `python:*@sha256:<digest>`, `mcr.microsoft.com/...@sha256:<digest>`,
  `ghcr.io/snorkel-ai/...@sha256:<digest>`, or `scratch`.
- Install `tmux` and `asciinema`.
- Pin language dependencies exactly.
- Install verifier dependencies in the Docker image by default. Never fetch
  packages from the network at verifier runtime.
- Keep `environment/` under 100 MiB total and each file under 50 MiB.
- Include `.dockerignore` for non-trivial environments.
- Avoid heredocs for source files; store files on disk and `COPY` them.
- Pin downloaded binaries by version and checksum; avoid `curl | sh`.
- Order Dockerfile layers from stable dependencies to volatile task source.
- Extract copied archives during build and remove the archive in the same stage.
- Avoid broad recursive `chmod -R` or `chown -R`; use `COPY --chmod` or
  `COPY --chown` for targeted metadata.
- Keep `.git`, `.env`, credentials, package caches, build outputs, and
  AI-framework scaffolding filenames such as `CLAUDE.md` or `skills.md` out of
  `environment/`.

For Python tasks, separate project/runtime dependencies from verifier-only
dependencies. Install `pytest`, `pytest-json-ctrf`, and verifier packages in
the Docker image with exact pins.

Narrow exception: local-only installs from preloaded wheels are acceptable when
needed, but they must use `--no-index`, exact versions, and no network. Do not
use this exception to hide an incomplete Dockerfile.

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
Do not add `exit $?` or any trailing exit after the final `fi`: Harbor records
pass/fail from `/logs/verifier/reward.txt`, and the static gate rejects that
extra exit even though the script's own exit code is not the reward signal.

Do not run runtime setup, `apt-get`, `npm install`, or network downloads in
`tests/test.sh`. If `pip install` is unavoidable, it must be local-only from
preloaded wheels with `--no-index` and exact versions.

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
Generate rubrics through the platform UI before reviewer submission: check
"Generate Rubric(s)" while "Send to Reviewer" is unchecked, wait for the
generated rubric, edit it for accuracy, then uncheck "Generate Rubric(s)" before
checking "Send to Reviewer" so the edited rubric is not overwritten.
Rubrics must be trace-focused: non-milestone positive totals should be 10-40
points; each milestone should account for 10-40 positive points; every line
starts with `Agent` and ends with `, +/-N`; allowed values are only 1, 2, 3, or
5; do not use 4; include at least three negative criteria for regular tasks and
at least one negative criterion per milestone.

Quality preflight:

- `codebase_size` is `small` or `large`, not `minimal`
- final runtime base image is sanctioned or explicitly exempt
- no `.ruff_cache`, `.pytest_cache`, `__pycache__`, `.DS_Store`, `._*`, `__MACOSX`, reports, logs, or submissions in the ZIP
- no `tests/` or `solution/` copied into the Docker image
- no runtime dependency setup in `tests/test.sh` unless using a justified
  local-only wheel exception with `--no-index`
- no unverified downloads, `curl | sh`, stale copied archives, broad recursive
  permission rewrites, or cache-hostile Dockerfile layer ordering
- no hidden solution walkthroughs, procedural hints, or prompt-bypass
  instructions in environment files, comments, README, configs, scripts, TODOs,
  `spec.md`, or architecture docs
- oracle passes, nop fails, and failures are behavioral rather than infrastructure
