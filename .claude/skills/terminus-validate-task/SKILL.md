---
name: terminus-validate-task
description: Pre-submit audit for a Terminus Edition 2 / Snorkel Expert Platform task. Runs the same family of checks the platform CI + LLMaJ would run (structural, Dockerfile, oracle, tests, instruction.md, optional pass-rate sanity), so the task is unlikely to bounce back from `Send to Reviewer`. Use AFTER `terminus-create-task` (or any hand-edited task) and BEFORE zipping for upload. Different from `validate-task` (the in-house tb-quality Phase 1 + Phase 2 pipeline aimed at the autorun loop) — this skill is platform-shaped and reports against Snorkel's High/Medium/Low severity criteria from `docs/reviewing-tasks/reviewer-checklist.md`.
---

# Terminus Validate Task

Audit a Terminus Edition 2 task against the Snorkel platform's submission contract before upload. Specs live in `docs/` (local mirror of https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/).

## Authoritative skeletons (compare-against reference)

The official Snorkel-portal task skeletons live at `/Users/trung/develop/terminus/task_skeleton/`:

- [task_skeleton/regular/](../../../task_skeleton/regular/) — non-milestone (Python pytest)
- [task_skeleton/milestone/milestone_template/](../../../task_skeleton/milestone/milestone_template/) — 2-milestone
- [task_skeleton/ui/](../../../task_skeleton/ui/) — UI-building (Vitest + Playwright)

The structural checks below are the **shape contract these skeletons define**. When a check ambiguously flags or accepts something, **read the matching skeleton file** to decide. The current `check_test_sh` gate accepts both `if [ $? -eq 0 ]` immediately after pytest and the preferred defensive `rc=$?` variable captured immediately after pytest.

## API keys / `.env`

Steps 6 (LLMaJ judge) and 7 (`--with-agent`) need API keys. They are loaded
from a single file: **`/Users/trung/develop/terminus/.env`** (passed to
`harbor` via `--env-file`, or auto-loaded from the working directory).

Expected variables:
- `ANTHROPIC_API_KEY` — for the Sonnet judge in Step 6 (LLMaJ).
- `OPENAI_API_KEY` — for the codex agent in Step 7 (Portkey-routed; this is your Snorkel-issued Portkey key, not a raw OpenAI key).
- `JUDGE_MODEL`, `LLM_PROVIDER`, `LLM_MODEL` — routing config consumed by `harbor`.

Steps 1–5 do NOT need any API keys (oracle and nop runs are local Docker only).
If `.env` is missing, the skill still runs Steps 1–5 and emits a HIGH finding
for Steps 6–7 telling the user to recreate `.env` (e.g. by copying from
`/Users/trung/develop/tb-quality/.env`).

Never `source .env` into the shell — let `harbor` consume it via `--env-file`
so the values stay scoped to that one subprocess. `.env` is git-ignored.

## Cross-repo dependency

Steps 2–7 shell out to the `harbor` binary (`harbor task check`, `harbor run -a oracle`, `harbor run -a nop`, `harbor check -m sonnet`, optional `harbor run -a codex`) and to the `tb_quality check-b4` offline scan. Both live in the sibling repo's venv at `/Users/trung/develop/tb-quality/.venv/`.

These tools are the **same `harbor` binary the official Snorkel docs reference** (`docs/testing-and-validation/{ci-feedback-training,oracle-agent,nop-agent,llmaj-checks-reference,running-real-agents}.md`); the only repo-local addition is `tb_quality check-b4` for the offline B4 anti-gaming scan (Step 2). Without the venv, each affected step emits a HIGH "tooling-missing" finding and the skill continues with what it can (Step 1 structural checks still produce useful findings regardless).

To make this repo self-sufficient, install `terminalbench-harbor` and the
`tb_quality` package into a local `.venv/` here and rewrite the
`/Users/trung/develop/tb-quality/.venv/bin/...` paths in Step 2–7 to
`./.venv/bin/...`.

## Inputs

- **TASK_DIR** (required): absolute or repo-relative path to the task root. Resolves to a folder containing either `instruction.md` (non-milestone) or `steps/milestone_*/` (milestone).
- Optional flag the user can pass:
  - `--with-agent` — additionally kick off `harbor run -a codex` k=2 to estimate pass-rate (very slow + costs real API money, opt-in only).

## Default run profile (always-on, matches Snorkel docs)

When the user says "validate task X", this skill **always runs the full pre-submit audit per the official Snorkel docs** (`docs/testing-and-validation/`):

1. **Structural checks** (Step 1) — file shape, task.toml schema, instruction.md style, Dockerfile rules, solve.sh, test.sh, test_outputs.py, anti-cheating, repo hygiene. Free, ~seconds.
2. **B4 offline scan** (Step 2) — fast static scan via `tb_quality check-b4` (the only `tb_quality` invocation; it's an offline regex pass, not a Docker run). Free, ~seconds.
3. **CI quality checks** (Step 3) — `harbor task check <task_dir>`. Catches the 12 CI checks documented in `docs/testing-and-validation/ci-checks-reference.md` (pinned_dependencies, validate_task_fields, check_task_absolute_path, ruff, etc.). Free, ~seconds.
4. **Oracle run** (Step 4) — `harbor run -a oracle -p <task_dir>`. Builds the image and verifies the oracle solution passes. **~5 min, free** (local Docker only).
5. **Nop baseline** (Step 5) — `harbor run -a nop -p <task_dir>`. Must FAIL — if it passes, the tests are too lax (agent can do nothing and still win). **~1 min, free**.
6. **LLMaJ judge** (Step 6) — `harbor check <task_dir> -m sonnet`. Runs the 7 LLMaJ checks documented in `docs/testing-and-validation/llmaj-checks-reference.md` (behavior_in_tests, anti_cheating_measures, hardcoded_solution, …). **~1 min, costs API (small).**

There is no flag to disable any of these — they are the official Snorkel pre-submit audit. If the `harbor` binary is missing the affected steps emit a HIGH "tooling-missing" finding and the skill continues with the remaining steps.

Only Step 7 (`--with-agent`, k=2 codex pass-rate sanity using the `stb harbor run -m @openai/gpt-5.2` real-agent flow from `docs/testing-and-validation/running-real-agents.md`) is opt-in, because it's slow (~10-20 min) and costs real API money.

## What this skill is NOT

- Not the autorun pipeline (that's `validate-task` / `python -m tb_quality validate`).
- Not a code review of the task's logic — it checks the *contract*, not whether the problem is interesting.
- Not a rubric authoring tool — rubrics live in the Snorkel UI, not in the repo.

---

## Step 0 — Locate and identify the task

```bash
TASK_DIR="$1"                              # whatever the user passed
[ -d "$TASK_DIR" ] || { echo "no such dir"; exit 1; }
cd "$TASK_DIR"
TASK_SLUG=$(basename "$PWD")
```

Detect milestone vs non-milestone:

```bash
if [ -d steps ]; then KIND=milestone; else KIND=nonms; fi
```

Read `task.toml` once and extract: `category`, `subcategories`, `difficulty`, `number_of_milestones`, `codebase_size`, `languages`, `tags`, `custom_docker_compose`, `is_multi_container`. (Use Python `tomllib` via Bash if needed.)

Cross-check: `number_of_milestones == count(steps/milestone_*)` for milestone tasks; `== 0` for non-milestone tasks.

---

## Step 1 — Structural checks (always run)

Build a finding list. Each finding has: `severity` (HIGH | MED | LOW), `area`, `path`, `message`.

### 1a. Required files

**Non-milestone** must have all of:
- `task.toml`, `instruction.md`, `environment/Dockerfile` (or `environment/docker-compose.yaml`),
  `solution/solve.sh`, `tests/test.sh`, `tests/test_outputs.py`.

**Non-milestone + `ui_building` subcategory** — DIFFERENT shape (mirrors [task_skeleton/ui/](../../../task_skeleton/ui/)):
- `task.toml`, `instruction.md`, `environment/Dockerfile`, `solution/solve.sh`, `tests/test.sh`
- `tests/package.json`, `tests/playwright.config.ts`, `tests/vitest.config.ts`
- At least one spec under `tests/unit/*.spec.ts` AND at least one under `tests/e2e/*.spec.ts`
- `tests/test_outputs.py` is NOT required (and typically absent) for UI tasks — pytest not used.
- HIGH if any of the above JS test-stack files are missing for a UI task.

**Milestone** must have:
- `task.toml`, `environment/Dockerfile`, and for each milestone N (1..number_of_milestones):
  `steps/milestone_N/instruction.md`,
  `steps/milestone_N/tests/test.sh`,
  `steps/milestone_N/tests/test_mN.py`,
  `steps/milestone_N/solution/solve.sh`,
  `steps/milestone_N/solution/solveN.sh`.
- And must NOT have: root-level `instruction.md`, `tests/`, `solution/`, or any `milestone_*.md`.

Missing files → HIGH. Forbidden root files in milestone task → HIGH.

### 1b. `task.toml` schema

Required `[metadata]` keys (HIGH if missing):
`author_name, author_email, category, subcategories, difficulty, codebase_size,
number_of_milestones, languages, tags, expert_time_estimate_min, junior_time_estimate_min`.

- **HIGH — HARD BLOCKER (per `docs/understanding-tasks/task-taxonomy.md`)**: `category` MUST be exactly one of the **nine fixed taxonomy values** (no other strings accepted — no free-text, no Edition-1 labels like `feature`/`fix`/`bug`, no capitalized variants, no compound combinations):
  1. `system-administration`
  2. `build-and-dependency-management`
  3. `data-processing`
  4. `games`
  5. `software-engineering`
  6. `machine-learning`
  7. `debugging`
  8. `security` (lowercase — docs heading writes "Security" but `task.toml` value must be lowercase, per skeleton `task_skeleton/regular/task.toml`)
  9. `scientific-computing`

  All values are lowercase kebab-case. Snorkel's `validate_task_fields` CI rejects anything else with `category not in allowed set`. **There is no "Other" / "custom" / "domain-specific" category** — if the task doesn't fit one of the nine, the task itself doesn't fit the benchmark (redesign the scope, don't invent a new label). No platform restriction on *which* of the nine to pick (per `diversity-requirements.md`); the dataset-level distribution guideline (no single category > ~30%, ≥ 4 categories ≥ 10%) is informational only, not a per-submission gate. Detection: `python3 -c "import tomllib; t=tomllib.load(open('task.toml','rb')); assert t['metadata']['category'] in {'system-administration','build-and-dependency-management','data-processing','games','software-engineering','machine-learning','debugging','security','scientific-computing'}, t['metadata']['category']"`.

- **HIGH — HARD BLOCKER**: each entry in `subcategories` MUST be from the fixed set of **five subtype values** (per `docs/understanding-tasks/task-subtypes.md`), all lowercase snake_case:
  1. `long_context` (≥50k-token semantic doc required)
  2. `tool_specific` (target SDK/API where models underperform)
  3. `api_integration` (build/interact with/debug mocked APIs, no live network)
  4. `db_interaction` (SQL/NoSQL/Vector/In-Memory DBs)
  5. `ui_building` (Playwright-tested UI tasks)

  Empty list `[]` is fine (no subcategory required). Any other string fails `validate_task_fields`.

- LOW (category-mismatch heuristic): instruction.md primary activity doesn't match the declared category. Rough heuristic (won't catch all): a `data-processing` task should mention parsing/transforming/aggregating; a `debugging` task should mention a failing test / crash / wrong-output symptom; a `machine-learning` task should touch model training/inference. Mismatches are common reviewer-rejection reasons.
- Each `subcategories` entry ∈ {long_context, tool_specific, api_integration, db_interaction, ui_building} → MED. (No platform restriction on which.)
- `difficulty` ∈ {easy, medium, hard} → HIGH if not in set.
- **Diversity gate — `difficulty = "easy"` → HIGH.** Auto-blocked by Snorkel's pre-submit diversity eval (`diversity-requirements.md`). Only `medium` / `hard` accepted for brand-new submissions.
- `codebase_size` ∈ {minimal, small, large} → MED if literal value is something else entirely.
- **Empirical codebase_size mismatch → HIGH.** Snorkel CI counts files under `environment/` (excluding `Dockerfile`, `docker-compose.yaml`, and `docker-compose.yml`) and compares to the declared `codebase_size`:
  - 0–19 files → expected `minimal`;
  - 20–199 files → expected `small`;
  - ≥ 200 files → expected `large`.
  If the declared value disagrees with the empirical count, CI emits: `codebase_size is '<declared>' but environment/ has N files`, which is HIGH. Implementation: `find environment -type f | grep -vE '^environment/(Dockerfile|docker-compose\.ya?ml)$' | wc -l`. `minimal`, `small`, and `large` are all accepted; keep the value honest and vary size across the portfolio.
- **Diversity gate — Python primary + `difficulty != "hard"` → HIGH.** If `"python"` is a task/oracle implementation language and `difficulty` is not `"hard"`, auto-blocked. Do not include Python in `languages` solely because verifier tests are written in pytest.
- `len(tags)` between 3 and 6 → LOW outside that range.
- `number_of_milestones`: 0 for non-ms, ≥ 2 for ms (1 milestone is invalid). HIGH if violated. Note: non-ms is allowed but ms is *preferred* (higher pay) per `diversity-requirements.md` — LOW info if `number_of_milestones == 0`.

Required blocks:
- Non-ms: `[verifier].timeout_sec`, `[agent].timeout_sec`, `[environment].{build_timeout_sec, cpus, memory_mb, storage_mb}`. HIGH if missing.
- **HIGH — REQUIRED FIELD (added by Snorkel CI ~2026-05-20)**: `[environment].allow_internet` must be present. Value must be `false` for almost all tasks (the platform's quality-guidelines forbid network access; only specific approved cases allow `true`). Missing the field → CI fails with `Missing required field: environment.allow_internet (must be false)`. Detect via tomllib: `t["environment"].get("allow_internet")` must exist and be `false`.
- **HIGH — `allow_internet = false` ↔ test.sh / Dockerfile must work OFFLINE**: when `allow_internet = false`, the verifier container has NO outbound network. `tests/test.sh` must not run `curl|wget`, `apt-get`, `pip install`, `npm install`, or `uvx` that fetches dependencies. Install `pytest`, `pytest-json-ctrf`, and verifier-only dependencies in the Dockerfile with exact pins, then use system Python in `tests/test.sh`.

- **HIGH — Dockerfile MUST pre-install `tmux` + `bash` + `util-linux` for the agent harness**: Snorkel's `terminus-2` (and other interactive) agents bootstrap by attaching a tmux session inside the container. With `allow_internet = false` the bootstrap cannot `apt-get install tmux` at runtime, so the agent fails before ever generating code with the cryptic error:

  ```
  RuntimeError: Failed to start tmux session. Error: None
  ```

  The agent then scores 0/N across all trials — but this is a TASK ENVIRONMENT FAILURE, not the agent solving incorrectly. The reviewer report explicitly flags this as "Fail ở build môi trường cho agent, dẫn tới agent chưa thực sự sinh dòng code nào". Detect: `grep -E 'apt-get install[^\n]*tmux' environment/Dockerfile` must match. Mitigation: add to the existing `apt-get install -y --no-install-recommends \` block at the top of the Dockerfile:
  ```dockerfile
  RUN apt-get update && apt-get install -y --no-install-recommends \
      bash \
      ca-certificates \
      curl \
      ...
      tmux \
      util-linux \
      && rm -rf /var/lib/apt/lists/*
  ```
  Oracle runs (which DO NOT use the agent harness) will still pass without tmux — so passing oracle is NOT sufficient evidence that the task works for agents. Always sanity-check with `harbor run -a terminus-2 -m gpt-5.2 -k 1` before submitting.
- Ms: NO root `[verifier]`/`[agent]`. `[environment]` required. One `[[steps]]` per milestone, each with `[steps.agent].timeout_sec` + `[steps.verifier].timeout_sec`, and `name = "milestone_N"` matching the directory. HIGH if violated.

If `environment/docker-compose.yaml` exists:
- `custom_docker_compose = true` must be in `[metadata]` → HIGH if missing.
- If compose has ≥ 2 `services:` entries, also `is_multi_container = true` → HIGH if missing.

### 1c. `instruction.md` checks (per file — root for non-ms, each `steps/milestone_N/instruction.md` for ms)

- **HIGH (CI `check_task_absolute_path`)**: contains a relative path that *looks like* it points to a task file (matches `(^|\s)\.?\.?/?[a-z][\w/.-]+\.(py|sh|json|csv|txt|md|yaml|yml|toml)\b` AND not preceded by `/`). Tolerate inline code without paths. Suggest: prefix with `/app/`. Per `docs/testing-and-validation/ci-checks-reference.md#check_task_absolute_path`.
- HIGH: mentions `solution/`, `tests/`, `task.toml`, `solve.sh`, `test_outputs.py`, `rubric`, `milestone` (literal — agent must not see these terms).
- MED: contains the literal task slug (`$TASK_SLUG`) as a word.
- MED: contains a canary string. Pattern: `BENCHMARK DATA SHOULD NEVER APPEAR` or any 32-hex-char run that looks UUID-ish (`[0-9a-f]{32}` or `[0-9a-f]{8}-[0-9a-f]{4}`...).
- MED: file longer than ~3 paragraphs (≈ 25 non-empty lines or ≈ 400 words). Encourage trimming.
- LOW: contains 5+ `**bold**` markers — likely highlighting answer values, GPT-style.
- LOW: starts with `# Task:` / `# <slug>` style heading echoing the slug.
- LOW: contains emoji (regex `[\U0001F300-\U0001FAFF\U00002600-\U000027BF]`) — Snorkel guideline says no emoji.
- For milestone task, MED if `steps/milestone_1/instruction.md` is < ~5 lines (it should also include overall task context, not only the M1 delta).
- **MED (LLMaJ `instruction_check`)**: instruction reads as a "detailed implementation guide" — Snorkel's LLM judge (CI uses `claude-haiku-4-5`) flags instructions that prescribe step-by-step file edits, exact function signatures, exact line-by-line code patterns, or "Add X to file Y / Change function Z to accept parameter W" language. The reviewer's framing is **"state the problem, not the solution"** — instruction must read like a real bug report or feature request that a human engineer would receive, NOT a step-by-step tutorial walking the agent through every edit.

  Three concrete reviewer-stated requirements the instruction must meet (per repeated CI feedback):
  1. **Fewer than ~20 hard requirements**. Count every "must X" / "should X" / numbered enumeration item / explicit MUST list — if it crosses ~20, the instruction is over-specified. Consolidate or move details to the test contract.
  2. **Sound natural and human**. No "must X, must Y, must Z" rapid-fire enumeration; no chains of imperative bullets that look generated. Narrative paragraphs ("the package lives in...", "this approach uses...") read more human than bullet checklists.
  3. **No unnecessary hints; do not reveal the solution**. Drop concrete syntax patterns (e.g. `cy.compiles(...)`, `from X cimport Y`, `ctypedef int foo` fallback, specific regex patterns, exact dict keys for internal-only state). Keep only what the test will literally assert (exact public API names, exact constant strings, exact error messages, exact file paths) and the problem framing.

  Reference example of the right style: [task_release/sklearn-polars-no-interchange/instruction.md](../../../task_release/sklearn-polars-no-interchange/instruction.md) — 3 paragraphs: ¶1 frames the problem (Polars 1.40 deprecated `__dataframe__`, sklearn still routes through it), ¶2 lists the public behaviors that must match pandas paths + one explicit error message string + the negative constraint (must NOT invoke `__dataframe__`), ¶3 lists the four files allowed to be edited. No function signatures, no code snippets, no "add X here, change Y there".

  Heuristic flags to apply locally before submission:
  - Contains > 3 procedural verbs in imperative form pointing at specific code locations: "Add", "Change", "Rename", "Update", "Insert", "Replace", "Remove" followed by `/app/...` or "in `<filename>`".
  - Contains exact function signatures with parameter lists in the body text (e.g. `def foo(x: int, y: str = None)` outside a code-block illustrating the API contract).
  - Contains > 5 file path references to `/app/<specific-source-file>` — symptom of "tour of every file you must edit" style.
  - Contains a numbered list with > 10 items, or any "must"/"should" count > 20 across the whole file.
  - Contains code snippets > 1 line each that AREN'T the public API contract a test will read (e.g. internal helper bodies, build-config recipes).
  - To fix: rewrite as a problem statement. Open with **why** this work is needed (the observable bug or missing capability), state **what** must be true once it's done (the observable contract — names, error strings, numerical tolerances), and end with **constraint** (which files may be edited, what must not be modified). Strip the **how** entirely; an experienced engineer reading the instruction should still need to think about implementation.

### 1d. `environment/Dockerfile` checks

(If `docker-compose.yaml` exists, also scan it for `image:` lines and `privileged: true`.)

- **HIGH (CI `pinned_dependencies` — base image)**: any `FROM` line WITHOUT a digest pin `@sha256:<64-hex>`. As of mid-2026 CI hard-fails on tagged-only bases like `FROM python:3.12-slim` — must be `FROM python:3.12-slim@sha256:<64-hex>`. Fetch the digest with `curl -s 'https://hub.docker.com/v2/repositories/library/<image>/tags/<tag>' | python3 -c "import json,sys; print(json.load(sys.stdin)['digest'])"`. Common digests at the time of writing (verify before reuse):
  - `debian:bookworm-slim` → `@sha256:0104b334637a5f19aa9c983a91b54c89887c0984081f2068983107a6f6c21eeb`
  - `python:3.12-slim` → `@sha256:090ba77e2958f6af52a5341f788b50b032dd4ca28377d2893dcf1ecbdfdfe203`
- **HIGH (CI `dockerignore_missing`)**: `environment/` contains files beyond just the Dockerfile but no `environment/.dockerignore`. Add one with at minimum:
  ```
  .git
  .gitignore
  **/__pycache__/
  **/*.pyc
  **/.pytest_cache/
  **/.mypy_cache/
  **/.ruff_cache/
  **/node_modules/
  **/*.key
  **/.DS_Store
  ```
- **HIGH (CI `build_context_pollution` — secret-shaped files)**: any `*.key`, `*.pem`, `*.crt`, `id_rsa*`, or other credential-shaped filename anywhere under `environment/` (CI scans `environment/repo/**/*.key` too). Even GPG release-signing public keys (e.g. `jq-release-new.key`) trip this — delete them from the build context. Detect with `find environment -type f \( -name '*.key' -o -name '*.pem' -o -name '*.crt' -o -name 'id_rsa*' \)`.
- **LOW (CI false-positive — `runtime_build_tool_package` warning)**: a single-stage Dockerfile that installs build tooling (`build-essential`, `make`, `gcc`, `autoconf`, `cmake`, etc.) at the runtime layer triggers a "should be multi-stage" warning. For **debugging tasks** where the agent edits source and the verifier re-runs the build (e.g. all jq / scipy debugging tasks where `solve.sh` does `make -j"$(nproc)"`), this is a **known false positive** per the CI carve-out — keep the single-stage Dockerfile. CI documents a future `task.toml` metadata flag to auto-suppress this. Action: ignore for debugging tasks; for everything else, split into `<lang>:… AS builder` + `COPY --from=builder` runtime.
- **HIGH (CI `tests_or_solution_in_image`)**: `COPY tests/`, `COPY ./tests/`, `COPY solution/`, `COPY ./solution/`, or any `ADD` of those paths.
- **HIGH (verifier dependency placement)**: dependency wheels under `tests/`, or package installation/downloads in `tests/test.sh`, are client-feedback blockers. Bake verifier deps into the Dockerfile with exact pins.
- HIGH: `RUN mkdir` (or `mkdir -p`) of `/tests`, `/oracle`, `/solution`, `/logs/verifier`, `/logs/artifacts`.
- HIGH: `RUN chown ... /tests`, `... /oracle`, `... /solution`.
- **HIGH (CI `check_dockerfile_references`)**: Dockerfile references `solution/solve.sh`, `tests/test.sh`, `tests/test_outputs.py`, or any file under `solution/` or `tests/`. Detect with: `grep -E 'solution/(solve\.sh|init_state\.patch)|tests/(test\.sh|test_outputs\.py|test_m[0-9]+\.py)' environment/Dockerfile`.
- **HIGH (CI `pinned_dependencies` — pip)**: any pip install line where one of the requested packages lacks a `==X.Y.Z` pin. Detect tokens after `pip install` (skip flags); fail any token that matches `^[A-Za-z0-9_.-]+$` without a `==`.
- HIGH: `curl|wget` to a non-package URL inside `RUN` (allow `astral.sh/uv/<version>/install.sh`, `pypi`, `nodejs.org`, `apt` mirrors, `github.com/.../releases/...`, `playwright.azureedge.net`, `npmjs.org`). Skeletons use `astral.sh/uv/0.9.5/install.sh` and `astral.sh/uv/0.9.7/install.sh` — both fine. Heuristic: flag any http(s) URL not in an allowlist; let user override.
- HIGH: `git clone` without a follow-up `git checkout <sha>` pinning a commit.
- **HIGH (CI `check_privileged_containers`)**: any compose service with `privileged: true`, `cap_add: [SYS_ADMIN|NET_ADMIN|SYS_MODULE]`, or `volumes:` mounting `/var/run/docker.sock`, `/logs/verifier`, `/logs/artifacts`, `/tests`, or `/solution`.
- HIGH (compose): any `image:` with `:latest` or no tag.
- LOW: heredoc patterns (`<<EOF`, `<< 'EOF'`) inside `RUN` — discouraged.
- LOW: apt packages without `=version` for niche packages (don't flag common ones — `git`, `curl`, `ca-certificates`, `build-essential`).

### 1e. `solution/solve.sh` (non-ms) and `steps/milestone_N/solution/{solve.sh,solveN.sh}` (ms)

Canonical milestone wrapper pattern from [task_skeleton/milestone/.../solve.sh](../../../task_skeleton/milestone/milestone_template/steps/milestone_1/solution/solve.sh):
```bash
#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/solveN.sh"
```
And payload `solveN.sh` also has shebang + `set -euo pipefail`.

For each file:
- HIGH: missing shebang (`#!/usr/bin/env bash` or `#!/bin/bash`). (Exception: the regular-skeleton `solve.sh` has no shebang and is just `echo "Hello, world!" > hello.txt` — this is acceptable as a one-liner because harbor invokes via `bash solve.sh`, but for any multi-line script the shebang is HIGH.)
- HIGH: not executable (`! -x`). Auto-fix by `chmod +x` and re-flag as resolved-LOW (note in report).
- MED: missing `set -e` / `set -euo pipefail` near top (skipped if file is a single-line one-liner).
- HIGH: `curl|wget` to a non-package URL (same allowlist as Dockerfile).
- HIGH: lone `echo "<answer-looking string>" > <output file>` without surrounding derivation logic. Heuristic: file body is < 5 non-comment lines AND contains `echo ... >`. Flag as `hardcoded_solution` candidate. **Exception:** the regular-skeleton's `solve.sh` (`echo "Hello, world!" > hello.txt`) is a deliberate hello-world example — but any REAL task with that shape IS a hardcoded solution and should be flagged.
- HIGH (ms): `solveN.sh` exists; `solve.sh` is a wrapper that ultimately invokes `solveN.sh` (grep `bash .*solveN.sh` or `source .*solveN.sh`). Wrapper should NOT contain derivation logic itself.
- HIGH (ms): `solveN.sh` missing shebang OR missing `set -euo pipefail`.
- MED: any `random` / `time` call without a fixed seed (search for `random.choice`, `np.random` without `seed`, `$RANDOM`, `date +%N`).

### 1f. `tests/test.sh` (non-ms) and `steps/milestone_N/tests/test.sh` (ms)

`tests/test.sh` must end with a reward block. The current `check_test_sh` gate
accepts either the inline `$?` form or a variable captured immediately after
pytest; the variable form is preferred because `$?` is easy to clobber.

```bash
if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
```

Preferred form:

```bash
python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
rc=$?
if [ "$rc" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
```

Findings:
- **HIGH (CI reward-pattern)**: `tests/test.sh` does not end with an accepted
  reward block: pytest, then either immediate `rc=$?` plus `if [ "$rc" -eq 0 ]`
  or immediate `if [ $? -eq 0 ]`, then reward writes.
- HIGH: does not write `/logs/verifier/reward.txt` (or `reward.json`) on **both** the success and failure path.
- HIGH: any runtime setup in this file: `apt-get`, `pip install`, `npm install`, `curl`, `wget`, `playwright install`, or dependency-resolving `uvx`.
- HIGH: contains conditional logic that branches on whether `/oracle` exists, or sets `EVAL_IS_ORACLE`, or chmods test files only when oracle absent (quality-guidelines §2 — same logic for oracle and agent).
- HIGH: bare reference to an env var with no default (`"$TEST_DIR"` without `${TEST_DIR:-/tests}` somewhere earlier; allow `$HOME`, `$PWD`, `$PATH`).
- MED: latency / timing assertions inside the script (search for `p50|p95|p99|latency_ms|elapsed_ms` patterns).
- MED: uses `set -e` / `set -euo pipefail` without `set +e` around pytest and
  does not match either accepted reward form.

**UI task variant** (`tests/test.sh` for `ui_building` subcategory):
- HIGH: `npm install`, `npm ci`, `playwright install`, or browser downloads in
  `tests/test.sh`. Install Node verifier deps and browsers during Docker build.
- HIGH: missing `npm run test` and `npm run test:e2e` reward gating when the UI
  task expects both unit and E2E coverage.
- HIGH: reward gate not based on BOTH unit AND E2E exit codes (skeleton uses `UNIT_EXIT=$?` + `E2E_EXIT=$?`, then `[ "$UNIT_EXIT" -eq 0 ] && [ "$E2E_EXIT" -eq 0 ]`). Single-suite reward gating is incorrect.
- MED: Dockerfile does not install required Node verifier dependencies or browser
  binaries needed by the UI tests.

### 1g. `tests/test_outputs.py` (non-ms) and `steps/milestone_N/tests/test_mN.py` (ms)

Skip this section entirely for UI tasks (`ui_building` subcategory) — they use Vitest/Playwright specs, covered in 1g-ui below.

- HIGH (B4): any `import` from `solution`, `bash solution/`, `subprocess.*solve.sh`, `open("/solution/...")`, `Path("/solution/...")`. Anti-cheating + B4 from CLAUDE.md.
- HIGH (A6): any `inspect.getsource`, `inspect.getsourcefile`, `ast.parse(open(...).read())`, `re.search(r"def …", source)`, or `assert "…" in open("…py").read()` — these check implementation shape, not behavior.
- HIGH (B4): any reference to `solution/solve.sh` / `/solution/solve.sh` / `init_state.patch`.
- HIGH: a test function (`def test_*`) with no docstring (LLMaJ `informative_test_docstrings`).
- MED: uses `assert <var> == "<long literal>"` comparing entire file contents byte-for-byte (brittle); suggest substring/property check.
- MED (ms only): `test_mN.py` does not define a `class TestMilestoneN` (Snorkel reviewer-checklist requires the class).
- LOW: tests appear order-dependent (relies on module-level mutable state — `global` in a test fn).
- **MED (LLMaJ Test Quality Review — "weak assertion" pattern)**: a test that only asserts the *shape* of an API (e.g. `hasattr(cls, "foo")` or `try: cls.foo(...) except TypeError: ...`) but never asserts what `foo()` actually does to its inputs/outputs. The LLMaJ quality reviewer flags these as "agent can satisfy by adding a no-op signature". For every method/property documented in instruction.md, ensure at least ONE test asserts a behavior contract (input → output relationship), not just the existence of the symbol. Heuristic detection: a `test_*` function that contains `hasattr` / `try: ... except TypeError` but no `assert <result> == <expected>` / `assert <result> in <expected_set>` / `assert <key> in <returned_dict>`.
- **MED (LLMaJ Test Quality Review — "kwarg accepted but not used")**: a test that calls a method with a new keyword argument set to `None` (e.g. `func(..., new_param=None)`) only proves the parameter is accepted by the signature — it does NOT prove the implementation USES it. For every new keyword argument added by the task, write at least one additional test that passes a non-None value AND asserts an observable side-effect that requires the implementation to actually consume that argument. Common pattern: pass a recording stub (a small class with a `.calls` list) and assert `stub.calls` is non-empty after the call. Catches the "agent adds the parameter but never reads it" cheat.
- **MED (LLMaJ Test Quality Review — "subset coverage")**: end-to-end integration test exercises only a subset of the requirements (e.g. a playbook runs `ping` and `direct_invocation` but the instruction also mandates the same toggle behavior in the `copy` action plugin). Verify each entity named in instruction.md (module, action plugin, dataclass, helper function) appears in at least one assertion across the test file.
- **MED (LLMaJ Test Quality — "buffer-enlargement / scale-up cheat")**: if the task's bug is about handling state at a buffer boundary, page boundary, or other fixed size, the test inputs must EXCEED any plausible "just enlarge the limit" workaround. Concrete pattern from the jq-utf8-slurp task: source has `char buf[4096]` and the bug is multi-byte UTF-8 straddling that boundary; if the test input is only ~12 kB, the agent can change `buf[4096]` → `buf[16384]` (one token) and the test passes without addressing the bug. Fix: scale inputs to > 100 kB (or > 10× the buffer size), so no realistic stack-buffer enlargement can swallow the entire input. Add an inline `assert len(input) >= EXPECTED_MIN` so the test self-documents the lower bound.
- **MED (LLMaJ Test Quality — "forbidden-file edit cheat")**: when the instruction says "do not edit file X", the verifier must enforce that constraint with a SHA-256 checksum test, not trust the instruction alone. Pattern: read the file's bytes at test time, hash them, compare against a hardcoded digest computed at task-build time. Catches the cheat where an agent routes around the task by editing the forbidden helper / header / sibling-correct file. Example: [tasks/tbrain-jq-utf8-slurp-multibyte/tests/test_outputs.py](../../../tasks/tbrain-jq-utf8-slurp-multibyte/tests/test_outputs.py) → `_PROTECTED_FILE_HASHES` + `test_protected_files_unmodified`.
- **MED (LLMaJ Test Quality — "exact diagnostic format" pattern)**: if the instruction specifies exact error-message strings (e.g. `function has too many parameters (max %d)` with `%d` substituted), the test must assert ONE of the documented formats verbatim, NOT a loose substring like `"too many" in stderr and "(max 4095)" in stderr`. The loose form lets the agent emit non-standard messages like `error: too many things here (max 4095)` and still pass. Use `VALID_DIAGNOSTICS = ("function has too many parameters (max 4095)", ...)` + `assert any(m in proc.stderr for m in VALID_DIAGNOSTICS)`. Example: [tasks/tbrain-jq-closure-index-overflow/tests/test_outputs.py](../../../tasks/tbrain-jq-closure-index-overflow/tests/test_outputs.py).
- **MED (LLMaJ Test Quality — "category ↔ test pattern boundary mismatch")**: the test program shape might trip the bug at a DIFFERENT count than the instruction states. Example from jq-closure-index: instruction says boundary is 4096 subfunctions, but the test pattern (`def f{i}(x): x + {i}` with flat additive body) emits ~2 CLOSURE_CREATE opcodes per def, so the ceiling actually trips at N=2049, not 4096. Verify boundaries with oracle first, then document the empirical N in named constants (`_DEFS_BELOW_BLOCK_CEILING = 2048`, `_DEFS_ABOVE_BLOCK_CEILING = 2049`) with a docstring explaining the ratio.

### 1g-cross. instruction.md ↔ tests symmetry (`behavior_in_task_description` LLMaJ check)

- **HIGH (LLMaJ `behavior_in_task_description` — "tests assert symbols not mentioned in instruction")**: every symbol the test asserts the agent must produce (module name, class name, function name, constant name, exact error string, exact log substring, exact value of a constant, exact emoji codepoint) must appear somewhere in `instruction.md`. The agent does NOT see the test file at runtime — the Dockerfile only copies `repo/` — so anything the test grep-checks must be documented up front. Heuristic: grep `assert hasattr\(.*\)`, `assert .*==.*"`, `in proc.stderr`, `in proc.stdout` across `tests/test_outputs.py`, extract the literal strings/names, and verify each one is present in `instruction.md` (or in a clearly-named upstream test fixture that the verifier stages into the source tree — but ONLY if that fixture is also visible to the agent at task time, which it usually is NOT).
- **HIGH (LLMaJ `behavior_in_task_description` — "deferring contract to a file the agent can't read")**: instructions that say "read the upstream test module for the full contract" FAIL this check when the test module is NOT staged into the image at agent time (i.e. the Dockerfile only `COPY repo/ .`, not `COPY tests/`). The agent must be able to derive every test-asserted behavior from `instruction.md` alone. Fix: inline the contract into the instruction (constant values, exact log substrings, exact result-list ordering, exact env var names, exact early-return conditions, exact autoclose conditions). Reference example of the right balance: [task_release/tbrain-django-pr-quality-checks/instruction.md](../../../task_release/tbrain-django-pr-quality-checks/instruction.md) v12 — has explicit `### Public surface the tests import by name`, `### Behaviours the tests assert directly`, and `### Entry point and data sources` sections.
- **MED (LLMaJ `behavior_in_task_description` — "patch modifies files outside instruction's scope")**: if the instruction says "Do not modify files outside the new package directory" but the oracle's `init_state.patch` touches files outside that directory (e.g. `.github/workflows/*.yml`, `doc/`, `tools/`), the LLMaJ judge flags it as instruction-vs-solution mismatch. Strip those out-of-scope hunks from the patch before shipping. Detect with: `grep -E '^diff --git a/(\.github/|doc/|tools/|tests/)' solution/init_state.patch`.

### 1g-ui. UI task specs (`tests/unit/*.spec.ts`, `tests/e2e/*.spec.ts`)

Only run if `ui_building` is in `subcategories`. Skeleton: [task_skeleton/ui/tests/](../../../task_skeleton/ui/tests/).

- HIGH: no spec file under `tests/unit/` matching `*.spec.ts` (Vitest `include` glob).
- HIGH: no spec file under `tests/e2e/` matching `*.spec.ts` (Playwright `testDir: "./e2e"`).
- HIGH: any spec imports from `../../solution/` or reads files under `/solution/` (B4 / anti-cheating).
- HIGH: `tests/package.json` missing one of: `@playwright/test`, `vitest`, `serve` (or equivalent webServer command in `playwright.config.ts`).
- HIGH: `playwright.config.ts` `webServer.command` references a path that doesn't exist (typically `npx serve /app -p 3000` — `/app` must be the WORKDIR / where the agent writes the app).
- MED: spec contains a brittle full-page-source string match (e.g. `expect(html).toBe("<!DOCTYPE...long literal...>")`).
- LOW: missing `forbidOnly: true` in `playwright.config.ts` (skeleton has it; prevents accidental `.only` from greening CI).

### 1h. Anti-cheating cross-checks

- HIGH: any answer string from a test (`assert x == "<literal>"`) appears verbatim in the Dockerfile/COPY-ed files (grep the literal across `environment/`).
- MED: an output filename a test reads (`Path("/app/...")`) is **not** mentioned in `instruction.md` (`file_reference_mentioned` LLMaJ check).
- MED: a structured-data field name asserted by tests (e.g. `data["status"]`) is not mentioned in `instruction.md` (`structured_data_schema` LLMaJ check).

### 1i. Repo hygiene

- LOW: stray top-level files: `README.md`, `data/`, `jobs/`.
- **HIGH (CI ruff-fail)**: any macOS junk in the task tree — `__MACOSX/` directories, `.DS_Store` files, `._*` resource-fork files. These ride into the zip when compressed via macOS Finder Right-click → Compress, and Snorkel's ruff step then fails with `E902 stream did not contain valid UTF-8` on the binary `._*` files. To prevent: zip via `zip -rX <task>.zip instruction.md task.toml environment solution tests -x '*.DS_Store' -x '__MACOSX/*'` (the `-X` strips extra extended attributes, and the `-x` excludes are belt-and-suspenders) — or use `ditto -ck --norsrc --noextattr <src> <dst>.zip` on macOS. Detect by `find . \( -name __MACOSX -o -name '.DS_Store' -o -name '._*' \) | head`.
- LOW: `__pycache__/`, `*.pyc` (less harmful but should be cleaned before zipping).
- LOW: any file > 1 MB (CI `check_task_sizes` cutoff).

### 1i.1. `typos` CI check

- **MED (CI `typos`)**: Snorkel runs a spell-check across the task tree (file content + variable/function names in source files). Common offenders: `recieve` → `receive`, `seperate` → `separate`, `occured` → `occurred`, `enviroment` → `environment`, `lenght` → `length`. Per `docs/testing-and-validation/ci-checks-reference.md#typos`. To pre-flight, run `typos` (cargo install) or `codespell` locally over `instruction.md`, `solution/`, `tests/`, and any text files you authored under `environment/` (NOT inside `environment/repo/` — upstream code typos are out of scope; if CI flags them, exclude the path the same way the ruff exclude works in section 1j).
- LOW: instruction.md or test_outputs.py docstrings contain technical terms that look like typos but are intentional (`gunicorn`, `kube-apiserver`, etc.) — these can be silenced via a project-level dictionary if `typos` exposes one.

### 1j. `environment/repo/` upstream-source hygiene (pre-staged repos)

When a task pre-stages an upstream repo into `environment/repo/`, Snorkel's `ruff` and "blacklisted databases" checks run against THAT subtree too. The upstream code is rarely ruff-clean and may contain false-positive blacklist hits.

- **HIGH (root packaging hygiene)**: do not include task-root `pyproject.toml` in submitted tasks. If local tooling needs a ruff exclude for `environment/repo`, keep that config outside the ZIP or remove it before packaging.

- **HIGH (CI ruff-fail on env/repo)**: `ruff check <task>` runs over the entire task tree including `environment/repo/`. Upstream codebases may have many warnings. Prefer pruning irrelevant files or using CI-supported exclusions that do not require submitting a root `pyproject.toml`; never rewrite upstream source behavior just to silence ruff.

- **HIGH (CI blacklisted-database)**: Snorkel scans for commercial DB strings via **case-insensitive substring matching**, not word-boundary regex. Known triggers observed: `oci_` → "Oracle (OCI)", `maxscale` → "MariaDB_MaxScale". The blacklist is dumb-substring and produces false positives in sklearn (`MinMaxScaler`, `MaxAbsScaler` contain the substring `maxscale`), Ansible (`oci_vcn` legacy module redirects). Verify with: `grep -rilE 'maxscale|oci_|oracle|mysql|sqlserver|mariadb|snowflake|redshift|bigquery|postgres' environment/repo/`.
  Mitigation strategies (in order of preference):
  1. **Strip the offending file/block** if it's not needed for the task subset (e.g. legacy module redirects in YAML config).
  2. **Rename the symbol** to break the substring while keeping behavior (e.g. `MinMaxScaler` → `MinMxScaler` in preprocessing/, then update any external import alias). Insert a character to break the trigger substring; the class is still functional, just renamed. Find external users with `grep -rn "OldName" --include="*.py"` and update each.
  3. **Stub the subpackage entirely** if the task doesn't touch it AND sklearn's meson/init doesn't strictly require it — but this often cascades: sklearn `__init__.py` declares `_submodules`, and downstream code (e.g. `sklearn.metrics.pairwise` imports `from sklearn.preprocessing import normalize`) needs the public API intact. Strip with extreme caution.
  Always confirm with `grep -ric '<trigger>' environment/repo/` returning 0 hits AND `harbor run -a oracle` still passes.

  Implementation hint for YAML config blocks:
  ```python
  import re
  src = open('config_file.yml').read()
  pat = re.compile(r"^( {4}[a-zA-Z0-9_]*o(ci|racle)[a-zA-Z0-9_.]*:\n(?: {6,}[^\n]*\n)+)", re.M | re.I)
  open('config_file.yml', 'w').write(pat.sub("", src))
  ```

- **MED**: pre-staged repo larger than necessary. Snorkel `large` requires ≥ 200 files but a 50 MB repo will hit the 1 MB-per-file or aggregate `check_task_sizes` thresholds. Prefer the minimum subset that (a) compiles, (b) reaches the file count threshold, (c) contains the files the task actually patches.

---

### 1k. "What makes a good task" substance heuristics (per `docs/understanding-tasks/what-makes-a-good-task.md`)

Structural checks pass ≠ task is good. Snorkel's peer-review stage rejects tasks that pass CI but violate the "good task" core principle:

> **A good task is one that an expert human can solve confidently, but that challenges or stumps current AI coding agents.**

These offline heuristics flag the most common substance issues before they reach peer review. None of them are 100% accurate — they're cheap proxies that warrant a closer look.

- **HIGH (anti-pattern: external dependency)**: `instruction.md` mentions live network calls, paid APIs, or credentials. Detect any of: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, `AWS_`, `STRIPE_`, "API key", "credentials", `curl https://api.`, `requests.get("https://`, mentions of live external services (twitter.com, openai.com, stripe.com) that aren't mocked in `environment/`. Per `quality-guidelines.md`: tests must run offline.
- **HIGH (anti-pattern: single-command / trivia)**: `solution/solve.sh` body (excluding shebang + `set -e` + comments) is < 3 non-blank lines AND `instruction.md` is < 50 words. Almost certainly a one-liner or trivia question — worst-model pass rate will be 100% → auto-reject. Per `what-makes-a-good-task.md` "Anti-patterns": "Simple one-liners — agent solves instantly".
- **MED (anti-pattern: ambiguous requirements)**: `instruction.md` contains vague verb phrases without concrete observables. Detect: `make.*better`, `improve.*performance`, `clean.*up`, `optimize`, `refactor` without specifying the success criterion. Phrase like "Make this code better" is the docs' canonical bad example.
- **MED (anti-pattern: brittle tests — exact string match)**: `test_outputs.py` contains `assert .* == "<literal string > 100 chars>"` comparing whole-file content byte-for-byte. Prefer property/substring/structural assertions.
- **MED (anti-pattern: cheating opportunity — test file readable from solution)**: `solution/solve.sh` reads from `/tests/` (e.g. `cat /tests/test_outputs.py`, `cp /tests/...`). The four canonical cheat paths per the docs are (a) look in tests for answers, (b) edit data files to pass tests, (c) delete tests, (d) hardcode expected outputs. Section 1g already catches (a) via B4; this rule catches the reverse (solution peeking at tests).
- **MED (anti-pattern: cheating opportunity — fixture editable)**: a file the test reads (e.g. `Path("/app/data.json").read_text()`) lives at a path the agent has write access to AND the test's expected value is a literal in `test_outputs.py`. The agent can edit the data to match the literal. Mitigation: compute the expected value in the test from the inputs.
- **LOW (hardness hint: no debugging signal)**: `instruction.md` doesn't mention any failing test, error message, stack trace, or symptom — pure "implement X" phrasing. Per the docs' "How to Make Tasks Harder": debugging-style tasks (agent must find the root cause from symptoms) push the pass rate down. If the task is borderline-easy and worst-model exceeds 60%, reframing as debugging is the cheapest hardness lever.
- **LOW (hardness hint: very common pattern)**: instruction touches a topic every frontier model has memorized — quicksort, palindrome, fizzbuzz, simple CRUD, single-file flask app, classic leetcode problems. These tend to land > 80% pass rate; flag for user to consider replacing with a niche/domain-specific problem.

### Empirical difficulty cross-check (already covered, restated for context)

Per Step 7 (`--with-agent`, opt-in), the official Snorkel pass-rate calibration runs:
- `harbor run -a terminus-2 -m gpt-5.2 -p <task> -k 5 --env-file .env`
- `harbor run -a terminus-2 -m claude-opus-4-6 -p <task> -k 5 --env-file .env`

And applies the difficulty bands from `docs/understanding-tasks/difficulty-guidelines.md`:
- HARD: ≤ 20% on **best** OR **worst** model
- MEDIUM: 20% < accuracy ≤ 60% on **worst** model
- EASY: 60% < accuracy ≤ 80% on **worst** model
- > 80% on worst model → REJECTED

If `task.toml` declares a difficulty that doesn't match the observed worst-model band, emit HIGH (declared difficulty must match empirical; mismatch is one of the most common reviewer rejections). Python tasks must additionally hit HARD per the diversity gate in section 1b.

## Step 2 — Optional: B4 + tb_quality offline scan

Always run, very fast:

```bash
PYTHONPATH=/Users/trung/develop/tb-quality/src \
  /Users/trung/develop/tb-quality/.venv/bin/python -m tb_quality check-b4 "$TASK_DIR"
```

Pipe output into the report. Any non-zero exit → HIGH finding.

---

## Step 3 — CI quality checks (always run)

Fast (~seconds, free). Maps to the 12 CI checks in `docs/testing-and-validation/ci-checks-reference.md`:

```bash
/Users/trung/develop/tb-quality/.venv/bin/harbor task check "$TASK_DIR" 2>&1 | tee "/tmp/${TASK_SLUG}_ci_check.log"
```

Any failed check in the output → HIGH finding with the check name (e.g. `pinned_dependencies`, `check_task_absolute_path`, `validate_task_fields`).

If `harbor` binary missing → emit ONE HIGH finding (`harbor not installed — CI checks skipped`) and continue.

---

## Step 4 — Oracle agent (always run)

Builds the Docker image and verifies the oracle solution passes. **~5 min, free** (local Docker only). Per `docs/testing-and-validation/oracle-agent.md`:

```bash
mkdir -p reports
/Users/trung/develop/tb-quality/.venv/bin/harbor run \
  -a oracle \
  -p "$TASK_DIR" \
  -k 1 \
  -o "reports/${TASK_SLUG}" \
  --job-name tb-oracle \
  --quiet --delete --force-build
```

Read `reports/${TASK_SLUG}/tb-oracle/result.json` (or the per-trial reward.txt). Map:
- Oracle reward != 1 → HIGH (`Oracle does not solve the task as instructed — fix solve.sh or test_outputs.py`).
- Build failure → HIGH with the Docker error excerpt.

If Docker daemon down → emit ONE HIGH finding (`Docker not running — oracle step skipped; start Docker Desktop`) and continue to Step 5.

---

## Step 5 — Nop baseline (always run)

Sanity check: a no-op agent must FAIL the tests. If it passes, the tests are too lax — the agent can do nothing and still win. **~1 min, free**. Per `docs/testing-and-validation/nop-agent.md`:

```bash
/Users/trung/develop/tb-quality/.venv/bin/harbor run \
  -a nop \
  -p "$TASK_DIR" \
  -k 1 \
  -o "reports/${TASK_SLUG}" \
  --job-name tb-nop \
  --quiet --delete
```

(No `--force-build` — re-uses the image from Step 4.) Read `reports/${TASK_SLUG}/tb-nop/result.json`:
- Nop reward == 1 → HIGH (`Nop baseline passes — tests too lax, see common-errors.md "Cheating Opportunities"`).
- Nop reward != 1 → INFO (good — agent cannot cheat by doing nothing).

---

## Step 6 — LLMaJ judge (always run)

Runs the 7 LLM-as-Judge checks documented in `docs/testing-and-validation/llmaj-checks-reference.md`. **~1 min, costs API (small).**

```bash
/Users/trung/develop/tb-quality/.venv/bin/harbor check "$TASK_DIR" \
  -m sonnet \
  -o "/tmp/${TASK_SLUG}_harbor_check.json"
```

`ANTHROPIC_API_KEY` is loaded from `/Users/trung/develop/terminus/.env` automatically by `harbor` (or by exporting it in the shell). Do NOT also `source` the .env in the shell — let `harbor` read it directly so values don't leak into the shell env.

Map each failed criterion in the JSON output to a HIGH finding with the criterion id and the judge's rationale (truncate to ~200 chars). Common failures: `behavior_in_tests`, `behavior_in_task_description`, `informative_test_docstrings`, `anti_cheating_measures`, `hardcoded_solution`, `file_reference_mentioned`, `structured_data_schema`.

If `harbor` binary missing → emit ONE HIGH finding (`harbor not installed — LLMaJ skipped`) and continue.
If `.env` missing → emit ONE HIGH finding (`.env missing — LLMaJ cannot authenticate; copy from tb-quality/.env or recreate`).

---

## Step 7 — `--with-agent` pass-rate sanity (k=2) — opt-in only

Only run if user explicitly passed `--with-agent`. **Confirm with the user once more before kicking off** — slow (10–20 min) and costs real API money. Per `docs/testing-and-validation/running-real-agents.md`, official calibration uses 5 runs × {gpt-5.2, claude-opus-4-6}; this k=2 codex run is a fast sanity check, not the official measurement.

```bash
/Users/trung/develop/tb-quality/.venv/bin/harbor run \
  -p "$TASK_DIR" \
  -a codex -m gpt-5.3-codex -k 2 \
  -o "reports/$TASK_SLUG/tb-codex-precheck" \
  --env-file /Users/trung/develop/terminus/.env
```

Parse `reports/$TASK_SLUG/tb-codex-precheck/result.json` → `stats.evals.codex__adhoc.reward_stats.reward`. Count pass / 2.

- 2/2 pass → HIGH (`Likely too easy — pass-rate ≥ 80% even at k=2; Snorkel rejects worst-model > 80%`).
- 0/2 pass → MED (`Possibly too hard — verify that oracle still passes with --with-docker, and that the prompt isn't ambiguous`).
- 1/2 pass → INFO (`Difficulty looks healthy — re-confirm with k=5 in the autorun pipeline`).

This is *not* the official difficulty calibration (Snorkel uses 5 runs against both gpt-5.2 and claude-opus-4.6) — note that in the report.

---

## Step 8 — Emit the report

Print to stdout, in this order:

```
# Terminus Validate — <TASK_SLUG>

Kind: <non-milestone | milestone (N=<n>)>
Category: <category>   Subcategories: [<...>]   Difficulty: <difficulty>
Codebase size: <minimal|small|large>   Languages: [<...>]   Tags: [<...>]

Diversity gate: <PASS | BLOCKED — reason>
  (easy / Python+non-hard auto-block per diversity-requirements.md; codebase_size minimal/small/large all accepted when honest)

## HIGH (must fix before submit) — <count>
- [<area>] <path>: <message>
- ...

## MEDIUM (review before submit) — <count>
- ...

## LOW (nice to have) — <count>
- ...

## Checks run
- Structural (rules 1a-1i): <pass|N findings>             (always, offline)
- B4 scan (`tb_quality check-b4`): <pass|fail>            (always, offline)
- CI checks (`harbor task check`): <pass|N failed>        (always, ~seconds)
- Oracle (`harbor run -a oracle`): <pass|fail>            (always, ~5 min Docker)
- Nop baseline (`harbor run -a nop`): <fails-as-expected|too-lax>  (always, ~1 min)
- LLMaJ (`harbor check -m sonnet`): <pass|N failed>       (always, ~1 min API)
- Agent k=2 sanity: <skipped|2/2|1/2|0/2>                 (only if --with-agent)

## Verdict
- <READY-TO-SUBMIT | NEEDS-FIXES (count of HIGH)>
```

If HIGH count > 0 → verdict `NEEDS-FIXES`. Otherwise:
- HIGH=0 and MED=0 → `READY-TO-SUBMIT`.
- HIGH=0 and MED>0 → `READY-TO-SUBMIT-WITH-NOTES` and tell the user the medium items they're shipping with.

After printing, append a multi-line follow-up:

```
Next:
  1. Create the ZIP — DO NOT use macOS Finder Right-click → Compress (it injects __MACOSX/
     which fails Snorkel ruff with E902). Use this instead:

        cd <TASK_SLUG>/
        find . \( -name '.DS_Store' -o -name '._*' \) -delete
        zip -rX ../<TASK_SLUG>.zip \
            instruction.md task.toml environment solution tests \
            -x '*.DS_Store' -x '__MACOSX/*' -x '*/__pycache__/*' -x '*.pyc'

     (Milestone tasks: replace `instruction.md solution tests` with `steps`.)

  2. Sanity-check the archive:

        unzip -l <TASK_SLUG>.zip | grep -cE '__MACOSX/|\.DS_Store'   # must print 0

  3. Upload to experts.snorkel-ai.com → Terminus-2nd-Edition. Check the rubrics
     checkbox; leave Send-to-Reviewer UNticked the first time. Edit the generated
     rubric before reviewer submission: non-milestone uses a flat `Agent ...`
     list; milestone uses `# Rubric 1`, `# Rubric 2`, etc. blocks.

See docs/submitting-tasks/platform-submission.md.
```

### Coverage of the 11 official CI checks

The structural rules above are calibrated to catch every check Snorkel's `run_static_checks.py` runs offline. Cross-reference per `docs/testing-and-validation/ci-checks-reference.md`:

| CI check (official) | SKILL rule | Section | Sev |
|---|---|---|---|
| `pinned_dependencies` (pip) | unpinned package after `pip install` | 1d | HIGH |
| `pinned_dependencies` (base image) | `FROM ... :latest` or no tag | 1d | HIGH |
| `typos` | spell-check across task tree | 1i.1 | MED |
| `tests_or_solution_in_image` | `COPY tests/` or `COPY solution/` | 1d | HIGH |
| verifier dependency placement | wheels under `tests/` or runtime installs in `tests/test.sh` | 1d/1f | HIGH |
| `check_dockerfile_references` | Dockerfile references `solution/solve.sh` / `tests/test.sh` / `test_outputs.py` | 1d | HIGH |
| `check_test_sh` | test.sh missing reward write OR end pattern wrong | 1f | HIGH |
| `check_task_absolute_path` | instruction has relative path to a task file | 1c | HIGH |
| `check_privileged_containers` | compose `privileged: true` or dangerous caps | 1d | HIGH |
| `ruff` (task code) | macOS junk `__MACOSX/`/`.DS_Store`/`._*` triggers E902 | 1i | HIGH |
| root `pyproject.toml` | remove from submitted task ZIP | 1j | HIGH |
| `check_task_sizes` | any file > 1 MB | 1i | LOW |
| `validate_task_fields` | missing required `[metadata]` key | 1b | HIGH |
| `validate_task_fields` (category) | `category` not in 9 taxonomy values (lowercase kebab-case) | 1b | HIGH |
| `validate_task_fields` (subcategories) | `subcategories` entry not in 5 subtype values | 1b | HIGH |
| `validate_task_fields` (allow_internet) | `[environment].allow_internet` missing (must be `false`) | 1b | HIGH |

Plus three diversity-gate checks (per `docs/understanding-tasks/diversity-requirements.md`) and one blacklist (per `quality-guidelines.md`):

| Diversity / blacklist | SKILL rule | Section | Sev |
|---|---|---|---|
| `difficulty = "easy"` blocked | rule 1b diversity gate | 1b | HIGH |
| Python + difficulty ≠ "hard" blocked | rule 1b diversity gate | 1b | HIGH |
| Empirical `codebase_size` mismatch (file count) | rule 1b empirical check | 1b | HIGH |
| Commercial-database blacklist (`oracle`, `oci_`, `mysql`, `sqlserver`, …) | rule 1j substring scan | 1j | HIGH |

Plus the LLMaJ `instruction_check` (per `docs/testing-and-validation/llmaj-checks-reference.md`):

| LLMaJ judge | SKILL rule | Section | Sev |
|---|---|---|---|
| `instruction_check` (over-prescription) | rule 1c (3+ procedural verbs / 5+ `/app/...` path refs / inline function signatures) | 1c | MED |

Plus "what makes a good task" substance heuristics (per `docs/understanding-tasks/what-makes-a-good-task.md`):

| Substance heuristic | SKILL rule | Section | Sev |
|---|---|---|---|
| External-dependency anti-pattern (live APIs, credentials in instruction) | rule 1k anti-pattern: external dependency | 1k | HIGH |
| Single-command / trivia anti-pattern (solve.sh < 3 lines + instruction < 50 words) | rule 1k anti-pattern: single-command | 1k | HIGH |
| Ambiguous-requirement anti-pattern ("make better", "optimize", "refactor" with no observable) | rule 1k anti-pattern: ambiguous | 1k | MED |
| Brittle-test anti-pattern (exact-string assertion on 100+ char literals) | rule 1k anti-pattern: brittle | 1k | MED |
| Cheat path: solution reads from `/tests/` (peeking) | rule 1k cheating opportunity | 1k | MED |
| Cheat path: fixture editable + test expected value is a literal | rule 1k cheating opportunity | 1k | MED |
| Hardness hint: no debugging signal (pure "implement X" framing) | rule 1k hardness hint | 1k | LOW |
| Hardness hint: too-common pattern (quicksort, palindrome, fizzbuzz, CRUD) | rule 1k hardness hint | 1k | LOW |
| Declared difficulty ≠ empirical worst-model band | rule 1k empirical difficulty cross-check | 1k | HIGH |

### Real CI failures this skill is calibrated against

The rules above reflect real Snorkel CI failures observed during dogfooding 2026-05-16 → 2026-05-20 for `tbrain-ansible-inject-invocation`. Three consecutive submissions surfaced 8 issues; each issue → a strengthened rule:

| CI message (verbatim) | SKILL rule that now catches it |
|---|---|
| `codebase_size is 'large' but environment/ has 0 files (expected 'minimal')` | Empirical codebase_size mismatch (1b) |
| `test.sh: Must end with the reward section` | use an accepted reward block: immediate `rc=$?` or immediate `$?` conditional (1f) |
| `ruff E902: stream did not contain valid UTF-8` on `__MACOSX/.../._*.py` | macOS junk in tree (1i) |
| `ruff F401/F821 ...` over 1000+ errors inside `environment/repo/lib/ansible/` | prune/scope upstream files or use an allowed non-submitted local config; root `pyproject.toml` should not be in the ZIP (1j) |
| `Found 1 blacklisted database(s) in 1 file(s): Oracle` (substring match `oci_`) | Commercial-DB blacklist (1j) |
| `[instruction_check] reads as a detailed implementation guide` | LLMaJ over-prescription (1c) |
| `[instruction_check] reads like an implementation guide with prescribed refactoring steps` (2nd iteration) | Same rule (1c) — tighten further: prefer "outcome + constraint" wording, push naming details into a small "Naming hint" section at the end |
| `Missing required field: environment.allow_internet (must be false)` (added by Snorkel ~2026-05-20) | `[environment].allow_internet` required field (1b) |
| `typos: ini key 'interpreter_python' collides with INTERPRETER_PYTHON` | ini key collision when reusing upstream key for a new config (1b empirical) — pick a unique key (e.g. `inject_invocation`, not `interpreter_python`) |
| `setuptools>=77.0.3 ... Temporary failure in name resolution` when `uvx --with-editable` rebuilds | `allow_internet=false` offline rule (1b) — bake verifier deps into Dockerfile and remove runtime installs |
| Test Quality Review: "Copy action plugin toggle behavior has no correctness test" (LLMaJ recommendation: STRENGTHEN) | weak-assertion pattern (1g) — `hasattr` shape-check + no behavior assertion |
| Test Quality Review: "templar tested only with None — actual templating unverified" | "kwarg accepted but not used" pattern (1g) — use a recording stub |
| Test Quality Review: "`_ensure_invocation` result mutation not asserted" | weak-assertion pattern (1g) — must `assert "invocation" not in returned` |
| `Found 1 blacklisted database(s) in 15 file(s): MariaDB_MaxScale` (substring match `maxscale` in sklearn `MinMaxScaler`) | Commercial-DB blacklist false positive (1j) — case-insensitive substring; rename `MinMaxScaler` → `MinMxScaler` to break trigger |
| `[instruction_check] reads as a detailed implementation guide with prescriptive steps` (3rd iteration on sklearn) | LLMaJ over-prescription (1c) — refactor instruction outcome-focused: list the *observables* per code path (function returns False/True/list) rather than the diff (import X, change line Y, rename helper Z) |
| `RuntimeError: Failed to start tmux session. Error: None` → agent scores 0/N without writing any code | Dockerfile missing tmux + bash + util-linux (1b/1d) — agent harness can't bootstrap on `allow_internet=false`; pre-install at build time |

Run this skill BEFORE zipping. The combined `find` + `python toml parse` + `ruff check .` + `grep` set of checks reproduces ~80% of what Snorkel CI does, offline and in seconds.

---

## Implementation notes

- Do everything in one pass: read all files into memory once, run regex/AST checks, emit the report. Don't spawn one Bash per check.
- `task.toml` parsing: prefer Python `tomllib` (3.11+) — call via `python3 -c "import tomllib, json; print(json.dumps(tomllib.load(open('task.toml','rb'))))"`.
- For the regex scans inside Dockerfile / shell, use Python `re` — faster + clearer than chains of `grep`.
- Don't auto-fix anything except `chmod +x` on shell scripts (and report it as resolved-LOW). Surface every other finding for the user to act on; do NOT silently rewrite their files.
- If the user passes a path that doesn't exist OR the dir is empty, abort with `usage: /terminus-validate-task <path-to-task>`.

---

## Source-of-truth references (in `terminus/`)

These are the docs the checks above are derived from. When in doubt, re-read these:

- **Official Snorkel skeletons (compare-against canonical shape)** → [task_skeleton/regular/](../../../task_skeleton/regular/), [task_skeleton/milestone/milestone_template/](../../../task_skeleton/milestone/milestone_template/), [task_skeleton/ui/](../../../task_skeleton/ui/). If the skeleton has it, don't flag it.
- **What makes a good task (substance-level rules in section 1k)** → `understanding-tasks/what-makes-a-good-task.md`. The core principle, hardness levers, anti-patterns, cheating-path enumeration, and quality checklist that backs section 1k.
- Required structure → `understanding-tasks/task-components.md`, `task-requirements.md`
- **Category taxonomy (9 lowercase values, mandatory per task) → `understanding-tasks/task-taxonomy.md`**
- Subcategory taxonomy → `understanding-tasks/task-subtypes.md`
- Milestones → `understanding-tasks/milestones.md`
- Prompt style → `understanding-tasks/prompt-styling.md`
- Difficulty bands → `understanding-tasks/difficulty-guidelines.md`
- Diversity gates (codebase_size / model-difficulty / Python-must-be-hard auto-block) → `understanding-tasks/diversity-requirements.md`
- Dockerfile rules → `creating-tasks/creating-docker-environment.md`
- Oracle rules → `creating-tasks/writing-oracle-solution.md`
- Test rules → `creating-tasks/writing-tests.md`
- CI checks (the platform's automated scan) → `testing-and-validation/ci-checks-reference.md`
- LLMaJ checks (the platform's GPT-5 judge) → `testing-and-validation/llmaj-checks-reference.md`
- Common errors → `reviewing-tasks/common-errors.md`
- Quality scenarios (latency, oracle-vs-agent, web fetch, /tests dir, reward file, env var defaults, oracle-replication thresholds) → `reference/quality-guidelines.md`
- Reviewer severity table (HIGH/MED/LOW labels above are derived from this) → `reviewing-tasks/reviewer-checklist.md`
- Submission flow + ZIP procedure → `submitting-tasks/platform-submission.md`, `submission-checklist.md`
- Rubric authoring (out of scope here, but flag if user asks) → `understanding-tasks/rubrics.md`
