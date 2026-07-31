---
name: task-clone
description: "Use when transforming a mined candidate into a Terminus Regular task under workspace/tbrain-* folders, including closed upstream bugfix candidates and explicit category-profile candidates across all nine Regular categories. Consumes mined_candidate artifacts when available, avoids re-mining GitHub, applies prompt sanitization, repo slimming, behavioral verifier design, oracle creation, and Harbor validation. All nine Regular categories are open; the declared category must match the visible primary activity."
---

# Task Clone

Use this skill when the user wants to turn a mined candidate into a hard Terminus Regular task. Candidates may be upstream bugfixes or explicit category-profile tasks. Preserve the artifact's category unless it is invalid or the task's visible primary activity clearly belongs to another category.

Preferred split:

```text
mine = candidate discovery + scoring only
clone = transformation + packaging only
```

If a mined candidate artifact exists, consume it and do not repeat the mining pass unless required fields are missing.

## Core Rule

Task folder names must be:

```text
tbrain-<problem-slug>
```

Task folders must be created under the workspace directory:

```text
workspace/tbrain-<problem-slug>/
```

Do not include repo/tool/domain filler in the slug. Prefer the behavior or bug:

- Good: `tbrain-maxfail-teardown-reporting`
- Good: `tbrain-timezone-cutoff-reconciliation`
- Good: `tbrain-async-cancel-cleanup`
- Bad: `tbrain-pytest-maxfail-teardown-reporting`
- Bad: `tbrain-django-async-cancel-cleanup`

Exception: keep a domain word only when it is part of the actual problem concept, not just the source repo name.

Name-shape dedupe (mandatory, RELATIVE — no fixed banned-word list): name the
task after the domain problem a real team's ticket would describe, never after
the lever/mechanism it was built from. The check is against the CURRENT
portfolio, not a word list: before creating the folder, grep
`mined-candidates/index.jsonl` and the gallery snapshot for the slug's final
noun and overall shape; if a similar name already appears ≥2 times, pick a
different name (and, for synthetic tasks, a different domain skin). Identical
suffixes signal near-duplicate tasks to reviewers even when the logic differs —
the 2026-07 portfolio accumulated eight `tbrain-*-ledger` tasks this way, but
the over-used word will drift over time; trust the grep, not any remembered
list. Varying the name grammar across a batch helps too.

## Inputs

Accept any of:

- a `mined_candidate.json` or equivalent compact artifact
- a GitHub issue URL
- a GitHub PR URL
- `owner/repo` plus a requested domain
- a rough task idea plus a source repo

If a source URL is given without a mined artifact, browse or use `gh` only enough to verify it is closed/merged and identify the fixing PR/commit. Do not perform broad mining inside clone.

## Mined Artifact Contract

When available, clone should start from:

```yaml
candidate:
  category:
  gallery_category:        # canonical gallery name (Title Case) — goes into tags, NOT task.toml category
  subcategory:             # gallery leaf — slugged into tags
  subsubcategory:          # gallery leaf — slugged into tags
  subcategories:           # the 5 cross-cutting subtypes
  target_difficulty:       # hard | medium (never easy; Python => hard)
  expected_codebase_size:  # minimal | small | large — recompute from environment/ before shipping
  closest_gallery_task:
  gallery_novelty:         # novel | twist-on-existing | duplicate (duplicate => do not clone)
  subtype_profile:         # per-subtype details (tool/mock_plan/db_engine/…) when a subtype is set
  objective_type:
  source_url:
  issue_or_pr_id:
  repo:
  base_commit:
  parent_commit:
  fixing_commit:
  task_slug:
  bug_signature:
  touched_files:
  subsystem_tags:
  runtime_class:
  external_requirements:
  repro_summary:
  current_pipeline_summary:
  target_behavior:
  required_work:
  input_fixtures:
  output_contract:
  bad_behavior:
  expected_behavior:
  preserved_behavior:
  edge_cases:
  difficulty_rationale:
  reasoning_bottlenecks:
  tempting_partial_fixes:
  why_not_debugging:
  test_surface:
    primary_api:
    secondary_apis:
    constructor_contracts:
    offline_fixtures:
    skip_guard_policy:
  scoring:
    subsystem_interaction:
    deterministic_reproducibility:
    offline_viability:
    anti_shortcut_hardness:
    verifier_complexity:
    runtime_cost:
    leakage_risk:
  patch_shape_gate:        # pass | fail — fail means not Hard-eligible, do not clone as Hard
  patch_shape_evidence:
  family_key:              # library + bug_family, for the family ledger
  agent_probe:             # {ran, passed_oneshot} — blind-probe evidence backing the difficulty claim
```

If this exists, inspect only touched files, focused upstream tests, and support files needed to stage/build/run the task. Do not rescan large repo history or re-open unrelated issues.

If the artifact is missing `test_surface` details for a secondary implementation
that tests will cover, fill that gap before writing verifier tests. Do not guess
constructor signatures from class names.

For non-debugging category-profile artifacts, treat `category`, `target_behavior`,
`required_work`, `input_fixtures`, and `output_contract` as the source of truth.
Do not rewrite the task as a bugfix just because the source has issues or PRs.

## Dedupe Registry

Before cloning, check:

```text
mined-candidates/index.jsonl
```

If a shared team registry exists, check it too. Treat any matching `repo + fixing_commit`, `repo + issue_or_pr_id`, `repo + bug_signature`, `category + source + task_slug`, or `repo + base_commit + target_behavior` with status `claimed`, `cloned`, or `submitted` as already taken unless the user explicitly wants a variant.

During clone, update or append a compact JSON line:

```json
{"category":"debugging","repo":"pytest-dev/pytest","issue_or_pr_id":"14465","source_url":"...","fixing_commit":"...","parent_commit":"...","bug_signature":"maxfail session fixture teardown reporting","task_slug":"tbrain-maxfail-teardown-reporting","status":"cloned","rejection_reason":null}
```

Use `bug_signature` for near-duplicate detection when issue and PR URLs differ but the fix is the same behavior.

## Candidate Selection

For upstream bugfix candidates, prefer:

- a real bug, not docs-only text
- a fix that changed tests upstream
- 50-500 meaningful LOC, or a smaller fix involving subtle cross-module behavior
- deterministic local reproduction
- no live credentials, no external service, no network needed at runtime
- at least two interacting subsystems

For category-profile candidates, prefer:

- a clear category-primary activity, not a cosmetic label
- a target behavior that can be stated without source issue/PR leakage
- deterministic offline verifier inputs and outputs
- enough existing code/config/data for real discovery work
- at least four focused verifier assertions covering variants and preservation

Reject all candidates that are:

- docs-only, typo-only, dependency bump, CI-only, release metadata
- single-line validation or obvious message change
- tiny one-file patches where the likely solution is one branch or one flag check
- tasks whose verifier cases are mostly variants of the same condition
- too broad to isolate into one task
- impossible to test offline in Docker
- likely to pass current frontier agents in one shot

For Python Hard tasks, the final task must realistically target `difficulty = "hard"`.

## Workflow

1. Load the mined artifact or verify the source URL with the smallest needed browse/`gh` pass.
2. Gate the category shape before scaffolding: `implement` / `parse` / `render`
   / `cmp`, public API or stub completion, and exact-reference conformance usually
   belong to `software-engineering`; ETL/dataset→report pipelines usually belong
   to `data-processing`; diagnosis and repair usually belong to `debugging`.
   All three categories are open, so use the honest label instead of reshaping the
   prose. Record `category_mismatch_<predicted_slug>` when the artifact's declared
   category disagrees with its visible primary activity.
   In the same gate, check the TEMPLATE shape: the CI `template_detection` check
   (first observed 2026-07-13) blocks submissions matching a named template —
   confirmed `rust_cli` = minimal single-source-file stub project, stdin→stdout
   batch binary, "extend the starter" instruction, hidden vector-corpus verifier,
   `codebase_size = minimal`; assume per-language siblings. Scaffold away from
   that shape from the start (realistic multi-module repo, in-repo tests,
   domain-authentic file I/O); if flagged anyway, mark
   `template_detection_<template_name>` and see AGENTS.md §9 for current
   (UNVERIFIED) remediation levers.
3. Choose the parent commit before the fix for upstream bugfixes, or the artifact's `base_commit` for category-profile tasks.
4. Create `workspace/tbrain-<problem-slug>` using the naming rule.
5. Stage the repo or focused subset under `environment/repo`, not by runtime network fetch.
6. Slim the repo to task-relevant modules, support utilities, fixtures, and minimal build config.
7. Write sanitized `instruction.md` from observable behavior only, then run the real-user prompt test before building the verifier.
8. Write `task.toml` using `version = "2.0"`, `number_of_milestones = 0`, `allow_internet = false`, the artifact's valid category/subcategories, and realistic resources.
9. Write `environment/Dockerfile` with digest-pinned `FROM`, `tmux`, `asciinema`, `bash`, useful search/edit tools, and required pinned deps.
10. Write `solution/fix.patch` and `solution/solve.sh` that apply a generalized fix and rebuild if needed.
11. Write behavioral `tests/test_outputs.py` and offline `tests/test.sh`.
12. Validate baseline: nop fails for the intended reason only; oracle passes all verifier tests.
13. Run structural checks, CI checks, and optional real-agent trials.
14. After behavior and validation are stable, write reviewer-facing Difficulty,
    Solution, and Verification explanations outside the task folder.

## Regular Layout

```text
workspace/tbrain-<problem-slug>/
├── instruction.md
├── task.toml
├── environment/
│   ├── .dockerignore
│   ├── Dockerfile
│   └── repo/
├── solution/
│   ├── solve.sh
│   └── fix.patch
├── tests/
│   ├── test.sh
│   └── test_outputs.py
└── reports/                    # optional local notes; exclude from ZIP
    └── mining_notes.md
```

For a small app task, `environment/app/` is acceptable, but cloned upstream bug tasks should normally use `environment/repo/`.

Prefer external notes under `workspace/reports/<task-slug>/` when possible so submission zips do not accidentally include them.

For the current platform submission form, create:

```text
workspace/reports/<task-slug>/submission-explanations-source.md
workspace/reports/<task-slug>/submission-explanations.md
```

Never place these files under the submitted task root.

## Metadata Defaults

Use artifact category/subcategories first. For upstream bugfix artifacts with no category, default to `debugging` and `["tool_specific"]`. For non-debugging category-profile artifacts, do not use the bugfix default.

`category` MUST be one of the 9 kebab values below — NOT the gallery's Title Case name. The platform `task.toml` schema has only `category` (9), `subcategories` (the 5 subtypes) and `difficulty`; it has NO subcategory/subsubcategory field. If the artifact records the gallery's 3-level placement (`gallery_category`/`subcategory`/`subsubcategory`, see `mined-candidates/gallery_taxonomy.md`), carry that placement into `tags` (a slug of the chosen subsubcategory) so the task still lands under the right gallery leaf — do not put it in `category`.

```toml
version = "2.0"

[metadata]
author_name = "anonymous"
author_email = "anonymous"
difficulty = "hard"
category = "<artifact.category (one of the 9 kebab values below) or debugging for upstream bugfix; NOT the gallery Title Case name>"
subcategories = ["<artifact subcategories, or tool_specific for upstream bugfix>"]
number_of_milestones = 0
codebase_size = "<minimal|small|large>"   # compute from env file count; CI enforces this, do NOT default to small
languages = ["<main implementation language>"]
tags = ["<3-6 useful tags; include a slug of the gallery subcategory/subsubcategory when the artifact records one>"]
expert_time_estimate_min = 60
junior_time_estimate_min = 180

[verifier]
timeout_sec = 600.0

[agent]
timeout_sec = 1800.0   # CI hard cap: agent.timeout_sec must be 1-1800 (do not raise above 1800 for heavy builds)

[environment]
allow_internet = false
build_timeout_sec = 1800.0
cpus = 2
memory_mb = 4096
storage_mb = 10240
```

> **✅ CATEGORY AVAILABILITY (updated 2026-07-30).** All nine Regular-task
> categories accept net-new submissions until further notice; new milestone tasks
> remain blocked. The category classifier check is looser, but the declared label
> must still match the task's visible primary activity.
>
> Apply the activity mapping honestly: exact-reference/public-API/stub-completion
> work normally belongs to `software-engineering`; dataset/report/ETL work belongs
> to `data-processing`; diagnosis and repair belong to `debugging`. Historical
> blocked-category outcomes are calibration evidence only, not current blockers.
>
> Pick an accurate gallery-leaf tag after any reshape: a pattern matcher that
> classifies given paths is *Pattern Extraction & Regex Matching*, NOT *File
> Discovery & Search* (which implies walking a real filesystem).

Valid categories are only:

```text
system-administration
build-and-dependency-management
data-processing
games
software-engineering
machine-learning
debugging
security
scientific-computing
```

Valid subcategories are only:

```text
long_context
tool_specific
api_integration
db_interaction
ui_building
```

Python tasks must be hard. `codebase_size` may be `minimal`, `small`, or
`large`; choose the honest size from useful files under `environment/` and aim
for a portfolio mix instead of forcing every task to one size.

**CI enforces `codebase_size` mechanically** from the file count under
`environment/` EXCLUDING `Dockerfile`/`docker-compose*`: `minimal` = 0-19,
`small` = 20-199, `large` = 200+. A mismatch is a blocking error
(`run_static_checks.py`). Compute it, never default:
```bash
find <task>/environment -type f ! -name Dockerfile ! -name "docker-compose*" | wc -l
```

`languages` should list the main language(s) the agent works in or the oracle
solution changes. Do not include Python solely because the verifier is written
in pytest. Use LOWERCASE slugs: `["rust"]`, `["go"]`, `["c"]`, `["typescript"]`
— NOT `["Rust"]`/`["Go"]` (reviewers return capitalized values; the docs examples
are all lowercase).

**`[environment].workdir` is MILESTONE-ONLY.** Do NOT set `workdir` in a
non-milestone (`number_of_milestones = 0`) `task.toml` — the container working
directory comes from the Dockerfile `WORKDIR /app`; a stray `workdir` line gets
flagged. (Docs `task-components.md`: `workdir = "/app"  # Milestone tasks only`.)

⚠️ The der-canonical-codec reference `task.toml` predates these two rules — it
ships `languages = ["Rust"]` AND `[environment] workdir = "/app"` in a
non-milestone task. Both are WRONG; do not copy them. Confirmed 2026-07-01 by a
platform reviewer on a Rust task.

## Rubric quality (rubric is entered in the UI, NOT in the ZIP — see task-zip-submit)
Reward the END STATE, not the process. Do NOT add criteria for "reads/studies the
stub before starting", "compiles successfully with `cargo build`/`go build`"
(compilation is a prerequisite implied by any output), or "verifies by running the
binary on samples" — a reviewer strips these as process-not-state. Keep only
behavioral end-state positives plus the required >=3 negative criteria, and make
the max-score comment match the real positive sum. Confirmed 2026-07-01: a task
shipped 3 such process lines (34 positives) and the reviewer cut them to 27.

## Instruction Style

After writing or editing `instruction.md`, run the mechanical pre-flight and
fix every finding (structure, length, hint phrases, leakage) before the first
platform check:

```bash
python3 .agent/skills/terminus-regular-task-authoring/scripts/instruction_preflight.py <task-folder>
```

Write like a real engineer describing the requested observable work:

- 1-3 short FLOWING paragraphs — never a spec sheet. Do NOT use `## Input` /
  `## Output` / `## Build` (or any similar) section headers, format tables, or
  bulleted "rules" lists. The platform `instruction_check` reviewer flags a
  section-structured instruction as a "design document that prescribes
  implementation" and warns even after the rule enumeration is removed (confirmed
  twice, 2026-06-21: rule-free-but-sectioned still warned; the prose rewrite
  cleared it). Weave the stdin/stdout format, constraints, and the build note
  into narrative sentences that explain *why* each part matters. When the
  behaviour follows a known standard or tool, reference it ("the result must
  match `git check-ignore`") instead of restating its rules.
- Before the first platform check, run the `instruction_check` binary preflight
  in `terminus-regular-task-authoring` (Prompt Rules). The escape hatches for a
  flip-flopping verdict, test-pinned literals, and custom output formats live in
  `.agent/skills/task-miner/lever_patterns.md` (L1 step 8): ship the non-blocking
  ⚠️ when the flagged items are test-pinned, use natural JSON + a semantic
  verifier instead of a bespoke byte format, and move unavoidable disclosures
  into an in-env reference file with a one-line pointer.
- Absolute paths only, such as `/app` and `/app/src/module.py`.
- State observable contract and exact user-facing strings only if tests assert them.
- No issue URLs, PR numbers, test names, rubrics, or solution hints.
- No step-by-step implementation guide.
- No task name in the prompt.
- No canary strings.
- Apply the real-user prompt test to every sentence: would a developer who did
  not already know the solution naturally include this detail? If the detail is
  useful mainly because it points to the fix path, remove it or restate it as an
  observable requirement.
- If tests require a secondary implementation that is not obvious from the
  public behavior, name the relevant module or file path without giving the
  exact patch. This is allowed instruction sufficiency, not a solution hint.

**Do not narrate the internal mechanism or root cause (the #1 client reject,
June 2026 trial feedback).** The most common rejection is a prompt that "gives
away the solution": it explains how the code is wrong internally, or which code
path is already correct, so the agent only has to read the prompt rather than
reason about the code. Describe the OBSERVABLE symptom a real user would hit and
the DESIRED outcome; let the agent find the cause and the fix.

- Cut "Right now the parser does X internally" sentences. State the observable
  instead: not "the parser ignores the algorithm name and trusts the embedded
  curve" but "a key labeled `nistp384` that actually carries a `nistp256` curve
  is accepted."
- Cut "the other path already handles it" tells (e.g. "the ordinary callback
  enforces this but the new one does not"). They point the agent at where to
  copy the fix from. State only that the behavior is missing where the user
  observes it.
- Cut fix-shaped requirements that restate the implementation (e.g. "reject a
  line whose host field begins with `@`"). State the requirement behaviorally
  ("reject a line with more than one marker or an unknown marker").
- Litmus test: if a sentence would be strange for a user who did NOT know the
  fix to write, it is a hint. If removing a sentence makes the task unsolvable,
  it was probably a hint, not a requirement.
- KEEP test-asserted contracts that are genuine spec, even when specific:
  thresholds (`> 8192 bits`, `2048` rounds, `160`-bit), the public API the tests
  drive, named exempt contexts, and every preservation/edge case a test checks.
  These satisfy instruction/test symmetry. The goal is to remove root-cause and
  implementation narration, not the behavioral contract.

Prompt sanitizer must remove:

- issue URLs, PR numbers, commit hashes
- upstream test names and fixture names copied from the PR
- internal helper/function names unless they are public API
- implementation guidance such as "change `nextitem`" or "edit `runtestprotocol`"
- benchmark meta language such as verifier, oracle, hidden tests, rubric, or CI

Environment files must not smuggle the solution:

- README, config, scripts, comments, TODOs, and source files must not contain
  step-by-step walkthroughs, procedural hints, or commented solution plans.
- `spec.md`, README, and architecture docs may define schemas, protocols, API
  contracts, or business rules, but they must describe what is required, not
  how to implement the fix.
- Do not split the task's prompt/goals out of `instruction.md` into
  environment docs to satisfy length limits. Supporting docs should look like
  realistic engineering artifacts, not LLM-style prompt extensions.

Good bugfix shape:

```md
The package in `/app` mishandles <scenario>. A user who <does normal workflow> currently sees <bad observable behavior>.

Fix it so `<public command or API>` <observable result>. The run should still <preserve important behavior>, and <edge case contract>.
```

Good non-debugging shape:

```md
The tool in `/app` needs to produce <target artifact or behavior> from <input surface>. Implement support for <public command/API/workflow> so it follows <observable contract>.

The output must <format/schema/order/tolerance requirements>. Preserve <existing mode or compatibility behavior> for <normal workflow>.
```

## Docker Rules

`environment/Dockerfile` must:

- use `FROM ...@sha256:<digest>` on every stage
- use a **canonical Terminal-Bench base image** for the final runtime stage when
  one matches the task's language (exact digest-pinned refs):
  - Python: `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
  - Node: `public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383`
  - Go: `public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac`
  - Rust: `public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36`
  - Java (JDK): `public.ecr.aws/docker/library/eclipse-temurin:21-jdk-jammy@sha256:25d1276565738d3c805e632a4542c3a7598866ef967f4def6544c15de3a74b14`
  - C/C++ (GCC): `public.ecr.aws/docker/library/gcc:13-bookworm@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c`
  - Ruby: `public.ecr.aws/docker/library/ruby:3.3-slim-bookworm@sha256:e76733e94b3a5893e4a141024ef3a583dc10781dc24becebf74f9c9f9a33e3df`
  - Maven: `public.ecr.aws/docker/library/maven:3.9.9-eclipse-temurin-21@sha256:3a4ab3276a087bf276f79cae96b1af04f53731bec53fb2e651aca79e4b10211e`
  - Debian: `public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d`
  - Ubuntu: `public.ecr.aws/docker/library/ubuntu:24.04@sha256:0d39fcc8335d6d74d5502f6df2d30119ff4790ebbb60b364818d5112d9e3e932`

  A non-canonical base is allowed ONLY with a brief, credible justification (as a
  `Dockerfile` comment or in the task `README.md`) — e.g. a runtime the list
  doesn't cover. Missing/vague/boilerplate justification, or one that matches an
  existing canonical entry, is **blocked** by `check_sanctioned_base_images`.
- **languages without a canonical base = canonical Debian/Ubuntu base + a pinned
  apt toolchain, NOT a third-party language image.** Lua, PHP, Perl, OCaml,
  Haskell (ghc), Erlang/Elixir, Common Lisp (sbcl), SWI-Prolog, R and similar all
  install offline from apt in the same clean transaction as `tmux`/`asciinema`,
  which keeps `check_sanctioned_base_images` green with no justification needed;
  Fortran rides the canonical gcc image (gfortran included). The login-shell
  PATH, warm-build, and cache-retention rules below still apply — sanity-check
  with `bash -lc 'which <tool>'`. Do NOT introduce pre-1.0 / fast-churn
  toolchains (Zig, Nim, Crystal, V): frontier agents emit version-skewed code
  there, yielding timeout/0/N tooling failures instead of difficulty. New
  languages beyond the apt lane are added lazily per the expansion policy in
  `lever_patterns.md` ("Widen the language axis").
- install `tmux`, `asciinema`, `bash`, and usually `util-linux`
- include practical agent tools such as `git`, `ripgrep`, and `sed`/`coreutils` when the base image lacks them
- **expose the language toolchain on `/usr/local/bin`.** The agent runs in a LOGIN
  shell that resets PATH to `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`
  and drops any Docker `ENV PATH` additions. The Go image keeps `go`/`gofmt` in
  `/usr/local/go/bin` and the Rust image keeps `cargo`/`rustc` in `/usr/local/cargo/bin`,
  neither of which is on that login PATH, so the agent cannot invoke the compiler
  even though oracle/nop can (they run in a non-login shell with PATH intact).
  Symlink them: Go `RUN ln -sf /usr/local/go/bin/go /usr/local/bin/go && ln -sf /usr/local/go/bin/gofmt /usr/local/bin/gofmt`;
  Rust `ln -sf /usr/local/cargo/bin/cargo /usr/local/bin/cargo && ln -sf /usr/local/cargo/bin/rustc /usr/local/bin/rustc`.
  Confirmed 2026-07-01: a Go task omitted this and ~3/10 agent trials failed with
  "no Go toolchain, unable to compile", scoring 0 for a pure environment reason
  while oracle stayed green. Verify with
  `docker run --rm --entrypoint bash <img> -lc 'command -v go'`.
- **initialize a git repo in the task workdir** (after the final source `COPY`)
  so the agent's edit tooling works. Many agents apply edits via `git apply` and
  self-check with `git diff`; if the cloned repo's `.git` was stripped (and
  `.dockerignore` excludes `.git` from the build context anyway), `/app` is NOT
  a git repo at runtime, `git apply` silently fails, `git diff` shows nothing,
  and agents that understood the fix perfectly still score 0 (confirmed June
  2026: a grpc-go task got 0/3 agent trials purely because patches never landed,
  flagged "Some tests not passed by any agent run"). Add after the source COPY
  and build:
  ```dockerfile
  RUN git init -q \
      && git config user.email task@example.com \
      && git config user.name task \
      && git add -A \
      && git commit -q -m "initial task state"
  ```
  This runs inside the image (not the build context), so it does not trip the
  `check_dockerfile_hygiene` `.git`-in-context warning. Oracle/nop are unaffected
  (oracle applies `fix.patch` with `patch -p1`, not git).
- install build tools only when the agent must rebuild source
- **warm the build during image build whenever the agent must rebuild** (any
  compiled or heavy-build language — Rust, Go, C/C++, TypeScript, Java, Scala).
  Run one full build of the *unmodified* repo in the Dockerfile so every
  dependency is fetched and compiled and the build cache is populated; the
  agent's post-edit rebuild is then incremental (seconds), not cold (minutes).
  e.g. `RUN cargo build --tests`; `RUN go build ./... && go vet ./...`;
  `RUN npm ci && npm run build`; configure + `make` for autotools/CMake. A cold
  per-edit rebuild is the #1 cause of the Agent Timeout Gate (see that section).
- **put the language toolchain on the agent's LOGIN-shell PATH by symlinking it
  into `/usr/local/bin`** — the agent runs in a login shell that resets PATH to
  the default and DROPS Docker `ENV PATH=...` additions, so a toolchain under
  `/usr/local/cargo/bin` (Rust), `/usr/local/go/bin` (Go), or `${JAVA_HOME}/bin`
  (Java) is invisible to the agent and causes wasted steps / timeouts even
  though oracle/nop pass (they run as non-login subprocesses inheriting the
  image ENV). e.g. `RUN ln -sf /usr/local/cargo/bin/cargo /usr/local/bin/cargo`
  (+ `rustc`); `ln -sf /usr/local/go/bin/go /usr/local/bin/go`;
  `ln -sf "${JAVA_HOME}/bin/javac" /usr/local/bin/javac`. `node`/`gcc` images
  already place tools in `/usr/local/bin`. Sanity: `bash -lc 'which <tool>'`.
- pin Python/package dependencies exactly
- avoid `COPY tests/` and `COPY solution/`
- avoid creating `/tests`, `/oracle`, `/solution`, or `/logs/verifier`
- work with `allow_internet = false` at agent/verifier runtime
- avoid heredocs and opaque generated source in the Dockerfile; store source as
  files and `COPY` it
- use one clean apt transaction per stage with `--no-install-recommends` and
  remove `/var/lib/apt/lists/*`
- pin downloaded binaries by version and checksum; avoid `curl | sh`
- order layers from stable manifests/dependencies to volatile task source
- extract copied archives during build and remove the archive in the same stage
- avoid broad recursive `chmod -R` or `chown -R`; use targeted `COPY` metadata
- keep package-manager caches, compiler caches, and unused build outputs out of
  the final image — **exception:** when the agent must rebuild, KEEP the
  warmed build/dependency cache (`target/`, `GOCACHE`, `node_modules`,
  `~/.cargo/registry`, `~/.cache`, etc.) so the agent's rebuild stays
  incremental. Solvability under the timeout gate beats image slimness here, and
  `check_no_build_tools_in_final_image` already permits the toolchain for
  rebuild-required tasks. Strip only caches the agent will never reuse.

Do not add root-level `pyproject.toml` as a submission artifact. If local ruff
or editor tooling needs to exclude `environment/repo`, keep that configuration
outside the submitted task or remove it before packaging.

Remove macOS junk and secret-shaped files:

```bash
find <task> \( -name '.DS_Store' -o -name '._*' -o -name '__MACOSX' \) -print
find <task>/environment -type f \( -name '*.key' -o -name '*.pem' -o -name '*.crt' -o -name 'id_rsa*' \) -print
find <task>/environment -type f \( -name 'CLAUDE.md' -o -name 'skills.md' -o -name 'AGENTS.md' \) -print
```

Do not leave AI-framework scaffolding filenames such as `CLAUDE.md`,
`skills.md`, or similar files in `environment/`.

## Agent Timeout Gate

The platform runs ~10 real-agent trials and **blocks the task (`❌`) when more
than the threshold (~5) of them hit `agent.timeout_sec` without finishing** —
e.g. `Agent Timeout Gate: ❌ 10/10 real-agent runs timed out (threshold: 5)`.
This is a hard blocker, **not** a difficulty signal: a task where most agents
never even produce a fix is treated as a broken/too-heavy environment, not as
legitimately Hard. Hard must come from wrong or partial fixes, not from agents
starving on tooling.

Root cause is almost always that the agent burns its 30-minute budget on **cold
tooling** instead of reasoning: rebuilding a large project from scratch on every
edit, navigating an un-slimmed tree, or waiting on a slow test suite. It then
gets only one or two edit→build→test cycles and never converges. Prevent it
at build time:

- **Warm the build in the Dockerfile** so the agent's post-edit rebuild is
  incremental, not cold (see the Docker Rules bullet above). This is the single
  biggest lever.
- **Keep the warmed build/dependency cache in the final image** (the explicit
  exception in Docker Rules). A warm Dockerfile build is wasted if the cache is
  stripped before runtime.
- **Budget the edit→build→test cycle.** A solving agent needs ~8–12 iterations
  inside 1800s. Time one *warm* cycle locally (edit one source file, rebuild,
  run the focused test). If a single warm cycle still exceeds ~2–3 min, the task
  will trip the gate — slim further, shrink the test, or reject the candidate.
- **Slim the repo** so navigation and `grep`/`rg` are cheap (see
  `upstream-repo-sanitizer`); a multi-thousand-file tree wastes agent steps
  before any reasoning starts. Keep `codebase_size` honest.
- **Keep the verifier fast** — focused reproducer tests with short
  per-subprocess timeouts, never a full upstream suite
  (`terminus-hard-python-verifier`).
- Set `agent.timeout_sec = 1800` (the cap) for any build-involving task; the
  default already is. You cannot buy more than 30 min, so the fix is a faster
  cycle, not a bigger timeout.

Pre-check before spending real-agent budget — time the warm oracle cycle:

```bash
stb harbor run --force-build -a oracle -p <task-folder>   # build the image once
time stb harbor run -a oracle -p <task-folder>            # reuse cached image: this ~= the agent's per-cycle cost
```

The oracle does *less* than a solving agent (it applies a known patch and runs
the focused test — no exploration). If the cached-image oracle run is already a
large fraction of 1800s, real agents will certainly time out. Treat a slow
oracle as an early timeout-gate warning and warm/slim the build before running
agents.

## Oracle Pattern

For cloned repo tasks:

```bash
#!/bin/bash
set -euo pipefail

cd /app
patch -p1 < /solution/fix.patch
python -m pytest <focused smoke test or upstream regression>
```

If the project requires build artifacts, rebuild them in `solve.sh`. The patch must solve the general bug, not only verifier examples.
For non-debugging category-profile tasks, the patch must implement the general
target behavior, not only the concrete verifier fixtures.

## Verifier Pattern

`tests/test_outputs.py` should create temporary reproducer projects or inputs and run the target externally.

**Verifier tests MUST be supplied by the verifier at verify time, NEVER staged
inside `environment/repo`.** A compiled-language reproducer (a `*_test.go`,
`.rs`, `.exs`, `.java`, etc.) must either be embedded as a string in
`test_outputs.py` and written into `/app` at verify, or shipped under `tests/`
and copied into `/app` at verify (overwriting whatever is there). If the test
file lives in `environment/repo`, the agent can edit or delete it and the
`/app` working tree the agent gets is non-deterministic across trial instances
-- confirmed 2026-06-14: an h2 task staged its `concurrency.rs` in
`environment/repo` and ran it directly; some agents altered it, so the
verifier found the tests present in some instances and absent in others, which
the reviewer flagged as **Task Instruction Sufficiency: FAIL** (1/9 trials
passed). The agent fixes only the source; the verifier brings its own tests, so
the prompt need not name any test file or function -- name only a new public
API symbol the test must call (see Instruction Style).

**Re-check the RESOURCE is novel before scaffolding a conformance-style task.**
The named-suite universe (WHATWG / Unicode UTS-UAX / RFC CTS / JSON-Schema /
TOML toml-test …) is small and SHARED across teammates, so a slug-distinct task
built over the SAME official suite is still a duplicate. Before cloning, confirm
the artifact's `conformance_suite`+`spec` is not already `claimed`/`submitted`
in `mined-candidates/index.jsonl` (human mirror: the L1 claimed-resource ledger
in `.agent/skills/task-miner/lever_patterns.md`). If it is taken, STOP and
re-target the same lever onto a fresh spec+suite rather than cloning — learn the
pattern, not the resource.

**Expected-output DATA is a test vector too -- keep the answer key out of
`environment/repo`.** For conformance-style tasks graded against an official
suite, the `(input, expected-output)` vector table lives ONLY under `tests/`
(embedded in `test_outputs.py` or a `tests/*.json` data file the verifier reads).
NEVER commit the answer table into `environment/repo` -- e.g. a `cases.rs` /
`vectors.json` plus a repo `selftest` subcommand that a verifier test invokes.
The agent reads the shipped repo, so a repo-embedded answer table hands over the
expected outputs and the task collapses to trivial. If you want a fast in-process
full-suite check, feed the vectors from a `tests/` file into the binary at verify
time (or have the binary read a path under `tests/`); do not compile them into the
shipped crate. Before shipping, grep the repo for answer-shaped data:
`grep -rlE 'expected|TEST_CASES|÷|<the exact output token>' <task>/environment/repo`.
Confirmed 2026-07-01: a UAX-14 line-break task shipped `src/cases.rs` with all
19338 `(input, expected ÷/× marker)` vectors so a repo `selftest` could check them
-- that leaked the entire answer key; the fix was to move the check to the hidden
`tests/` vectors and delete the repo table.

**Structure conformance corpora for union-not-intersection difficulty (the
"Some tests not passed by any agent run" gate is BLOCKING).** Score per-case
(parametrized tests) or in graded bands whose top band a best realistic run can
actually reach; never ONE monolithic all-N-cases-must-pass function — a single
universal blind spot then turns that whole test 0/N and the task gets returned.
Before shipping, drop or disclose (one prose sentence) any case EVERY fresh
implementation would miss; keep hardness as many independent quirk families
each solver misses a different slice of. Full remediation decision tree when
the flag fires anyway: `.agent/skills/task-revise-flag-remediation/SKILL.md`
(design-time rules: `lever_patterns.md` L1 step 5).

Use real parsers for JSON/XML/CSV. Assert behavior, not source shape.

Verifier matrix for upstream bugfixes must include:

- direct upstream regression
- boundary or ordering edge case
- normal behavior preservation
- anti-shortcut check
- **one discriminating test per independent criterion the instruction lists.**
  If the prompt names N separate reject/accept conditions (e.g. reject modulus
  >8192 AND prime >4096 AND exponent malformed), a verifier covering only one
  lets an agent add a single check and pass — reviewers flag this Critical. Each
  test must DISCRIMINATE: the input must be ACCEPTED by the buggy code and
  REJECTED only by the fix. Watch for a downstream validator (e.g. `rsa.Validate`
  / `pk.Validate()`) that already rejects malformed inputs on the buggy build —
  that makes the test pass on both nop and oracle (a dud). Isolate each criterion
  with an OTHERWISE-VALID input that violates only the target bound (e.g. a real
  RSA key with one prime >4096 but modulus ≤8192; a valid key with a large odd
  exponent). Some criteria a validator already enforces (even exponent, e<3)
  cannot be made discriminating — do not add them as duds.
- no internal crash/traceback when the expected behavior is recoverable
- output format/schema check when relevant

Verifier matrix for category-profile tasks must include:

- primary target behavior from `instruction.md`
- at least one edge case not identical to the main example
- existing behavior preservation
- semantic output parsing or artifact inspection
- anti-shortcut variation in names, ordering, values, or fixture layout
- category-specific contract checks such as schema, build artifact, service health, security exploit failure, numeric tolerance, metric threshold, or game-state transition

Every test function needs a docstring. Every asserted behavior must be present in `instruction.md`.

Preservation tests are not exempt from prompt coverage. If a verifier checks that non-target modes, aliases, fallback paths, legacy layouts, or normal behavior still work, `instruction.md` must say so naturally.

Example:

```md
Fix the `--import-mode=importlib` collection case. Keep the existing `prepend` and `append` import modes working for the same shadowed-layout projects, and preserve assertion rewriting for nested package tests.
```

Anti-shortcut tactics:

- use temporary directories and generated project names
- vary filenames, ordering, or input values across tests
- include one unseen variant not present in the upstream PR
- avoid exact source-code assertions
- parse outputs semantically rather than matching full files
- never require an EXACT error-message string the instruction does not disclose.
  If discrimination needs distinguishing the fix's rejection from the buggy
  build's rejection (both error), prefer a pass/fail behavioral test (an input
  the buggy build accepts and the fix rejects); else match a loose token from
  the instruction's own vocabulary (e.g. instruction says "round count" → match
  case-insensitive `round`), which accepts any reasonable agent phrasing yet
  still differs from the buggy build's unrelated error. Matching the reference
  solution's exact wording fails functionally-correct agents who phrase the
  message differently (Task Instruction Sufficiency FAIL). Probe the buggy
  error first to confirm the loose token is absent there, and verify a variant
  wording still passes.

The oracle patch must pass the direct regression and at least one variant, proving it is not verifier-targeted hardcoding.

## Verifier API Sanity

Before packaging, run a focused smoke check for every import and constructor
used by `tests/test_outputs.py`.

For each tested API/class, verify:

- the import works in the pinned starting repo
- the constructor call matches the real signature
- the object under test actually owns the method/property being asserted
- skip guards catch only genuine absence, not broken construction or wrong API
- wrappers and raw containers are not confused

Bad pattern:

```python
try:
    from package.platform.response import RawResponse
except ImportError:
    pytest.skip("not available")

resp = RawResponse(wrapper_like_arg, request_method="GET")
```

The `ImportError` guard does not protect against a wrong constructor. If the
class exists, a `TypeError` is a verifier bug. Use the real wrapper class or
remove the secondary-implementation test.

Recommended smoke command before Harbor:

```bash
cd <task-folder>
python3 -m py_compile tests/test_outputs.py
```

Then run oracle and nop. A broken verifier must be fixed before any difficulty
or quality signal is trusted.

## tests/test.sh

Use the canonical test.sh pattern. The `check_test_sh` CI gate accepts the
current reward block shapes documented below, and `WORKDIR` in the Dockerfile
handles the `/app` working directory.

```bash
#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile before running this script."
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi

python3 -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
rc=$?
if [ "$rc" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
```

Always invoke `python3`, never bare `python`: non-Python base images (node, gcc,
rust, go, debian) ship no `python` alias, so `python -m pytest` dies with
`python: command not found` and the oracle silently scores 0 — read
test-stdout first when a working patch scores 0 (confirmed on a node base,
June 2026).

The final reward block must end the script. The current `check_test_sh` gate
accepts either `if [ $? -eq 0 ]` immediately after pytest or the preferred
defensive form above, where `rc=$?` is captured immediately after pytest and
used in `if [ "$rc" -eq 0 ]`. Do not wrap the block in a helper, add extra
commands between pytest and the capture/conditional, or rewrite it as
`pytest && echo 1`.
Do not append `exit $?` or any trailing exit after the final `fi`. Harbor uses
`/logs/verifier/reward.txt`, not the script exit code.

Verifier dependencies must be available before `tests/test.sh` starts. Install
`pytest`, `pytest-json-ctrf`, and verifier-only dependencies in the Dockerfile
with exact pins. `tests/test.sh` should run pytest and write
`/logs/verifier/reward.txt`; it must not install packages or fetch from the
network.

Keep runtime/project dependencies separate from verifier-only dependencies. For
editable installs of the target package, prefer `pip install --no-deps -e .`
after installing pinned deps so project metadata cannot fetch or override
unpinned packages.

## Spec-task gotchas that cost a re-run (2026-06-21, learn these)

When cloning a from-scratch spec-implementation whose oracle is checked against a
real external tool/library (gitignore, chmod, IPv6, quantile, DST, …), four
mistakes each cost a full rebuild this session — avoid them up front:

- **Reference the authoritative external behavior in `instruction.md`; do NOT
  enumerate the rule mechanics.** A prose list of matching rules / a precedence
  table reads to the platform reviewer as a "design specification that prescribes
  implementation" — the `instruction_check` warning and the #1 client reject.
  Instead say "the result must match what `git check-ignore` reports / matches
  `numpy.quantile(method=...)`" and let the tests be the source of truth. This
  ALSO satisfies instruction/test symmetry (the named reference defines
  correctness) without listing internals. Keep only YOUR I/O format + the
  observable contract; drop the mechanics. AND write the whole instruction as
  flowing prose (1-3 paragraphs) — NOT as `Input`/`Output`/`Build` sections:
  `instruction_check` flags rigid spec-section structure as a "design document"
  too, even after the rule tables are gone. Weave the stdin/stdout format into
  narrative sentences that say *why* each part matters (confirmed: a
  section-structured but rule-free instruction still drew the warning; the prose
  rewrite cleared it).
- **Generate ground-truth fixtures with the SAME runtime VERSION the verifier
  uses (inside the task image), never the host.** Baking fixtures from a host
  interpreter can disagree with the in-image one on edge cases (e.g. Python 3.9
  vs 3.11 `ipaddress` on a trailing-colon address), so the oracle passes locally
  but fails in CI. Run the reference in the task's base image (or the exact
  pinned version) when dumping expected values.
- **Pin verifier deps with a hash-locked `requirements.lock` + `pip install
  --require-hashes --no-deps`, for EVERY language's task** (not just Python ones).
  Inline `pip install pytest==x pytest-json-ctrf==y` trips the static-check
  lockfile warning even in a Go/C++/Rust task. Copy a `requirements.lock` into
  `environment/` and install from it. (Reusing an existing task's lock is fine.)
- **Don't make blank/empty input a fixture VALUE if the program skips blank
  lines, and avoid positional-alignment verifiers.** A program that ignores blank
  lines emits no output line for an empty input, which both contradicts an
  "empty -> INVALID" expectation and shifts every later line in an
  index-by-position comparison. Prefer one invocation per case, or assert on a
  parsed mapping, and only test inputs the program actually emits a line for.

## Quality Preflight

Before packaging or platform upload:

- run an instruction/test symmetry audit: every exact string, CLI flag, output key, XML/JSON field, ordering guarantee, and file path asserted by tests must be stated in `instruction.md`
- include preservation/non-regression test coverage in the prompt, including modes not directly part of the bug trigger
- run a verifier API sanity audit for every imported class/function and every
  constructor used in tests
- remove implementation hints, issue URLs, PR IDs, commit hashes, upstream test names, and private helper names from `instruction.md`
- remove hidden walkthroughs, procedural hints, and prompt-bypass instructions
  from environment files, comments, README, configs, scripts, TODOs, `spec.md`,
  and architecture docs
- verify the task root has no `pyproject.toml`
- set `codebase_size` to match the actual `environment/` file count (excluding
  `Dockerfile`/`docker-compose*`): 0-19 `minimal`, 20-199 `small`, 200+ `large`.
  CI rejects a mismatch.
- run `ruff check <task-folder>` over the WHOLE task dir. Platform CI lints
  `environment/repo` too (default E4/E7/E9/F rules), so a non-`ruff`-clean
  upstream dev/codegen `.py` fails the build. Remove non-build-required upstream
  `.py` that has lint errors; fix build-required generators in place
  (output-preserving, e.g. move an `E402` import to the top) and re-run oracle.
  Also clear `F401`/`E741` in `tests/test_outputs.py`.
- verify rubrics do not reference tests, verifier logic, `test.sh`,
  `test_outputs.py`, `/tests/`, hidden tests, CI, reward files, or pytest
  results
- verify `tests/` contains verifier scripts/fixtures only, not dependency
  wheels
- verify `tests/test.sh` does not run runtime setup, `apt-get`, `pip install`,
  `npm install`, or network downloads
- verify Dockerfile does not `COPY tests/`, `COPY solution/`, or create `/tests`, `/solution`, `/oracle`, `/logs/verifier`
- verify Dockerfile uses a canonical final runtime base (or non-canonical with a
  credible justification), has no
  heredoc-generated source files, no tag-only `FROM` image, no unverified
  downloads, no stale copied archives, and no broad recursive permission rewrites
- verify `environment/ <= 100 MiB` and no file under `environment/` exceeds `50 MiB`
- verify `environment/` contains no `.git`, `.env`, credentials, package caches,
  build outputs, or AI-framework scaffolding files such as `CLAUDE.md` or
  `skills.md`
- remove `.ruff_cache`, `.pytest_cache`, `__pycache__`, `.DS_Store`, `._*`, `__MACOSX`, reports, logs, and local notes from the submission ZIP
- run oracle and nop; nop must fail for the intended behavior, not missing deps or setup errors

## Submission Explanation Workflow

Generate submission explanations only after the prompt, oracle, verifier, and
available solve probes are stable.

1. Write `submission-explanations-source.md` from task evidence:
   - Difficulty: interacting concepts, the tempting partial fix, fair semantic
     failure patterns from solve probes, and why the issue requires reasoning
     across more than one local symptom.
   - Solution: root cause, high-level oracle strategy, and preserved behavior.
   - Verification: requirement-to-test mapping, why cases discriminate, and
     actual oracle/nop results.
2. Produce `submission-explanations.md` as the concise UI-ready version.
3. Apply the human-writing rules from `terminus-regular-task-authoring` only as
   an editorial pass. Do not add claims, remove thresholds, or change technical
   meaning.
4. Compare the final version with `instruction.md`, `solution/fix.patch`,
   `tests/test_outputs.py`, and validation reports.
5. Keep both files outside the task ZIP.

Use this structure in both files:

```md
# Difficulty Explanation

...

# Solution Explanation

...

# Verification Explanation

...
```

The final text must not mention LLMs, AI, models, agents, anti-LLM techniques,
detection avoidance, submission guidelines, or reviewer criteria. Although the
form asks why the task is challenging for humans and agents, answer by
describing the intrinsic technical difficulty rather than speculating about a
solver type.

## Quota Discipline

Avoid monolithic end-to-end exploration. After each phase, compress findings into compact notes and stop carrying raw diffs unless needed.

Exploration limits:

- inspect `<= 10` source/test files unless blocked
- inspect `<= 3` commits around the fix
- do not enumerate full repo trees or unrelated test suites
- reuse upstream regression tests as inspiration, but wrap them in behavioral verifier tests

For large repos such as TypeScript, go-ethereum, PyTorch, pandas, or NumPy, use focused staging/sparse extraction and strict runtime checks before investing in verifier/oracle work.

## Validation

Run what is available (full verified CLI surface + infra-failure triage live in
`task-harbor-runner` — notably `harbor tasks check` was removed in 0.7.0, and
agent runs need an explicit `-a terminus-2` because `-a` defaults to oracle):

```bash
stb harbor run -a oracle -p <task-folder>
stb harbor run -a nop -p <task-folder>
stb harbor check <task-folder>
stb harbor run -a terminus-2 -m @openai/gpt-5.5 -k 3 -p <task-folder>   # difficulty, needs approval
```

If Docker is not running, still run static checks:

```bash
python3 -m py_compile <python files>
python3 - <<'PY'
import tomllib
tomllib.load(open("task.toml", "rb"))
PY
```

Before submission, real-agent pass rate must be below 80%; Python tasks should target hard.

Difficulty gate:

- If any frontier reference agent passes `5/5`, treat the task as Medium unless another agent family consistently fails for implementation reasons.
- If aggregate real-agent pass rate is `>= 80%`, do not submit as Hard; re-mine or redesign.
- If the oracle patch is `<= 10` meaningful LOC in one obvious file, require empirical agent failures before keeping it.
- Timeouts count as weak evidence only; a good Hard task should produce wrong/partial fixes, not mostly environment/tooling timeouts.
- A high timeout rate is not Hard — it is a blocker. If `> ~5/10` real-agent runs time out, the platform fails the **Agent Timeout Gate** (`❌`); fix the environment per the Agent Timeout Gate section (warm build, keep the cache, slim, fast verifier), do not submit hoping the timeouts read as difficulty.

## Final Packaging

Zip task contents, not the containing folder:

```bash
cd tbrain-<problem-slug>
find . \( -name '.DS_Store' -o -name '._*' -o -name '__pycache__' -o -name '.ruff_cache' -o -name '.pytest_cache' -o -name '.mypy_cache' \) -print
TASK_NAME="$(basename "$PWD")"
mkdir -p ../submissions
zip -rX "../submissions/${TASK_NAME}.zip" instruction.md task.toml environment solution tests \
    -x '*.DS_Store' -x '__MACOSX/*' -x '*/__pycache__/*' -x '*/.ruff_cache/*' -x '*/.pytest_cache/*' -x '*.pyc'
```

Regular task ZIPs must contain only submission-required files/folders, not root
`pyproject.toml`, `reports/`, `submissions/`, `workspace/`, logs, caches, or
scratch notes.

## Hand-Off

When done, report:

- source issue/PR URL and pinned starting commit
- task folder path
- task slug under `workspace/` and why the name omits repo/domain filler
- tests included and which prompt requirement each covers
- validation commands run and results
- paths to the factual and UI-ready submission explanation files
- any blocked step, especially Docker/Harbor/API key availability
