# Terminal Bench 2.0 — Task Revise Report

> Comprehensive task information extracted from the Snorkel Experts task payload.
> This is the same data that populates the task's right-hand **Revise panel** (Difficulty Explanation, Solution Explanation, checks, rubrics, agent runs, etc.).

## 1. Task Identity & Metadata

| Field | Value |
|---|---|
| Project | `Terminus-3-Prod` |
| Project ID | `a34832f4-76f4-4d2a-aa62-c92deb15675d` |
| Assignment ID | `ecd93580-63c0-498f-b3c6-07d6be4002d7` |
| Task ID | `5576eee5-02b0-40db-b2b7-4130441b597c` |
| Submission ID | `5576eee5-02b0-40db-b2b7-4130441b597c` |
| Task category (stage) | `SUBMISSION` |
| Submission task type | `submission-8d482d68-4d7e-449f-9388-b3cb0cefb643` |
| Review task type | `submission-8d482d68-4d7e-449f-9388-b3cb0cefb643` |
| Form schema revision | `9110301d-4bfc-42cc-8185-74945ca1a856` |
| Skippable | `false` |
| Further revisions allowed | `true` |
| Expiry time | `2027-02-24T15:52:32.992317Z` |

### Task Classification (submission_document)

| Field | Value |
|---|---|
| Difficulty | **** |
| Solvable | `` |
| Task category | `Operations` |
| Task subcategories | `["Claims"]` |
| Task languages | `python` |
| Codebase size | `` |
| Number of milestones | `` |
| Submission AHT (min) | `120` |
| Uses approved canonical base image | `true` |
| Used Task Gallery inspiration | `false` |
| Send to reviewer | `` |
| Generate rubrics | `` |

## 2. Submission Artifact

| Field | Value |
|---|---|
| Filename | `tbrain-workers-comp-disability-benefit.zip` |
| Uploaded at | `2026-09-27T15:33:33.773Z` |
| S3 URI | `s3://daas-blobs/prd/a34832f4-76f4-4d2a-aa62-c92deb15675d/ecd93580-63c0-498f-b3c6-07d6be4002d7/86dbf33c-b3c6-40b0-b98a-9b94c248f08f_submission_2026-09-27T15:33:32.168Z.zip` |
| S3 key | `prd/a34832f4-76f4-4d2a-aa62-c92deb15675d/ecd93580-63c0-498f-b3c6-07d6be4002d7/86dbf33c-b3c6-40b0-b98a-9b94c248f08f_submission_2026-09-27T15:33:32.168Z.zip` |

- **Difficulty-check artifact:** `s3://daas-blobs/codebuild_uploads/autoeval_artifacts/agent_runner/5ac66ac1-1475-4eb3-a248-773b9e03165a/difficulty_check/a9eaf814a2ea/logs_artifact.zip`

## 3. Reviewer Narrative Fields (Right Panel)

### Difficulty Explanation

> *Describe in your own words why your task is challenging for humans and agents to solve.*



### Solution Explanation



### Verification Explanation



## 4. Difficulty Check — Agent Simulation Summary

Overall: **difficulty check not run** (see the summary and quality panel below).

### Agent Performance

| Agent | Accuracy | Runs | Successes | Timeouts | Other failures |
|---|---|---|---|---|---|

### Per-Test Results (pass count across runs)

| Test | Passed / 0 |
|---|---|

### Full Difficulty-Check Text Summary

```
## Pre-Difficulty Gate Failed

Difficulty not run: the submission did not pass every blocking quality or quality panel check. Oracle/NOP already passed. No Opus, GPT, analysis, or rubric-generation runs were started.

QUALITY PANEL: NEEDS REVISION -- 2 blocking issues to fix. Details for each are below.

Blocking (fix every one):
   1. [Sound Verifier] MAJOR: The verifier never grades a register spanning more than 52
      distinct Friday paydays, so an added fixed-size payday guard can reject a contract-valid
      job.
   2. [Sound Verifier] MINOR: All numeric test inputs are a fixed sealed corpus; the only
      runtime variation relabels claims, shuffles claims, and shuffles wage-line order, allowing
      a verifier-specific normalized lookup table instead of a manual implementation.

Checked and clean: Coherent Contract, Correct Reference Solution, Protected Ground Truth,
  Deterministic Execution.

------------------------------------------------------------------------------------------------
DETAILS
------------------------------------------------------------------------------------------------

1. [Sound Verifier] MAJOR -- missing behavioral coverage
   The verifier never grades a register spanning more than 52 distinct Friday paydays, so an
   added fixed-size payday guard can reject a contract-valid job.
   Why this fails:
     Reach: Use one claim injured Monday 2025-01-06, with 53 Friday wage lines of 2,000 cents
     each, dated weekly from 2024-01-05 through 2025-01-03, one valid disability day, no
     earnings, and a rate row effective 2016-01-01 with max 400,000 and min 1,000. The oldest
     line is within 400 days of injury; all lines meet section 1. Flip: A genuine implementation
     that stores or accepts at most 52 distinct paydays and raises an exception on the 53rd
     would fail this job. It would clear the shown comparisons: the 120-line limits fixture
     repeats a small set of Friday dates, while the other listed families do not supply 53
     distinct paydays. The verifier's large-job assertion checks claim and rate-row counts, not
     that payday span.
   Where to look: instruction.md:3-5, environment/app/docs/td-benefits-manual.md:28-35,
     tests/test_outputs.py:391-403, tests/expected/limits_claims.jsonl:2,
     tests/expected/ROSTER:1-24

2. [Sound Verifier] MINOR -- missing behavioral coverage
   All numeric test inputs are a fixed sealed corpus; the only runtime variation relabels
   claims, shuffles claims, and shuffles wage-line order, allowing a verifier-specific
   normalized lookup table instead of a manual implementation.
   Why this fails:
     Reach: check_family loads only rows from the pinned expected files and runs row['job'];
     generated-family variation calls relabel, which copies the job and changes only claim
     labels, claim order, and wage-line order. Flip: a submission can canonicalize each claim by
     sorting wage lines and ignoring the fresh claim label, recognize every fixture
     claim/rate-table signature, emit a hardcoded expected numeric statement with the incoming
     claim label, and preserve incoming claim order. It clears compare because compare only
     checks the resulting JSON values and types. Such a lookup requires knowledge of this
     verifier's hidden corpus, so it falls on the adversarial side of the reachability line and
     is Minor.
   Where to look: tests/test_outputs.py:238-240, tests/test_outputs.py:369-383,
     tests/test_outputs.py:440-447
```

## 5. Quality Check Results

### Quality Check Summary

```
## Quality Check Results
✅ pass - verifiable: tests/test_outputs.py performs deterministic, programmatic, exact-value JSON comparisons (type-strict integer equality) against expectations sealed ahead of time by solution/seal.py+model.py. No LLM-as-judge is used. tests/Dockerfile bakes pytest/pytest-json-ctrf at build time; test.sh performs no runtime network installs.
✅ pass - solvable: solution/fix.patch (applied by solution/solve.sh via `patch -p1`) makes small, targeted changes to payroll.py, rates.py, partial.py and disability.py that I traced line-by-line and confirmed match solution/model.py's rule-by-rule logic (arrears crediting threshold 2,000, divide by 13, RATE_FRACTION=2/3, date-based row_in_force, aww<min early-return, inclusive period_days, WAITING_DAYS=3, half_up rounding of ttd, and the two documented scope decisions for corrections/low partial weeks). The changes are small and mechanically verifiable by an expert in a few hours.
✅ pass - difficult: The task requires precisely parsing a 6-section benefits manual, distinguishing which of several plausible-looking bugs the manual actually rules on versus which behaviors must be left exactly as today's (buggy) code computes them, and getting exact cent-level rounding, date arithmetic, and rate-table selection correct. The differential/scope tests (corrections, low_partial_weeks) specifically punish common over-fixes, making this a genuinely tricky requirements-precision task rather than a routine bugfix.
✅ pass - interesting: This mirrors real work of a workers' compensation claims adjuster/indemnity analyst validating benefit-statement software against a benefits manual; such reconciliation and business-rule-fidelity work is a real paid occupation (per the provided relevant_experience field).
✅ pass - outcome_verified: Instructions describe the end state (statements must follow the manual) and tests grade only the final JSON output of the documented driver command; the one process constraint (leave the driver file unchanged) is a mechanistic anti-cheat measure, not a dictated implementation approach.
✅ pass - anti_cheat_robustness: All ground truth (tests/expected, tests/shipped) lives only in the verifier image (tests/), excluded from the agent image via environment/.dockerignore and never COPYed by environment/Dockerfile. The verifier overwrites /app/tools/tdbenefit_run.py with its own copy before running, executes candidate code as an unprivileged uid via setpriv in isolated sessions, and a dedicated test proves the candidate user cannot read /tests, ROSTER, the shipped copy, or /logs/verifier.
✅ pass - task_security: No malicious code, exfiltration, obfuscation, or prompt injection found in any Dockerfile, script, or test file; all filesystem/permission operations (chown/chmod/setpriv) are directly in service of anti-cheat isolation, not host escape.
✅ pass - functional_verification: Tests execute the driver as a subprocess on real job files and compare structured JSON outputs; no keyword/string scanning of source code is used to grade correctness.
✅ pass - deterministic_reproducible: Base images are digest-pinned, pytest/ctrf plugin versions are pinned, no network is used at agent or verifier runtime, and all graded jobs/expectations are pre-generated and sealed with SHA-256+row-count pinning in ROSTER. Per-run random relabeling of claim names/order does not affect the pass/fail outcome of a correct or incorrect implementation.
✅ pass - essential_difficulty: Difficulty stems from correctly implementing arrears-based wage crediting, base-period math, date-sensitive rate-table lookup, and precise scope judgments about which unstated behaviors to preserve — genuine logical/domain reasoning, not output formatting (the output schema is unchanged from the shipped package and trivial to satisfy).
✅ pass - test_instruction_alignment: Each family test (weeks_pay, base_period, average_weekly_wage, rate_two_thirds, row_in_force, low_wage_rate, disability_days, waiting_period, retroactive_days, ttd_rounding, partial_benefit, etc.) traces directly to a manual rule the instruction tells the agent to follow, and the instruction's symptom list (AWW mismatches, short rates, stale maximum, over-lifted minimum, lost waiting-period days) maps onto these tests; no test introduces a requirement absent from the manual/instruction.
✅ pass - novel: This is a bespoke fictional 'tdbenefit' package and manual (edition TD-7) with idiosyncratic rules and scoping traps; it is not a standard textbook exercise or a problem with an available memorized solution.
✅ pass - agentic: Solving requires exploring multiple source files, cross-referencing a manual, iterating on a patch, and reasoning about generated edge-case jobs — this cannot be done via a single zero-shot generation.
✅ pass - reviewable: The manual is short and explicit, model.py's functions carry inline comments citing exact manual section numbers, and all expected outputs are derived programmatically (jobgen.py -> model.py -> seal.py) rather than hardcoded, letting a careful non-specialist reviewer trace correctness end-to-end.
✅ pass - instruction_concision: instruction.md is prose without headings, roleplay, or tool-listing, uses backticked absolute paths throughout (/app/docs/..., /app/src/tdbenefit, /app/tools/tdbenefit_run.py), and describes the goal/symptoms rather than a step-by-step fix procedure; it is dense but purposeful given the scope-ambiguity design, not filler or LLM boilerplate.
✅ pass - solution_quality: solve.sh applies a real diff (fix.patch) rather than echoing an answer, and the large diff content is kept in its own file (fix.patch) rather than inlined as a heredoc in solve.sh, consistent with guidance.
✅ pass - separate_verifier_configured: Verifier reads only /app (a declared artifact) and baked tests/ assets; tests/Dockerfile pre-installs pytest and pytest-json-ctrf at build time with no runtime installs in test.sh; spot-checked duplicated files (payroll.py, tdbenefit_run.py) between environment/app and tests/shipped/app are byte-identical.
✅ pass - environment_hygiene: environment/Dockerfile only COPYs app/ (tests/ and solution/ are excluded via .dockerignore and never referenced), installs only agent-facing tools (tmux, asciinema, patch, git, ca-certificates) with apt update/cleanup and no version pinning; tests/Dockerfile owns its own pytest/ctrf dependencies baked at build time.
✅ pass - structured_data_schema: environment/app/README.md normatively documents the exact job-file schema and the exact statement-output schema ('with exactly these keys, every value but claim an integer'), not merely illustrative examples.
✅ pass - typos: No typos found in filenames, code identifiers, paths, or prose across instruction.md, task.toml, source, tests, and solution files upon inspection.
✅ pass - difficulty_explanation_quality: The difficulty_explanation identifies the real occupation (claims adjuster/indemnity analyst), specifies the concrete reasoning failure modes (arrears crediting, scope judgment on corrections and low partial weeks), states the data is synthetic, and avoids citing model pass rates — it focuses on intrinsic task difficulty for both agents and humans.
✅ pass - solution_explanation_quality: The solution_explanation gives a per-file, per-rule table of exactly what changed and why, which I verified is congruous with fix.patch and model.py's actual logic.
✅ pass - verification_explanation_quality: The verification_explanation accurately describes the driver-swap/byte-check mechanism, the sealed/pinned expectations, the per-rule test structure, the differential tests for the two manual-silent cases, and the isolation/anti-read tests — all of which I confirmed are actually implemented in tests/test_outputs.py; comparisons are exact-value, not tolerance-based, so no calibration justification is needed.
✅ pass - category_and_tags: Category 'Operations' / subcategory 'Claims' fits a business-rules/insurance-claims adjudication task (analogous to the finance-with-Python example in the guidance), and tags (insurance-claims-benefit-adjudication, workers-compensation, temporary-disability, indemnity-benefits, average-weekly-wage) are specific and directly relevant, not generic.
✅ pass - no_extraneous_files: Every file inventoried (environment app package/docs/examples, solution scripts and patch, tests/expected jsonl+ROSTER, tests/shipped mirror, tests/Dockerfile/test.sh/test_outputs.py) is referenced by a Dockerfile, the tests, or the solution; no editor cruft, backups, or unused assets were found.
✅ pass - verifier_execution_isolation: Candidate (and shipped-copy) driver invocations run via setpriv with a dedicated low-privilege uid, cleared groups, no-new-privs, a restricted environment, their own session (killed via killpg afterward), and outputs captured via pipes/communicate with a timeout; /logs/verifier and /tests are sealed 700 root-owned before any candidate code executes, and root (test.sh) alone derives and writes the reward from pytest's exit code plus a byte-comparison.
✅ pass - ctrf_reporting: test.sh invokes `python3 -I -m pytest ... --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA`, writing the CTRF report directly to the collected location since pytest itself runs as root.
✅ pass - do_not_modify_enforced: The instruction's 'leave /app/tools/tdbenefit_run.py exactly as it is' constraint is enforced both functionally (the verifier always substitutes its own driver copy before running any job) and directly (test_submitted_driver_unchanged asserts the originally-delivered bytes equal the shipped driver's bytes, and that the on-disk file/parent dirs remain root-owned and non-writable), so a modified driver fails the run.
✅ pass - binary_reward: test.sh only ever writes literal `0` or `1` to /logs/verifier/reward.txt (initial 0, then 1 iff pytest rc==0 and the driver byte-compare succeeds, else 0); no fractional, weighted, or clamped score is ever written.

## Blocking Quality Gates
✅ PASS - verifiable
✅ PASS - solvable
✅ PASS - outcome_verified
✅ PASS - anti_cheat_robustness
✅ PASS - task_security
✅ PASS - functional_verification
✅ PASS - deterministic_reproducible
✅ PASS - test_instruction_alignment
✅ PASS - agentic
✅ PASS - separate_verifier_configured
✅ PASS - environment_hygiene
✅ PASS - structured_data_schema
✅ PASS - typos
✅ PASS - category_and_tags
✅ PASS - no_extraneous_files
✅ PASS - verifier_execution_isolation
✅ PASS - ctrf_reporting
✅ PASS - do_not_modify_enforced
✅ PASS - binary_reward
```

### Quality Check Logs

```
## Quality Check Results
✅ pass - verifiable: tests/test_outputs.py performs deterministic, programmatic, exact-value JSON comparisons (type-strict integer equality) against expectations sealed ahead of time by solution/seal.py+model.py. No LLM-as-judge is used. tests/Dockerfile bakes pytest/pytest-json-ctrf at build time; test.sh performs no runtime network installs.
✅ pass - solvable: solution/fix.patch (applied by solution/solve.sh via `patch -p1`) makes small, targeted changes to payroll.py, rates.py, partial.py and disability.py that I traced line-by-line and confirmed match solution/model.py's rule-by-rule logic (arrears crediting threshold 2,000, divide by 13, RATE_FRACTION=2/3, date-based row_in_force, aww<min early-return, inclusive period_days, WAITING_DAYS=3, half_up rounding of ttd, and the two documented scope decisions for corrections/low partial weeks). The changes are small and mechanically verifiable by an expert in a few hours.
✅ pass - difficult: The task requires precisely parsing a 6-section benefits manual, distinguishing which of several plausible-looking bugs the manual actually rules on versus which behaviors must be left exactly as today's (buggy) code computes them, and getting exact cent-level rounding, date arithmetic, and rate-table selection correct. The differential/scope tests (corrections, low_partial_weeks) specifically punish common over-fixes, making this a genuinely tricky requirements-precision task rather than a routine bugfix.
✅ pass - interesting: This mirrors real work of a workers' compensation claims adjuster/indemnity analyst validating benefit-statement software against a benefits manual; such reconciliation and business-rule-fidelity work is a real paid occupation (per the provided relevant_experience field).
✅ pass - outcome_verified: Instructions describe the end state (statements must follow the manual) and tests grade only the final JSON output of the documented driver command; the one process constraint (leave the driver file unchanged) is a mechanistic anti-cheat measure, not a dictated implementation approach.
✅ pass - anti_cheat_robustness: All ground truth (tests/expected, tests/shipped) lives only in the verifier image (tests/), excluded from the agent image via environment/.dockerignore and never COPYed by environment/Dockerfile. The verifier overwrites /app/tools/tdbenefit_run.py with its own copy before running, executes candidate code as an unprivileged uid via setpriv in isolated sessions, and a dedicated test proves the candidate user cannot read /tests, ROSTER, the shipped copy, or /logs/verifier.
✅ pass - task_security: No malicious code, exfiltration, obfuscation, or prompt injection found in any Dockerfile, script, or test file; all filesystem/permission operations (chown/chmod/setpriv) are directly in service of anti-cheat isolation, not host escape.
✅ pass - functional_verification: Tests execute the driver as a subprocess on real job files and compare structured JSON outputs; no keyword/string scanning of source code is used to grade correctness.
✅ pass - deterministic_reproducible: Base images are digest-pinned, pytest/ctrf plugin versions are pinned, no network is used at agent or verifier runtime, and all graded jobs/expectations are pre-generated and sealed with SHA-256+row-count pinning in ROSTER. Per-run random relabeling of claim names/order does not affect the pass/fail outcome of a correct or incorrect implementation.
✅ pass - essential_difficulty: Difficulty stems from correctly implementing arrears-based wage crediting, base-period math, date-sensitive rate-table lookup, and precise scope judgments about which unstated behaviors to preserve — genuine logical/domain reasoning, not output formatting (the output schema is unchanged from the shipped package and trivial to satisfy).
✅ pass - test_instruction_alignment: Each family test (weeks_pay, base_period, average_weekly_wage, rate_two_thirds, row_in_force, low_wage_rate, disability_days, waiting_period, retroactive_days, ttd_rounding, partial_benefit, etc.) traces directly to a manual rule the instruction tells the agent to follow, and the instruction's symptom list (AWW mismatches, short rates, stale maximum, over-lifted minimum, lost waiting-period days) maps onto these tests; no test introduces a requirement absent from the manual/instruction.
✅ pass - novel: This is a bespoke fictional 'tdbenefit' package and manual (edition TD-7) with idiosyncratic rules and scoping traps; it is not a standard textbook exercise or a problem with an available memorized solution.
✅ pass - agentic: Solving requires exploring multiple source files, cross-referencing a manual, iterating on a patch, and reasoning about generated edge-case jobs — this cannot be done via a single zero-shot generation.
✅ pass - reviewable: The manual is short and explicit, model.py's functions carry inline comments citing exact manual section numbers, and all expected outputs are derived programmatically (jobgen.py -> model.py -> seal.py) rather than hardcoded, letting a careful non-specialist reviewer trace correctness end-to-end.
✅ pass - instruction_concision: instruction.md is prose without headings, roleplay, or tool-listing, uses backticked absolute paths throughout (/app/docs/..., /app/src/tdbenefit, /app/tools/tdbenefit_run.py), and describes the goal/symptoms rather than a step-by-step fix procedure; it is dense but purposeful given the scope-ambiguity design, not filler or LLM boilerplate.
✅ pass - solution_quality: solve.sh applies a real diff (fix.patch) rather than echoing an answer, and the large diff content is kept in its own file (fix.patch) rather than inlined as a heredoc in solve.sh, consistent with guidance.
✅ pass - separate_verifier_configured: Verifier reads only /app (a declared artifact) and baked tests/ assets; tests/Dockerfile pre-installs pytest and pytest-json-ctrf at build time with no runtime installs in test.sh; spot-checked duplicated files (payroll.py, tdbenefit_run.py) between environment/app and tests/shipped/app are byte-identical.
✅ pass - environment_hygiene: environment/Dockerfile only COPYs app/ (tests/ and solution/ are excluded via .dockerignore and never referenced), installs only agent-facing tools (tmux, asciinema, patch, git, ca-certificates) with apt update/cleanup and no version pinning; tests/Dockerfile owns its own pytest/ctrf dependencies baked at build time.
✅ pass - structured_data_schema: environment/app/README.md normatively documents the exact job-file schema and the exact statement-output schema ('with exactly these keys, every value but claim an integer'), not merely illustrative examples.
✅ pass - typos: No typos found in filenames, code identifiers, paths, or prose across instruction.md, task.toml, source, tests, and solution files upon inspection.
✅ pass - difficulty_explanation_quality: The difficulty_explanation identifies the real occupation (claims adjuster/indemnity analyst), specifies the concrete reasoning failure modes (arrears crediting, scope judgment on corrections and low partial weeks), states the data is synthetic, and avoids citing model pass rates — it focuses on intrinsic task difficulty for both agents and humans.
✅ pass - solution_explanation_quality: The solution_explanation gives a per-file, per-rule table of exactly what changed and why, which I verified is congruous with fix.patch and model.py's actual logic.
✅ pass - verification_explanation_quality: The verification_explanation accurately describes the driver-swap/byte-check mechanism, the sealed/pinned expectations, the per-rule test structure, the differential tests for the two manual-silent cases, and the isolation/anti-read tests — all of which I confirmed are actually implemented in tests/test_outputs.py; comparisons are exact-value, not tolerance-based, so no calibration justification is needed.
✅ pass - category_and_tags: Category 'Operations' / subcategory 'Claims' fits a business-rules/insurance-claims adjudication task (analogous to the finance-with-Python example in the guidance), and tags (insurance-claims-benefit-adjudication, workers-compensation, temporary-disability, indemnity-benefits, average-weekly-wage) are specific and directly relevant, not generic.
✅ pass - no_extraneous_files: Every file inventoried (environment app package/docs/examples, solution scripts and patch, tests/expected jsonl+ROSTER, tests/shipped mirror, tests/Dockerfile/test.sh/test_outputs.py) is referenced by a Dockerfile, the tests, or the solution; no editor cruft, backups, or unused assets were found.
✅ pass - verifier_execution_isolation: Candidate (and shipped-copy) driver invocations run via setpriv with a dedicated low-privilege uid, cleared groups, no-new-privs, a restricted environment, their own session (killed via killpg afterward), and outputs captured via pipes/communicate with a timeout; /logs/verifier and /tests are sealed 700 root-owned before any candidate code executes, and root (test.sh) alone derives and writes the reward from pytest's exit code plus a byte-comparison.
✅ pass - ctrf_reporting: test.sh invokes `python3 -I -m pytest ... --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA`, writing the CTRF report directly to the collected location since pytest itself runs as root.
✅ pass - do_not_modify_enforced: The instruction's 'leave /app/tools/tdbenefit_run.py exactly as it is' constraint is enforced both functionally (the verifier always substitutes its own driver copy before running any job) and directly (test_submitted_driver_unchanged asserts the originally-delivered bytes equal the shipped driver's bytes, and that the on-disk file/parent dirs remain root-owned and non-writable), so a modified driver fails the run.
✅ pass - binary_reward: test.sh only ever writes literal `0` or `1` to /logs/verifier/reward.txt (initial 0, then 1 iff pytest rc==0 and the driver byte-compare succeeds, else 0); no fractional, weighted, or clamped score is ever written.

## Blocking Quality Gates
✅ PASS - verifiable
✅ PASS - solvable
✅ PASS - outcome_verified
✅ PASS - anti_cheat_robustness
✅ PASS - task_security
✅ PASS - functional_verification
✅ PASS - deterministic_reproducible
✅ PASS - test_instruction_alignment
✅ PASS - agentic
✅ PASS - separate_verifier_configured
✅ PASS - environment_hygiene
✅ PASS - structured_data_schema
✅ PASS - typos
✅ PASS - category_and_tags
✅ PASS - no_extraneous_files
✅ PASS - verifier_execution_isolation
✅ PASS - ctrf_reporting
✅ PASS - do_not_modify_enforced
✅ PASS - binary_reward
```

## 5b. Quality Panel Judge Feedback

### Quality Panel Judge Feedback

```
QUALITY PANEL: NEEDS REVISION -- 2 blocking issues to fix. Details for each are below.

Blocking (fix every one):
   1. [Sound Verifier] MAJOR: The verifier never grades a register spanning more than 52
      distinct Friday paydays, so an added fixed-size payday guard can reject a contract-valid
      job.
   2. [Sound Verifier] MINOR: All numeric test inputs are a fixed sealed corpus; the only
      runtime variation relabels claims, shuffles claims, and shuffles wage-line order, allowing
      a verifier-specific normalized lookup table instead of a manual implementation.

Checked and clean: Coherent Contract, Correct Reference Solution, Protected Ground Truth,
  Deterministic Execution.

------------------------------------------------------------------------------------------------
DETAILS
------------------------------------------------------------------------------------------------

1. [Sound Verifier] MAJOR -- missing behavioral coverage
   The verifier never grades a register spanning more than 52 distinct Friday paydays, so an
   added fixed-size payday guard can reject a contract-valid job.
   Why this fails:
     Reach: Use one claim injured Monday 2025-01-06, with 53 Friday wage lines of 2,000 cents
     each, dated weekly from 2024-01-05 through 2025-01-03, one valid disability day, no
     earnings, and a rate row effective 2016-01-01 with max 400,000 and min 1,000. The oldest
     line is within 400 days of injury; all lines meet section 1. Flip: A genuine implementation
     that stores or accepts at most 52 distinct paydays and raises an exception on the 53rd
     would fail this job. It would clear the shown comparisons: the 120-line limits fixture
     repeats a small set of Friday dates, while the other listed families do not supply 53
     distinct paydays. The verifier's large-job assertion checks claim and rate-row counts, not
     that payday span.
   Where to look: instruction.md:3-5, environment/app/docs/td-benefits-manual.md:28-35,
     tests/test_outputs.py:391-403, tests/expected/limits_claims.jsonl:2,
     tests/expected/ROSTER:1-24

2. [Sound Verifier] MINOR -- missing behavioral coverage
   All numeric test inputs are a fixed sealed corpus; the only runtime variation relabels
   claims, shuffles claims, and shuffles wage-line order, allowing a verifier-specific
   normalized lookup table instead of a manual implementation.
   Why this fails:
     Reach: check_family loads only rows from the pinned expected files and runs row['job'];
     generated-family variation calls relabel, which copies the job and changes only claim
     labels, claim order, and wage-line order. Flip: a submission can canonicalize each claim by
     sorting wage lines and ignoring the fresh claim label, recognize every fixture
     claim/rate-table signature, emit a hardcoded expected numeric statement with the incoming
     claim label, and preserve incoming claim order. It clears compare because compare only
     checks the resulting JSON values and types. Such a lookup requires knowledge of this
     verifier's hidden corpus, so it falls on the adversarial side of the reachability line and
     is Minor.
   Where to look: tests/test_outputs.py:238-240, tests/test_outputs.py:369-383,
     tests/test_outputs.py:440-447
```

## 5c. Oracle / NOP Validation

### Oracle / NOP Validation

```

```

### Difficulty Check Full Logs

```

```

## 6. Test Quality Report

### Test Quality Judge Report

```

```

## 7. TB 3.0 Rubric Feedback Checks

### TB 3.0 Rubric Feedback Checks

```

```

## 8. Agent Review Report

### Agent Review

```

```

## 9. CI & Static Checks

### CI Checks Summary

```

```

**Fast static checks:** status = `success`

- **AutoEval Execution Summary** — passed: `true` (codebuild)
  - AutoEval execution succeeded. Build status: SUCCEEDED. Build ID: CodeExecutionEnvironment:94d246aa-a583-4b35-a086-23df010b6d76.

## 10. Evaluation Rubrics

### test_rubrics

```
Agent credits a wage line of 2,000 cents or more, a week's pay, to the payroll week before its Friday payday's week, the week whose work it pays, instead of the week it was paid in, +2
Agent divides the base-period wages by thirteen for every worker, including one paid in only a few base weeks or in none, rather than by the number of weeks that received pay, +2
Agent sets the weekly rate at two thirds of the average weekly wage in place of the package's 60 per cent, rounded to the nearest cent, +2
Agent bounds the rate with the maximum and minimum of the rate-table row in force on the date of injury, not the newest row, including an injury on the very day a row takes effect and the last row of a 40-row table, and applies the row's figures as given, however low the maximum or high the minimum, +2
Agent pays a worker whose average weekly wage is below that minimum the wage itself as the weekly rate instead of lifting it to the minimum, +2
Agent counts both the first and the last day of every certified period as disability days, +2
Agent treats only the first three disability days as the waiting period and pays them back as retroactive days once the claim reaches fourteen disability days, +2
Agent rounds the total-disability amount, weekly rate times paid days over seven, to the nearest cent rather than truncating it, +2
Agent keeps a correction line below 2,000 cents counting toward the week that holds its payday while moving every week's pay back a week, so a correction paid in the week of injury stays out of the base period and one paid in the first base week stays in, +3
Agent keeps paying a partial-earnings week below 1,000 cents at the package's existing 60 per cent of its wage loss, rounded to the cent and capped at the weekly rate, while weeks of partial disability move to two thirds, +3
Agent leaves /app/tools/tdbenefit_run.py byte-for-byte as shipped, +1
Agent shifts every wage line a week earlier when fixing the payroll lag, corrections included, -3
Agent drops wage lines below a week's pay from the base-period wages instead of leaving them in their payday's week, -2
Agent changes the shared RATE_FRACTION to two thirds so that weeks under 1,000 cents are also paid two thirds of their loss, -3
Agent pays nothing for a partial week under 1,000 cents, treating it as no week of partial disability at all, -2
Agent floors a low week's 60 per cent share to the cent or lets it exceed the weekly rate, -1
Agent edits the benefits manual or hardcodes statement figures for particular claims instead of repairing the package, -5
```

## 10b. Automated Feedback

| Field | Value |
|---|---|
| Eval revision notes | `Agent Runner Summary: Evaluation FAILED. Pre-difficulty quality or quality panel gate failed; difficulty not run` |
| Eval revision requested at | `2026-09-27T15:52:32.992317Z` |
| Rebuttal notes | `` |

### Evaluation History (oldest first)

| # | Created | Outcome | Blocking stage | Stages |
|---|---|---|---|---|
| 1 | `2026-09-27T14:19:18.607543Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |
| 2 | `2026-09-27T15:35:51.906121Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |

## 11. Reviewer Decision

| Field | Value |
|---|---|
| Submission Review Decision | **—** |

### Revision Notes

_(none)_

---

_Generated by TB Task Revise Extractor from the Snorkel Experts task payload._
