---
name: task-harbor-runner
description: Use when running, debugging, or triaging Harbor/Terminus commands for a task. Covers oracle, nop, CI checks, LLMaJ/agent runs, Docker daemon failures, build-log feedback, and the rule to follow explicit Harbor/Docker failure instructions before guessing.
---

# Task Harbor Runner

Use this skill after a task folder exists and the user wants to run or debug it.

## Command Order

Prefer this sequence (CLI surface verified 2026-06-24; mind the version skew —
bare `harbor` is 0.5.0 while the stb-bundled one is 0.7.0, and `harbor tasks
check` was REMOVED in 0.7.0):

```bash
harbor run -a oracle -p <task-folder>
harbor run -a nop -p <task-folder>
stb harbor check <task-folder>          # replaces the removed `harbor tasks check`
```

Run real agents only when the user approves API usage. `-a` DEFAULTS TO ORACLE —
always pass the agent explicitly, and the agent name is `terminus-2` (not
`terminus`); models are Portkey `@provider/model` slugs:

```bash
stb harbor run -a terminus-2 -m @openai/gpt-5.5 -k 3 -p <task-folder>
stb harbor run -a terminus-2 -m @anthropic/claude-opus-4-8 -k 3 -p <task-folder>
```

Known INFRA failures — do not treat these as task defects:

- `stb harbor check` dying with an `openrouter` API-key error is the check
  harness, not the task. Fall back to Docker oracle/nop plus a blind solve
  probe (`task-local-solve-probe`); the platform check at submit stays the
  source of truth.
- From VN both providers geo-block direct API calls (OpenAI 403 country /
  Anthropic not-allowed) — no VPN/remote access is available; these calls
  only ever run at platform submission time. Locally, substitute
  fresh-subagent probes (`task-local-solve-probe`) and never rewrite the
  task in response to the geoblock.

Use the absolute binary path if PATH is stale:

```bash
"$HOME/.local/bin/harbor" --version
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
- If CI says the final runtime base is non-canonical (`check_sanctioned_base_images`),
  switch the final stage to the **canonical Terminal-Bench base image** for the
  task's language, using the EXACT digest-pinned ref (registry + tag + digest all
  matter — a bare `golang@sha256:<other>` or a different registry is blocked even
  though it's "official"). Canonical refs (all under `public.ecr.aws/docker/library/`):
  - Python `python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
  - Node `node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383`
  - Go `golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac`
  - Rust `rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36`
  - Java `eclipse-temurin:21-jdk-jammy@sha256:25d1276565738d3c805e632a4542c3a7598866ef967f4def6544c15de3a74b14`
  - GCC `gcc:13-bookworm@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c`
  - Ruby `ruby:3.3-slim-bookworm@sha256:e76733e94b3a5893e4a141024ef3a583dc10781dc24becebf74f9c9f9a33e3df`
  - Maven `maven:3.9.9-eclipse-temurin-21@sha256:3a4ab3276a087bf276f79cae96b1af04f53731bec53fb2e651aca79e4b10211e`
  - Debian `debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d`
  - Ubuntu `ubuntu:24.04@sha256:0d39fcc8335d6d74d5502f6df2d30119ff4790ebbb60b364818d5112d9e3e932`

  If the task genuinely needs a base off this list, keep it but add a brief,
  credible justification (Dockerfile comment or task `README.md`); missing/vague
  justification — or one that matches a canonical entry — is blocked. Builder
  stages are unrestricted.
- The `build toolchain in runtime image` (`make_build`/compile in a single
  stage) finding is a NON-BLOCKING warning with an explicit carve-out for
  debugging/rebuild tasks whose verifier re-runs the build. Keep the
  single-stage Dockerfile; do NOT split to multi-stage (the agent needs the
  toolchain at runtime to rebuild after editing).
- A `pip install`/`npm install` without a lockfile next to it is a NON-BLOCKING
  warning; inline `==` pins are accepted. Add a lockfile only to silence it.
- If CI `ruff` fails on an upstream `.py` under `environment/repo`, the platform
  lints the whole task dir; delete non-build-required dev scripts or fix
  build-required ones in place (see `upstream-repo-sanitizer`).
- If `test.sh` reward block is rejected, use the current canonical reward
  ending: run pytest, immediately capture `rc=$?` or branch on `$?`, write
  `/logs/verifier/reward.txt`, and do not add a trailing `exit` after the final
  `fi`. Harbor reads `/logs/verifier/reward.txt`, not the script exit code.
- If build output names a missing package, add it to Dockerfile build-time or verifier dependency installation. Do not move dependency setup into `tests/test.sh` or bundle dependency wheels under `tests/`.
- If LLMaJ says tests assert behavior not in instructions, update `instruction.md` or remove the test requirement.
- If review flags a missing trailing `exit` in `tests/test.sh`, treat that as stale feedback; the current docs say the canonical reward block ends the script.
- If review flags hidden instructions in environment docs, remove procedural hints from README/spec/config/comments/scripts and keep all task goals in `instruction.md`.

- **Platform "Oracle failed" while local harbor+docker are GREEN ⇒ suspect
  noexec `/tmp` FIRST.** The platform mounts `/tmp` noexec; any verifier that
  stages a binary — or a `#!/bin/sh` wrapper script — under bare
  `tempfile.mkdtemp()` and then execs it dies with `PermissionError`/EACCES,
  every test errors, and the oracle fails invisibly (local `/tmp` is exec).
  Repro exactly with `docker run --tmpfs /tmp:noexec,nosuid,size=256m …`
  (fails) vs without the flag (passes). Fix = a `_find_exec_base()` that
  probes `[/app, /var/tmp, /dev/shm, gettempdir()]` by writing+running a tiny
  `#!/bin/sh` script and passes the winner as `dir=` to every `mkdtemp`; for
  interpreter wrappers, yield an argv prefix (`["node", main_js]`,
  `["java", "-cp", classes, "Main"]`) instead of a staged executable —
  interpreters read code fine from a noexec mount. `scripts/preflight.sh`
  (repo root) now runs the noexec-/tmp oracle repro; validate every fix with
  oracle=1 AND nop=0 under the `--tmpfs` flag.
- **"Oracle failed" on a byte-identical locally-green artifact = stale
  PLATFORM image** → fresh repackage + force-build. Repeated staleness means
  content-hash caching — make a real difficulty-neutral content change (e.g.
  trim a verifier loop) to bust it.
- If oracle suddenly fails with a `[build failed] undefined: <symbol>` from the
  verifier AND `agent/oracle.txt` is empty, suspect a STALE cached Docker image:
  Harbor does not reliably rebuild when `environment/repo` or `solution/fix.patch`
  change on disk. Re-run with `harbor run --force-build -a oracle -p <task>` (and
  for nop). Do not chase the "undefined symbol" as a patch/code bug until you
  have force-built. To get ground truth without Harbor, build the image and run
  the real flow in one container: `docker build -t dbg environment/ && docker run
  --rm -v "$PWD/<task>/solution:/solution:ro" -v "$PWD/<task>/tests:/tests:ro"
  dbg bash -c 'set -e; bash /solution/solve.sh; bash /tests/test.sh; cat
  /logs/verifier/reward.txt'`.

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

- missing `tmux` causes interactive agent bootstrap failure. On a raw non-tb
  base image (e.g. `rust:1.85-slim`) EVERY agent run dies at setup — the
  harness builds tmux from source and hits the 360s `AgentSetupTimeoutError` —
  and the platform report disguises it as external "tmux-build-timeout" infra
  plus a spurious HARD verdict. Fingerprint: `verifier_did_not_run: N/N` +
  oracle passes + nop fails = contaminated signal, NOT difficulty. Fix:
  apt-install `tmux` + `asciinema` in the Dockerfile, re-verify oracle=1/nop=0,
  re-zip. Mandatory check whenever the base image is not a tb-canonical one.
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

Real agents / Agent Timeout Gate:

- `Agent Timeout Gate: ❌ N/10 real-agent runs timed out (threshold: 5)` is a
  hard blocker, not a difficulty signal. It means the environment is too heavy:
  agents spend the 1800s budget on cold rebuilds, navigating an un-slimmed repo,
  or a slow test suite, and never converge.
- Pre-check WITHOUT spending agent budget: build once, then `time harbor run -a
  oracle -p <task-folder>` against the cached image. The cached-image oracle run
  approximates one agent edit→build→test cycle; if it is a large fraction of
  1800s, agents will time out.
- Fix the environment, do not just raise the timeout (capped at 1800): warm the
  build in the Dockerfile so rebuilds are incremental, keep the build/dependency
  cache in the final image, slim the repo, and shrink the verifier. See the
  `task-clone` "Agent Timeout Gate" section.

## Reporting

Report:

- commands run
- pass/fail status
- exact blocker
- files changed to fix it
- next command to run

Do not say a task is ready if Docker/Harbor could not run.
