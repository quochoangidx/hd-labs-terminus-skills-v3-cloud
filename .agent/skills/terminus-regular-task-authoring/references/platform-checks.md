# What the platform actually checks

Build to this list. A local gate that checks something not on it is internal
hygiene: useful when it is cheap, never a reason to rework a task that meets
everything below.

Sources: `docs/` (cited) and the platform's own returned reports. The
pre-difficulty check names below come from returned reports. They do **not**
appear in `docs/`, so the returned report is their only authority. When a return
names a check that is missing here, add a row, and add a cheap static mirror only
if one can reproduce it without false positives.

Legend for **Local mirror**: a script and rule name, or `judgment` when only a
reader can decide it (the single reviewer, or your own read before upload).

## 1. Static and CI checks (block on error)

| Check | Local mirror | Source |
|---|---|---|
| task.toml required fields, under `[metadata]` where descriptive | `task-policy.py` task.toml:* | ci-checks-reference.md; task-components.md |
| `artifacts` top-level; `environment_mode = "separate"` | task-policy task.toml:artifacts / separate-verifier | ci-checks-reference.md |
| timeouts ≤ 18000 (agent ≥ 1800 is a reviewer criterion) | task-policy task.toml:agent-timeout | ci-checks-reference.md |
| `network_mode` in all three phases, environment `public` | task-policy *-network-mode | task-requirements.md |
| absolute paths in instruction.md | `judgment` (no mirror yet) | ci-checks-reference.md "Instructions" |
| every file tests read or write is named in instruction.md | `judgment` | ci-checks-reference.md |
| instruction.md and solve.sh screened for AI-generated text | `task-llm-style-audit` (advisory) | ci-checks-reference.md |
| every `FROM` digest-pinned; sanctioned base or credible justification | task-policy *-dockerfile:digests / final-base | dockerfile-best-practices.md |
| no `FROM --platform=` | task-policy *-dockerfile:no-platform-pin | ci-checks-reference.md |
| pip pinned with `==`; apt **not** pinned | task-policy verifier pinned-deps / *-dockerfile:apt-unpinned | ci-checks-reference.md |
| bare `nproc` (severity not stated) | task-policy *-dockerfile:no-bare-nproc (warn) | ci-checks-reference.md |
| cloud-builder COPY syntax; no local `ADD` | task-policy *-dockerfile:modal-syntax | ci-checks-reference.md |
| `environment/` ≤ 100 MiB, no file > 50 MiB | task-policy environment:size | dockerfile-best-practices.md |
| compose: no networks, no privileged/caps/docker.sock | task-policy environment:compose-* | ci-checks-reference.md |
| tests/ and solution/ absent from the agent image | task-policy agent-dockerfile:no-hidden-copy | ci-checks-reference.md |
| verifier tooling baked into tests/Dockerfile, nothing installed in test.sh | task-policy test.sh:no-runtime-setup | ci-checks-reference.md |
| `--ctrf /logs/verifier/ctrf.json` | task-policy test.sh:ctrf | writing-tests.md |
| canonical test.sh shape; no `exit $?` after `fi` | task-policy test.sh:*; review_task test-sh-ending | reviewer-checklist.md |
| dual bash-path permission restore | verifier_static_checks interpreter | ci-checks-reference.md |
| ruff | review_task ruff | writing-tests.md |
| no canary strings | preflight leak:canary | task-requirements.md |
| ZIP holds task files, no wrapper folder | preflight zip:*; review_task zip-structure | submission-checklist.md |
| Oracle passes (3 runs), NOP fails | preflight docker:oracle / nop / determinism | oracle-agent.md; nop-agent.md |

## 2. Pre-difficulty quality checks (named in returned reports)

Blocking in the returned report: every row whose Local mirror is not `advisory`.
The first four were reported as passes but are the expertise, solvability and
novelty gates the docs describe.

| Check | What it asks | Local mirror |
|---|---|---|
| `verifiable` | fixed pytest run, deterministic, no LLM judge | preflight determinism |
| `solvable` | the reference solves it, plausible time estimate | preflight docker:oracle |
| `difficult` | needs genuine domain expertise (docs: blocking) | `judgment`; review_task difficulty-explanation-* |
| `novel` | not a known public task | `judgment` |
| `outcome_verified` | tests judge outputs, not how the fix was made | `judgment` |
| `anti_cheat_robustness` | ground truth unreachable from the agent image | preflight verifier:unprivileged-candidate; harness-bypass wrong path |
| `task_security` | no exfiltration, destructive or obfuscated code | `judgment` |
| `functional_verification` | no grepping candidate source | `judgment` |
| `deterministic_reproducible` | pinned images and packages, no live services | task-policy digests / pinned-deps |
| `test_instruction_alignment` | every instruction promise has a test, and vice versa | panel_precheck `named_cases`; `judgment` for the rest |
| `agentic` | needs exploration, not one-shot generation | `judgment` |
| `separate_verifier_configured` | verifier inputs and tooling baked into tests/Dockerfile | task-policy separate-verifier / copy-tests |
| `environment_hygiene` | no tests/solution in the agent image; test-only deps only in tests/Dockerfile | task-policy agent-dockerfile:no-verifier-deps / no-hidden-copy |
| `structured_data_schema` | exact output schema documented | `judgment` |
| `typos` | none in paths, identifiers, commands | `judgment` |
| `category_and_tags` | taxonomy fits the domain | task-policy taxonomy:pair |
| `no_extraneous_files` | every file is used | preflight leak:stray-files (warn) |
| `verifier_execution_isolation` | candidate demoted, sealed trees, reward by root after | preflight verifier:unprivileged-candidate / reward-dir-mode |
| `ctrf_reporting` | per-test CTRF at the collected path | task-policy test.sh:ctrf |
| `do_not_modify_enforced` | every "do not modify" is enforced if it confers an advantage | `judgment`; review_task verifier-trusts-candidate-driver |
| `binary_reward` | reward is only 0 or 1 | task-policy test.sh:reward-footer |
| `interesting`, `essential_difficulty`, `reviewable`, `instruction_concision`, `solution_quality`, `*_explanation_quality` | reported, not blocking in the observed return | `judgment` |

## 3. Quality panel (blocks difficulty measurement)

Five axes. Minor and Major block on every axis except `protected_ground_truth`,
where only Major blocks. Advisory never blocks. A defect proven by execution
becomes Major. The panel generates its own plausible wrong implementations and
runs them, so a suite that kills only the builder's wrong paths is not enough;
see `scaffold-five-axis-checklist.md`. Source: quality-panel-judge-guide.md.

## 4. After the panel

- Difficulty: 8 runs (4 per model); a new submission needs at least 3 failures.
  Source: difficulty-guidelines.md.
- Human review: any failed High rejects the task, and one failed Medium sends it
  back. Source: reviewer-checklist.md.
- Rubric: edited in the platform UI; only an empty rubric blocks (Sep 22).
  Source: reviewer-checklist.md.

## Explicitly not required (do not gate on these)

- anonymous author fields
- a missing `--no-new-privs` alone
- `schema_version` in task.toml
- `is_multi_container`, `gpus` or `docker_flags` for a single-container task
- a trailing `exit` in test.sh
- a declared difficulty that differs from the measured tier
- instruction length (guidance, not a cap)
- rubrics.txt or README.md in the ZIP (the platform adds both)
- internal receipts of any kind

The platform receives only the ZIP, the rubric, the task.toml explanation fields
and, on resubmission, a revision note. Sources: task-components.md,
quality-panel-examples.md C-3, review-guidelines.md, submission-checklist.md.
