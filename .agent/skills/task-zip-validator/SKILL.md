---
name: task-zip-validator
description: Validate a Terminus task ZIP against Snorkel CI/review rules and auto-fix issues. Input is a ZIP file path. Unzips, audits structure/Dockerfile/instruction/tests against all known CI checks and review criteria, auto-fixes what it can, runs oracle+nop, re-zips if changes were made. Use before uploading to Snorkel platform.
---

# Task ZIP Validator

Validate and auto-fix a Terminus 3 task ZIP before Snorkel upload. This skill catches the issues that cause CI failures and reviewer rejections, based on the current portal documentation plus empirical submission feedback.

## Input

A single argument: path to a `.zip` file (absolute or relative).

```
/task-zip-validator workspace/submissions/tbrain-my-task.zip
```

## Workflow

> ⚙️ For an UNZIPPED task folder, run `scripts/preflight.sh <task-dir>
> --strict --report-json workspace/reports/<slug>/preflight.json`
> (repo root) first — it covers the mechanical subset below (layout,
> .dockerignore entries, Dockerfile hygiene, task.toml fields, leak sweep,
> zip arcnames, rubric format, docker oracle/nop, noexec-/tmp repro) in one
> command; this skill then focuses on the judgment checks (category shape,
> instruction/test symmetry, template shape).

1. **Unzip** to a temp directory
2. **Structural audit** — check every file against rules
3. **V3 evidence inferability** — recreate or locate the external schema-v3
   manifest, run two fresh task-visible fairness reviews, and pass
   `sufficiency_manifest_check.py --require-v3`
4. **Auto-fix** — apply fixes for known issues
5. **Oracle + Nop** — run harbor tests if Docker available
6. **Quality panel audit** — review `coherent_contract`,
   `correct_reference_solution`, `protected_ground_truth`, `sound_verifier`,
   and `deterministic_execution`; `Minor` and `Major` block on every axis
   except `protected_ground_truth`, where only `Major` blocks
7. **Report** — summarize findings and fixes
8. **Re-zip** — if fixes applied, create updated ZIP

The compatibility-named V3 evidence manifest is intentionally absent from the ZIP. Look first for
`workspace/reports/<slug>/instruction-sufficiency.json`. If it is unavailable,
rebuild schema version 3 from the extracted instruction/environment/tests using
`terminus-regular-task-authoring/references/instruction-sufficiency-gate.md`.
Do not mark a ZIP ready merely because every test has a passer: coverage and
solver success cannot certify goal clarity or evidence inferability. Conversely,
do not require every inferred semantic rule to appear in `instruction.md`.

### Verifier-integrity review (manual, blocking when violated)

Read the verifier before auto-fixing it. `tests/` may legitimately run the
candidate, parse output, consume golden fixtures/hashes, check invariants, or
use sealed held-out truth. It must not contain a callable that maps task inputs
to the complete expected artifact; move that end-to-end logic to `solution/`.

When the task says the candidate must read a variable config or input file,
change one meaningful config value and re-run the verifier. The verifier must
read it dynamically and reject a candidate that hardcodes the original value.
Do not flag hardcoded expected results, tolerances, or format constants unless
they replace values the instruction says come from that file.

Reject verifier truth loaded or derived from `/app`, a mutable corpus, or any
other agent-writable tree. Goldens and held-out fixtures belong in the separate
verifier image. Do not manually stage whole agent-controlled directories:
symlinks can turn protected fixture contents into apparent candidate output;
declare exact top-level artifacts and let the harness transfer them instead.
If the verifier executes agent-supplied code, drop privileges before exec with
`--no-new-privs` or equivalent and confirm that process cannot read goldens,
hidden fixtures, or `/logs/verifier`. Do not place expected answers in a parent
tree of an input path passed to that process; demotion stops writes, not reads.

For each domain rule explicitly named by the contract, require an isolating
fixture whose expected result changes when that rule alone is inverted. A
coarse multi-rule wrong solution or mixed held-out corpus is insufficient, and
held-out data cannot be the sole enforcement of a stated rule.

Scan every Python file under `tests/` for temporary interpreter permission
changes. Resolve and deduplicate targets before recording modes; specifically,
`/bin/bash` and `/usr/bin/bash` may resolve to one executable. Restore each
saved mode once from `finally`, then verify complete Oracle reward/log
collection. This blocking platform preflight is not run by `stb harbor check`.

Assert at the specificity of the instruction: exact comparison is required for
byte-exact or otherwise pinned output, but exact undocumented wording is invalid.
When the instruction states a numeric tolerance, enforce that same band. When it
defines an optimization objective or tie-break, include a case that rejects a
merely feasible or differently optimized answer and spot-check the Oracle there.

## Step 1 — Unzip and Identify

```bash
ZIPFILE="$1"
TMPDIR=$(mktemp -d)
unzip -q "$ZIPFILE" -d "$TMPDIR"
cd "$TMPDIR"
```

Verify ZIP root structure. Good (files at root):
```
instruction.md
task.toml
environment/
solution/
tests/
```

Bad (nested folder):
```
tbrain-my-task/instruction.md    ← extra parent folder
```

If nested, note for re-zip fix.

## Step 2 — Structural Checks

### 2a. task.toml (BLOCKING)

Parse with `tomllib`. Required structure:

```toml
artifacts = ["/app/output.json"]
name = "task-name"

[metadata]
author_name = "anonymous"
author_email = "anonymous"
difficulty = "frontier"       # frontier | advanced | core | base
category = "Software"         # one of the 7 Title Case categories below
subcategory = "Systems"       # exactly one matching taxonomy value
languages = [...]             # task implementation languages; exclude verifier-only Python
tags = [...]                  # 3-6 values
expert_time_estimate_hours = N
difficulty_explanation = "..."
solution_explanation = "..."
verification_explanation = "..."
relevant_experience = "..."

# If using docker-compose:
# is_multi_container = true    # only if >1 service

[verifier]
timeout_sec = N
environment_mode = "separate"
network_mode = "no-network"

[agent]
timeout_sec = N                # 1800-18000
network_mode = "no-network"

[environment]
network_mode = "public"        # required on every task
build_timeout_sec = N
cpus = N
memory_mb = N
storage_mb = N
```

Valid categories and subcategories are the exact Title Case values below:
```
Science: Biology, Chemistry, Physics, Earth, Robotics, Math, Linguistics
Software: Algorithms, Systems, Databases, Data engineering, Frontend, Languages
ML: Training, Inference, Evaluation, Kernels
Operations: Finance, Logistics, Supply chain, Claims, Compliance, Marketing
Security: Cryptography, Reverse engineering, Forensics, AppSec
Hardware: CAD, RTL
Media: Music, Design
```

> ✅ All seven Terminus 3 categories are open as of 2026-07-31. Pick the category
> for the domain the task lives in, not merely the fact that code is written.

> ⛔ The CI `template_detection` static check (first observed 2026-07-13) BLOCKS
> submissions whose structural shape matches a named template library entry —
> confirmed: `rust_cli` (`Matches known template 'rust_cli' (llm_fallback,
> confidence 0.85). Rework the task so it is not templated.`). Heuristic to flag
> as a manual BLOCKER-risk: `environment/repo` is a minimal single-source-file
> project (one `main.rs`/`main.go`/etc. + manifest + README), the graded binary
> is a stdin→stdout batch pipe, the instruction says to extend a starter/stub,
> and the verifier compares against a hidden vector corpus. Judges SHAPE, not
> prose; assume per-language sibling templates. Remediation levers UNVERIFIED —
> see AGENTS.md §9.

**Checks:**

| Check | Rule | Auto-fix |
|-------|------|----------|
| `artifacts` | Required top-level array; every verifier input path must be declared | ❌ manual |
| per-phase `network_mode` | `[environment]` must be `"public"`; `[agent]` and `[verifier]` must each declare `"public"` or `"no-network"` | ✅ set environment public; add agent/verifier only when task intent is unambiguous |
| `difficulty` | Must be `frontier`, `advanced`, `core`, or `base` and match measured accuracy | ❌ manual |
| `environment_mode` | `[verifier].environment_mode` must be `"separate"` | ✅ set to separate |
| `agent.timeout_sec` | Must be between 1800 and 18000 seconds | ❌ manual |
| `languages` | Must list task/oracle implementation languages, not verifier-only Python | ❌ manual |
| `languages` casing | Values must be LOWERCASE slugs (`"rust"`,`"go"`,`"c"`,`"typescript"`), never `"Rust"`/`"Go"` | ✅ lowercase them |
| `tags` | Must contain 3-6 values | ❌ manual |
| `category` / `subcategory` | Exactly one valid Title Case pair from the Terminus 3 taxonomy | ❌ manual |
| `is_multi_container` | If compose has >1 service → must be `true` | ✅ add flag |
| removed fields | Reject Terminus 2 fields such as `codebase_size`, `number_of_milestones`, `subcategories`, `allow_internet`, and `junior_time_estimate_min` | ✅ remove |

### 2b. Dockerfile (BLOCKING)

Check `environment/Dockerfile`:

| Check | Rule | Auto-fix |
|-------|------|----------|
| Digest pin | Every external `FROM` must end in `@sha256:<64hex>`; canonical `FROM image:tag@sha256:<digest>` is valid and expected, while a plain floating `FROM image:tag` is not | ❌ manual (need to pull digest) |
| Numeric `COPY --chown` | Every Dockerfile must use numeric IDs such as `--chown=0:0` or `--chown=1000:1000`; named users fail the cloud builder | ✅ replace when the intended UID/GID is known |
| Digest-only image `COPY --from` | External image refs must be `image@sha256:<digest>`, never `image:tag@sha256:<digest>`; stage aliases remain valid | ❌ manual |
| Canonical final-stage base | Final stage must use a **canonical Terminal-Bench base image** (digest-pinned) when one matches the task's language, OR a non-canonical base with a brief credible justification in the `Dockerfile`/`README.md`. Canonical refs: Python `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`, Node `…/node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383`, Go `…/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac`, Rust `…/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36`, Java `…/eclipse-temurin:21-jdk-jammy@sha256:25d1276565738d3c805e632a4542c3a7598866ef967f4def6544c15de3a74b14`, GCC `…/gcc:13-bookworm@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c`, Ruby `…/ruby:3.3-slim-bookworm@sha256:e76733e94b3a5893e4a141024ef3a583dc10781dc24becebf74f9c9f9a33e3df`, Maven `…/maven:3.9.9-eclipse-temurin-21@sha256:3a4ab3276a087bf276f79cae96b1af04f53731bec53fb2e651aca79e4b10211e`, Debian `…/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d`, Ubuntu `…/ubuntu:24.04@sha256:0d39fcc8335d6d74d5502f6df2d30119ff4790ebbb60b364818d5112d9e3e932`. Builder stages may use any task-appropriate toolchain image. | ❌ manual |
| **tmux + asciinema REQUIRED** | MUST be in apt-get install. Missing either = ALL agent runs fail with zero output. | ✅ add to apt-get |
| No COPY tests | NO `COPY tests/` or `COPY solution/` | ✅ remove line |
| No reserved dirs | NO `mkdir /tests`, `/oracle`, `/logs/verifier`, `/solution` | ✅ remove line |
| apt hygiene | `apt-get update && apt-get install ... && rm -rf /var/lib/apt/lists/*` in one RUN | ❌ manual |
| `patch` installed | For Go/Rust tasks: `patch` must be in apt-get install list | ✅ add to apt-get |
| No `# syntax=` line | NO `# syntax=docker/dockerfile:1` line — platform build nodes can't pull the frontend → "Oracle failed" (preflight.sh checks this) | ✅ delete line |
| No `--mount=type=bind` | NO BuildKit `RUN --mount=type=bind` — convert to plain `COPY` + `rm -rf` in the same layer | ❌ manual (convert to COPY + rm) |
| `set -uo pipefail` | test.sh must have `set -uo pipefail` (not `-e`) | check |
| No privileged/dangerous caps | docker-compose must NOT use `privileged: true`, `cap_add` of `SYS_ADMIN`/`NET_ADMIN`/`SYS_MODULE`, or mount `/var/run/docker.sock`; volume mounts must not shadow reserved paths (`/logs/artifacts`, `/logs/verifier`, `/tests`, `/solution`) | ❌ manual |

**Agent image vs verifier image:** `environment/Dockerfile` builds the agent
environment and must never copy `tests/` or `solution/`. `tests/Dockerfile`
builds the isolated verifier, must be digest-pinned, must bake in
`pytest`, `pytest-json-ctrf`, and every verifier-only dependency with exact pins,
must `COPY . /tests/`, and must create the parent directory for every declared
artifact path. Do not put dependency wheels under `tests/`, and do not install
packages in `tests/test.sh`.

For Hardware / CAD submissions, additionally apply
`docs/creating-tasks/cad-task-guidelines.md`: every stated dimension must be
measured on built geometry; sampling spacing must be finer than the tolerance;
through/repeated/exact-count features must be covered; the Oracle solid must be
independently measured; free pose/construction choices must pass; and any
parametric requirement must be exercised by changing a fresh value,
recomputing, and measuring the changed part.

### 2c. .dockerignore (WARNING → auto-fix)

Must exist at `environment/.dockerignore` with ALL of:
```
.git
**/.git
.gitignore
.env
solution/
tests/
**/__pycache__/
**/*.pyc
**/.pytest_cache/
**/.mypy_cache/
**/.ruff_cache/
**/node_modules/
```

`solution/`, `tests/`, and `.env` are mandatory (AGENTS.md §10): missing them
passes local harbor (NOP=0, Oracle=1) but gets reviewer-returned;
`scripts/preflight.sh` FAILs on each.

**Auto-fix**: create/overwrite with standard content (including `solution/`,
`tests/`, `.env`, `**/.git`).

### 2d. test.sh (BLOCKING)

Check `tests/test.sh`:

| Check | Rule | Auto-fix |
|-------|------|----------|
| Uses pytest | Contains `pytest` command | ❌ manual |
| Uses `-rA` | pytest called with `-rA` option | ✅ add flag |
| `set -uo pipefail` | Must have `set -uo pipefail` (not `-e`) | ✅ fix |
| Canonical reward block | Must capture pytest status immediately (`rc=$?`) or branch on `$?` immediately; `rc=$?` is preferred | ✅ rewrite |
| No `cd /app` | WORKDIR handles this — `cd /app` is not in canonical template | ✅ remove |
| No runtime setup | No `apt-get`, `pip install`, `npm install`, `curl`, or `wget` in test.sh | ✅ remove |
| CTRF output | Uses `--ctrf /logs/verifier/ctrf.json` | ✅ add flag |

**Canonical test.sh template** (auto-fix target):
```bash
#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier
python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
rc=$?
if [ "$rc" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
```

The current portal explicitly requires no `set -e` and no trailing `exit`.
End on `fi`: pytest's status is captured, while a failed reward write remains
visible as an infrastructure error. If the published Terminus 3 skeleton differs,
the skeleton wins and the discrepancy must be reported.

### 2e. Dependency wheels and root pyproject

Dependency wheels under `tests/` are blocker-level client feedback issues.
Root-level `pyproject.toml` is not part of the submission allowlist and should
not be included in the ZIP.

```bash
find tests -name '*.whl' -print
test -f pyproject.toml && echo "FAIL: root pyproject.toml should not be submitted"
```

**Auto-fix**: remove wheels from `tests/`; remove root `pyproject.toml` from
the submission package.

### 2f. Secret-shaped files (WARNING)

Scan `environment/` for:
```bash
find environment/ -type f \( -name '*.pem' -o -name '*.key' -o -name '*.crt' -o -name 'id_rsa*' \)
```

**Auto-fix**: delete them (after checking no test depends on them).

### 2g. AI scaffolding files (WARNING — High severity in reviewer checklist)

Scan `environment/` for AI-generated framework files:
```bash
find environment/ -type f \( -name 'CLAUDE.md' -o -name 'skills.md' -o -name '.cursorrules' -o -name '.cursor' -o -name 'AGENTS.md' -o -name 'copilot-instructions.md' \)
```

**Auto-fix**: delete them.

### 2h. Junk files

Scan for and remove:
```bash
find . \( -name '.DS_Store' -o -name '._*' -o -name '__MACOSX' -o -name '__pycache__' \
  -o -name '.ruff_cache' -o -name '.pytest_cache' -o -name '.mypy_cache' -o -name '*.pyc' \)
```

**Auto-fix**: always delete.

### 2i. Build context size (BLOCKING)

```bash
# Total environment/ must be <= 100 MiB
du -sm environment/ | awk '{if ($1 > 100) print "FAIL: environment/ is "$1"MiB (max 100)"}'

# No single file > 50 MiB
find environment/ -size +50M -exec echo "FAIL: {} exceeds 50MiB" \;
```

### 2j. Blacklisted databases

Scan for commercial database references:
```bash
grep -rl 'sqlserver://\|oracle://\|db2://' environment/ 2>/dev/null
```

**Auto-fix**: remove offending files if they're CI/workflow configs (e.g., `.github/workflows/`).

## Step 3 — Instruction Audit (per docs/understanding-tasks/prompt-styling.md)

The instruction_check LLMaJ reviewer applies "state the problem, not the solution." Every finding below maps to a real CI/reviewer rejection pattern.

Fast first pass — run the shared mechanical scanner, then audit the content rules manually:

```bash
scripts/python3 .agent/skills/terminus-regular-task-authoring/scripts/instruction_preflight.py <unzipped-task-dir>
```

### 3a. Structure and style (BLOCKING — instruction_check)

| Check | Rule | Detect |
|-------|------|--------|
| Avoid heavy markdown | Avoid multiple heading levels, excessive bold/bullets. A few headers OK if content is substantive. Flag ≥3 heading lines. | `grep -c "^#"` |
| No numbered steps | No `### Step 1`, `1.`, `2.` walkthrough | `grep -cE "^[0-9]+\.\s\|^### Step"` |
| Absolute paths only | All file refs use `/app/...`, never `app/` or `./` | `grep -E "\bapp/" \| grep -v "/app/"` |
| No task name in text | Task slug doesn't appear in instruction | check slug |
| No canary strings | No `CANARY_STRING`, UUID-like tokens, or marker strings | grep |
| No emojis | No emoji characters | regex |
| Narrative paragraphs | Reads like a bug report, not bullet-list spec | manual |
| Length | 1-3 paragraphs, < 20 "must"/"should" items | count |

### 3b. No solution leaks (BLOCKING — instruction_check)

| Check | Rule | Detect |
|-------|------|--------|
| No issue URLs | No `github.com/...` URLs | grep |
| No PR numbers | No `#1234`, `PR #`, `pull/` | grep |
| No commit hashes | No 7+ hex strings that look like SHAs | grep |
| No function signatures | No `func name(args)`, no `def name(args):` | grep |
| No code snippets | No triple-backtick code blocks showing fix | grep ``````` |
| No implementation steps | No "Add X field", "Modify Y function", "Change Z to W" | manual |
| No internal names | No unexported function/variable names from the fix | compare with fix.patch |
| No upstream test names | No `TestSomething`, `test_something` from upstream | compare with repo tests |
| No pitfall/trap emphasis | No "where a naive X goes wrong", "the tricky/subtle parts are", "a few points bear emphasis", "getting it wrong is easy", "worth calling out". Points the solver at the traps (no-hints violation) and makes it easier. For spec/conformance tasks, delegate rule detail to the named standard ("per RFC 9535 / UAX-14, treat it as authoritative") and let the solver find the hard parts. | `grep -inE 'naive\|goes wrong\|bear emphasis\|tricky\|worth calling out\|getting (it\|them) wrong'` |
| No verifier/test mention | Instruction never references the grader: no "the verifier", "the tests check/lean on", "the verifier expects" | `grep -inE '\bverifier\b\|the tests\b'` |

### 3c. V3 contract/evidence completeness (BLOCKING)

Every behavior asserted by `tests/test_outputs.py` must map either to the
explicit success surface or to an evidence-backed inference family:

1. Read `test_outputs.py` and list each distinct asserted behavior.
2. Require paths, public API/schema, exact consumer-visible strings, and
   arbitrary constants in `instruction.md` or a realistic visible source.
3. For semantic rules, verify the schema-v3 report cites sufficient visible
   evidence; do not require the final derived rule to be copied into the prompt.
4. Flag oracle-only policy, unobtainable facts, or representation overfit.

Common gaps:
- Tests assert a specific error message string → instruction must mention it
- Tests check a public non-target mode → instruction should make its preservation scope clear
- Tests check a specific API/method name → instruction must mention it when it is a required public API

### 3d. No meta-language (WARNING)

| Check | Rule |
|-------|------|
| No "solve.sh" | Don't mention oracle/solution files |
| No "test.sh" | Don't mention test infrastructure |
| No "task.toml" | Don't mention task metadata |
| No "verifier" | Don't mention the verification system |
| No "rubric" | Don't mention scoring |
| No edition/framework metadata | Don't mention task packaging or verifier structure |

### 3e. Content prescriptiveness (WARNING — instruction_check)

The instruction should describe WHAT is broken and WHAT the fix should achieve, NOT HOW to implement it. Flag:

- "Add a `fieldName` field to the struct" → prescribes implementation
- "Use `atomic.Bool` to track state" → prescribes implementation
- "The fix should track whether X is expected" → prescribes strategy
- "Modify `functionName` to check X" → prescribes location + approach

Rewrite recommendations:
- BEFORE: "The mux should track whether a response is currently expected"
- AFTER: "Unexpected global responses should be silently discarded"
- BEFORE: "Add validation during parsing so that if a critical header appears in an unprotected header, parsing is rejected"
- AFTER: "The library should reject JWS/JWE tokens where critical headers appear in unprotected position"

### 3f. Instruction/test symmetry cross-check

For each Python test function in test_outputs.py:
1. Read the docstring
2. Identify the behavior being tested
3. Verify instruction.md covers that behavior

For each requirement in instruction.md:
1. Identify the claimed behavior
2. Verify at least one test covers it

Report:
- Tests with no instruction coverage → **add to instruction or remove test**
- Instructions with no test coverage → **add test or remove from instruction**

### 3g. Environment spec files anti-bypass (WARNING — High severity)

Scan `environment/**/*.md` and `environment/**/README*` for:
- Step-by-step implementation guides
- "How to fix" sections
- Solution hints that bypass instruction.md
- Content that reads as task instructions rather than real engineering docs

Environment docs must read like real engineering documents, not solution walkthroughs. Flag and report for manual review.

**Auto-fix**: Cannot auto-fix — report findings for manual review.

## Step 4 — Code Quality

### 4a. Ruff

```bash
cd "$TMPDIR" && ruff check tests/test_outputs.py
```

**Auto-fix**: `ruff check --fix tests/test_outputs.py`

### 4b. Python syntax

```bash
<repo-root>/scripts/python3 -m py_compile tests/test_outputs.py
```

### 4c. TOML syntax

```python
import tomllib
tomllib.load(open("task.toml", "rb"))
```

## Step 5 — Harbor Tests (if Docker available)

```bash
stb harbor run -a oracle -p "$TMPDIR" -o "$JOBS_DIR" --job-name validate-oracle -q   # Must return 1.0
stb harbor run -a nop -p "$TMPDIR" -o "$JOBS_DIR" --job-name validate-nop -q         # Must return 0.0
```

Use the current Snorkel CLI surface for both Harbor and real-agent runs; see
`task-harbor-runner` for triage and credential handling.

## Step 6 — Report and Re-zip

Print summary table:

```
=== Task ZIP Validation Report ===

| Check                    | Status | Auto-fixed |
|--------------------------|--------|------------|
| task.toml structure      | ✅     | -          |
| artifacts top-level      | ✅     | -          |
| verifier separate mode   | ✅     | YES        |
| per-phase network_mode   | ✅     | -          |
| category/subcategory     | ✅     | -          |
| docker-compose flags     | N/A    | -          |
| Dockerfile digest pin    | ✅     | -          |
| Canonical base image     | ✅     | -          |
| Cloud COPY syntax        | ✅     | -          |
| tmux + asciinema         | ✅     | -          |
| tests/Dockerfile         | ✅     | -          |
| CAD geometry review      | ✅/N/A | -          |
| artifact landing dirs    | ✅     | -          |
| test.sh canonical form   | ✅     | YES        |
| .dockerignore            | ✅     | YES        |
| verifier deps in image   | ✅     | -          |
| secret files             | ✅     | YES (3)    |
| AI scaffolding files     | ✅     | YES (1)    |
| build context size       | ✅     | -          |
| blacklisted databases    | ✅     | -          |
| ruff                     | ✅     | YES        |
| instruction style        | ⚠️     | MANUAL     |
| instruction/test symmetry| ✅     | -          |
| env spec anti-bypass     | ✅     | -          |
| Oracle                   | 1.0    | -          |
| Nop                      | 0.0    | -          |

Fixes applied: 6
```

If any fixes were applied, re-zip:
```bash
TASK_NAME=$(basename "$ZIPFILE" .zip)
cd "$TMPDIR"
zip -rX "${ZIPFILE}" instruction.md task.toml environment solution tests \
    -x '*.DS_Store' -x '__MACOSX/*' -x '*/__pycache__/*' -x '*/.git/*' -x '*.pyc'
```

## Rubric Reminder

After upload to Snorkel, remind the user to create a rubric in the platform UI:
- Use a flat `Agent ...` criterion list.
- Include at least **one negative-reward criterion**.
- Format: `"Agent <did/did not> <observable action>, +/-N"`
- Allowed scores: `{+1, +2, +3, +5, -1, -2, -3, -5}` only
- **Positive scores need an explicit leading `+`** (write `+3`, not `3`); unsigned positives are sent back for revision
- Total positive points: 10–40
- Rubrics grade trace-evidenced engineering behavior, not the final pytest result.
  Keep criteria task-specific and diagnostic; avoid generic meta-checks such as
  reading instructions, and include validation/recovery actions only when they
  are meaningful for this task.
- Do NOT reference tests, verifier logic, `test.sh`, `test_outputs.py`,
  `/tests/`, hidden tests, CI, reward files, pytest results, metadata, or
  instruction items

## Common CI Failures (auto-detect and fix)

Top recurring CI failures from empirical data:

1. **verifier isolation** — missing `tests/Dockerfile`, `environment_mode = "separate"`, top-level artifacts, or artifact landing directories
2. **verifier deps** — missing pinned pytest/pytest-json-ctrf in `tests/Dockerfile` or runtime installation in test.sh
3. **FROM not digest-pinned** — missing `@sha256:` suffix
4. **check_modal_dockerfile_compat** — named `COPY --chown=` IDs or an external-image `COPY --from=` ref that is not digest-only
5. **check_sanctioned_base_images** — final stage uses a non-canonical base with no (or vague) justification; or uses a different digest/registry than the canonical entry for that language (e.g. bare `golang@sha256:…` instead of the canonical `public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d…`)
6. **ruff errors** — unused imports, ambiguous variable names
7. **secret files** — .pem/.key/.crt in environment/
8. **missing .dockerignore** — or incomplete exclusions
9. **instruction_check** — headers, solution hints, prescriptive language
10. **reward section** — test.sh doesn't use canonical `$?` pattern
11. **blacklisted databases** — MSSQL/Oracle/DB2 references in repo files
12. **AI scaffolding files** — CLAUDE.md, .cursorrules in environment/
13. **build context size** — environment/ exceeds 100MiB or single file >50MiB
14. **root pyproject.toml** — remove from submission ZIP
15. **Terminus 2 metadata** — stale difficulty/category/network/milestone fields remain

## Go-specific Checks

For Go tasks (detected by `languages = ["go"]` in task.toml):

- `patch` must be in Dockerfile apt-get install
- `go.mod` and `go.sum` must exist in `environment/repo/`
- Dockerfile should have `COPY repo/go.mod repo/go.sum /app/` before `COPY repo/ /app/`
- `ENV PATH` or symlink for the Go binary (`ln -sf /usr/local/go/bin/go /usr/local/bin/go` — platform login shells reset PATH)
- No `.github/workflows/` directories (may contain blacklisted DB references)
- For Go tasks, the canonical base IS the full `golang` image: `public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac` (covers all Go 1.21–1.26 + alpine/bullseye/bookworm). A single-stage final image using THIS exact ref passes `check_sanctioned_base_images` — no exemption needed. A bare `golang@sha256:<other digest>` or a different registry/tag is **blocked**; replace the digest with the canonical one.
