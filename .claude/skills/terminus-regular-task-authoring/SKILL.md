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

- Set `codebase_size` honestly from useful files in `environment/`.
- Use `minimal` for roughly 0-19 useful files, `small` for roughly 20-199
  useful files, and `large` for roughly 200+ useful files.
- `minimal`, `small`, and `large` are all accepted; aim for a portfolio mix
  instead of padding or pruning solely to hit one size.
- `languages` lists the main language(s) used by the task/oracle changes. Do
  not include Python solely because verifier tests are written in pytest.

## Prompt Rules

`instruction.md` should:

- Be short and human-styled.
- State observable behavior, not implementation hints.
- Mention all required paths and output files.
- Avoid issue URLs, PR numbers, exact test names, canaries, and rubrics.
- Include enough edge-case requirements that tests are fair.
- Apply the real-user prompt test to every sentence: would a developer who did
  not already know the solution naturally include this detail? If not, it is
  probably a hint rather than a requirement.
- Do not narrate the internal mechanism or root cause (the #1 client reject,
  June 2026 trial feedback). Describe the observable symptom and the desired
  outcome, not how the code is wrong inside. Cut "Right now the parser does X
  internally" sentences (state what is observed instead), "the other path
  already handles it" tells (they point at where to copy the fix), and
  fix-shaped requirements that restate the implementation (state them
  behaviorally). KEEP test-asserted spec contracts even when specific
  (thresholds, public API the tests drive, preservation/edge cases) so
  instruction/test symmetry still holds.

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
- distinguish two kinds of things a test can pin (docs: prompt-styling.md gives
  the what not the how; `behavior_in_task_description` + `structured_data_schema`
  want asserted behavior and output schemas explicit; prompt-styling section 4
  "Overly Prescriptive Guidelines" calls listing exact function signatures /
  struct layouts BAD):
  - VALUES the test asserts (numeric thresholds, output keys, JSON/CSV/data
    schema the agent produces, exact-match constants) MUST be explicit. Omitting
    a tested cutoff makes agents guess and fail unfairly; this is required
    sufficiency, not over-spec.
  - CODE IDENTIFIERS the test pins (function signatures, struct field
    names/types, project layout the agent must produce) are exactly what
    prompt-styling section 4 forbids prescribing. Do NOT resolve a compile-time
    name mismatch by pasting a struct schema or signature list into the prompt
    (that is the "reads like a design document" failure). Resolve it by making
    the verifier BEHAVIORAL/OPAQUE: drive observable output and pass any new
    value straight back into the API as a black box, so the test never reads
    its fields and the instruction can say "you choose its fields." That often
    means the API owns more of the protocol (e.g. a resume option takes the
    full input and seeks internally rather than the caller slicing by a field).
    Only when a brand-new exported symbol genuinely cannot be made behavioral,
    name that single symbol minimally (a new type/function the test must call by
    that exact name) and nothing more; never its field schema.

Common quality-check failure: a test asserts that unaffected modes such as `prepend`/`append`, non-editable installs, normal parsers, or legacy fallbacks still work, but `instruction.md` only describes the target mode. Fix by adding one natural sentence like "Keep `<mode A>` and `<mode B>` behavior unchanged for the same layout" or remove that preservation test.

## Docker Rules

`environment/Dockerfile` must:

- Use `FROM ...@sha256:<digest>` on every stage.
- Use a **canonical Terminal-Bench base image** for the final runtime stage when
  one matches the task's language (all under `public.ecr.aws/docker/library/`,
  exact digest required): `python:3.13-slim-bookworm@sha256:01f4…24fb`,
  `node:22-bookworm-slim@sha256:f3a6…2383`, `golang:1.24-bookworm@sha256:1a6d…77ac`,
  `rust:1.85-slim@sha256:9f84…cb36`, `eclipse-temurin:21-jdk-jammy@sha256:25d1…4b14`,
  `gcc:13-bookworm@sha256:930f…ac5c`, `ruby:3.3-slim-bookworm@sha256:e767…e3df`,
  `maven:3.9.9-eclipse-temurin-21@sha256:3a4a…211e`, `debian:bookworm-slim@sha256:4724…655d`,
  `ubuntu:24.04@sha256:0d39…e932`. (Full digests live in `docs/creating-tasks/dockerfile-best-practices.md`.)
  A non-canonical base is allowed only with a brief, credible justification in the
  `Dockerfile` or task `README.md`; missing/vague justification is blocked.
- Install `tmux` and `asciinema`.
- For cloned-repo tasks, `git init` the task workdir after the final source
  `COPY` (`RUN git init -q && git config user.email task@example.com && git
  config user.name task && git add -A && git commit -q -m "initial task
  state"`). Agents often apply edits via `git apply` and self-check with `git
  diff`; if `/app` is not a git repo (cloned `.git` stripped, and excluded from
  the build context), patches silently fail to land and otherwise-correct agents
  score 0 ("Some tests not passed by any agent run"). Runs in the image, so it
  does not trip the `.git`-in-context hygiene warning; oracle/nop unaffected.
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

Do not put verifier dependency wheels in `tests/`. The `tests/` directory should
contain verifier scripts and fixtures only; install verifier dependencies during
Docker build.

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
- for floating-point or irrational NUMERIC results, assert an accuracy
  tolerance (`|got - trueRef| <= tol`) instead of exact string equality. Exact
  matching forces agents to reproduce one implementation's undocumented
  rounding (often a float64 artifact that is LESS correct than the true value),
  so a more-accurate agent fails unfairly. Pick `tol` so the oracle's own output
  clears it and a naive/buggy impl misses by orders of magnitude; for a
  `precision`-parameterised API set `tol` to that floor (precision=10 -> 1e-10).
  Keep exact string match only for genuinely exact results (integer powers,
  defined truncations, edge-case zero/error)
- when the instruction mandates a REFACTOR of an EXISTING interface/signature
  (not just new behavior), behavioral tests alone let an agent add a parallel
  interface and skip the refactor. Add two guards: (a) a compile-time
  interface-satisfaction assertion (`var _ pkg.Interface = (*Probe)(nil)` where
  `Probe` has the new method signature) so the verifier only compiles if the
  EXISTING interface was actually changed; this checks a public type-system
  contract the instruction requires, not private implementation; and (b) a
  separate `go build ./...` test, since `go test ./_verifier_test/` compiles
  only transitively-imported packages, not sibling subpackages with their own
  call sites of the changed interface
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
Do not add `exit $?` or any trailing exit after the final `fi`: Harbor records
pass/fail from `/logs/verifier/reward.txt`; the script's own exit code is not
the reward signal.

Do not run runtime setup, `apt-get`, `npm install`, or network downloads in
`tests/test.sh`. Bake verifier dependencies into the Docker image; `test.sh`
should run the verifier and write `/logs/verifier/reward.txt`, not install
packages.

## Oracle Rules

`solution/solve.sh` must:

- Start with `set -euo pipefail`.
- Be deterministic and self-contained.
- Avoid network access.
- Apply a real fix, not write hardcoded expected outputs.
- Contain ONLY the hunks relevant to the task. When the patch is generated from
  an upstream PR or a multi-concern diff, strip every file/hunk unrelated to the
  stated instruction (a separator fix should not also bundle a regexp/string
  refactor). Bundled changes create a hidden requirement that widens the agent's
  scope beyond instruction.md and misaligns the oracle with the goal (review
  flags "Solution Patch Contains Unrelated Changes"). After stripping, confirm
  the build step in `solve.sh` still passes; if an unrelated hunk turns out to
  be load-bearing for the build, that is a signal the snapshot is inconsistent,
  not a reason to keep the refactor.
- Rebuild or regenerate artifacts when the verifier invokes a built binary.

## Final Checks

Run, when available:

```bash
harbor run -a oracle -p <task-folder>
harbor run -a nop -p <task-folder>
harbor tasks check -m openai/@openai/gpt-5.5 <task-folder>
```

For submission ZIPs, compress the contents of the task folder, not the folder itself.
Generate rubrics through the platform UI before reviewer submission: check
"Generate Rubric(s)" while "Send to Reviewer" is unchecked, wait for the
generated rubric, edit it for accuracy, then uncheck "Generate Rubric(s)" before
checking "Send to Reviewer" so the edited rubric is not overwritten.
Rubrics must be trace-focused. Every criterion line starts with `Agent` and
ends with `, +/-N`; allowed values are only 1, 2, 3, or 5; do not use 4.
Non-milestone rubrics should be a flat list of `Agent ...` criteria; a single
`# Rubric 1` header is tolerated but not required, and `# Rubric 2+` is reserved
for milestone tasks. Milestone rubrics must use one block per milestone:
`# Rubric 1`, `# Rubric 2`, etc. Non-milestone positive totals should be 10-40
points, and each milestone should account for 10-40 positive points. Include at
least three negative criteria overall; for milestone tasks, also include at
least one negative criterion per milestone.
Rubrics must describe observable agent behavior during the solve. Do not
reference tests, verifier logic, `test.sh`, `test_outputs.py`, `/tests/`,
hidden tests, CI, reward files, pytest, or final test results.

Quality preflight:

- `codebase_size` matches the useful environment file count and portfolio mix
- `languages` excludes verifier-only Python
- no root-level `pyproject.toml`
- final runtime base image is canonical for the task's language (or non-canonical with a credible justification)
- no `.ruff_cache`, `.pytest_cache`, `__pycache__`, `.DS_Store`, `._*`, `__MACOSX`, reports, logs, or submissions in the ZIP
- no dependency wheels in `tests/`
- no `tests/` or `solution/` copied into the Docker image
- no `privileged: true`, no `SYS_ADMIN`/`NET_ADMIN`/`SYS_MODULE` capabilities,
  no `/var/run/docker.sock` mounts; compose volume mounts must not shadow the
  reserved paths `/logs/artifacts`, `/logs/verifier`, `/tests`, `/solution`
- no runtime dependency setup in `tests/test.sh`
- no rubric or instruction references to tests, verifier logic, `test.sh`,
  `test_outputs.py`, `/tests/`, hidden tests, CI, reward files, pytest, or final
  test results
- no unverified downloads, `curl | sh`, stale copied archives, broad recursive
  permission rewrites, or cache-hostile Dockerfile layer ordering
- no hidden solution walkthroughs, procedural hints, or prompt-bypass
  instructions in environment files, comments, README, configs, scripts, TODOs,
  `spec.md`, or architecture docs
- oracle passes, nop fails, and failures are behavioral rather than infrastructure
