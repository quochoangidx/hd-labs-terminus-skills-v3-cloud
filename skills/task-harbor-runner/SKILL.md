---
name: task-harbor-runner
description: Use when running, debugging, or triaging Harbor/Terminus commands for a task. Covers oracle, nop, CI checks, LLMaJ/agent runs, Docker daemon failures, build-log feedback, and the rule to follow explicit Harbor/Docker failure instructions before guessing.
---

# Task Harbor Runner

Use this skill after a task folder exists and the user wants to run or debug it.

## Command Order

Prefer this sequence:

```bash
harbor run -a oracle -p <task-folder>
harbor run -a nop -p <task-folder>
harbor tasks check -m openai/@openai/gpt-5.2 <task-folder>
```

Run real agents only when the user approves API usage:

```bash
harbor run -a terminus-2 -m openai/@openai/gpt-5.2 -p <task-folder>
harbor run -a terminus-2 -m anthropic/@anthropic/claude-opus-4-6 -p <task-folder>
```

Use the absolute binary path if PATH is stale:

```bash
/Users/thuongthai/.local/bin/harbor --version
```

Keep Harbor/agent outputs under the ignored workspace:

```text
workspace/reports/
```

When a command supports an output directory, prefer:

```bash
harbor run -a oracle -p <task-folder> -o workspace/reports/<task-slug>/oracle
```

## Failure Discipline

When Docker, Harbor, CI, or LLMaJ emits a specific instruction, follow that instruction first. Do not guess a fix before reading the relevant log section.

Examples:

- If Docker says it cannot connect to the daemon, ask the user to start Docker Desktop or enable the Docker socket.
- If CI says `environment/` is too large, reduce the build context before changing tests.
- If CI says `FROM` lacks a digest, pin the base image digest.
- If CI says the final runtime base is unsanctioned, move the final stage to an
  approved base such as `python:*`, `mcr.microsoft.com/...`,
  `ghcr.io/snorkel-ai/...`, or `scratch`, all digest-pinned, unless the task has
  an explicit exemption.
- If `test.sh` reward block is rejected, make the final reward block match the skeleton literally. Do not add a trailing `exit` after the final `fi`; Harbor reads `/logs/verifier/reward.txt`, not the script exit code.
- If build output names a missing package, add it to Dockerfile build-time deps or preloaded wheels, not verifier-time network fetch.
- If LLMaJ says tests assert behavior not in instructions, update `instruction.md` or remove the test requirement.
- If review flags a missing trailing `exit` in `tests/test.sh`, treat that as stale feedback; the current docs say the canonical reward block ends the script.
- If review flags hidden instructions in environment docs, remove procedural hints from README/spec/config/comments/scripts and keep all task goals in `instruction.md`.

Always quote the shortest useful error excerpt in the handoff.

## Docker Build Context Limits

The Terminus docs define a blocking Dockerfile check:

- `environment/` total size must be `<= 100 MiB`.
- any individual file under `environment/` must be `<= 50 MiB`.

Reason: submitted build contexts must remain cacheable, auditable, and lazy-pull friendly. Large upstream repos must be pruned before submission.

Check with:

```bash
du -sh <task>/environment
find <task>/environment -type f -exec du -h {} + | sort -h | tail
```

## Triage Map

Docker daemon:

- `Cannot connect to the Docker daemon` means Docker Desktop is not running or socket access is blocked.
- On macOS, Docker Desktop Settings -> Advanced -> enable default Docker socket if required.

Dockerfile:

- missing `tmux` causes interactive agent bootstrap failure.
- missing `asciinema` can fail agent runtime.
- `apt-get` in verifier fails when `allow_internet = false`; install deps at image build time.
- `COPY tests/` or `COPY solution/` is a hard failure.

Oracle:

- oracle failure usually means `solution/solve.sh` or tests are wrong.
- verify the patch applies cleanly from the initial state.
- rebuild artifacts if tests invoke a compiled binary.

Nop:

- nop must fail.
- if nop passes, tests are too weak or initial state already satisfies the task.

CI:

- fix high/blocking checks before spending time on real agents.
- run static checks again after each structural edit.

LLMaJ:

- make prompt/tests symmetric.
- remove implementation hints from prompt.
- add docstrings and behavioral assertions.

## Reporting

Report:

- commands run
- pass/fail status
- exact blocker
- files changed to fix it
- next command to run

Do not say a task is ready if Docker/Harbor could not run.
