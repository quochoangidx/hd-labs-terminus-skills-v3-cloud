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
| Expiry time | `2027-02-25T03:28:40.240907Z` |

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
| Uploaded at | `2026-09-28T02:20:25.053Z` |
| S3 URI | `s3://daas-blobs/prd/a34832f4-76f4-4d2a-aa62-c92deb15675d/ecd93580-63c0-498f-b3c6-07d6be4002d7/86dbf33c-b3c6-40b0-b98a-9b94c248f08f_submission_2026-09-28T02:20:23.492Z.zip` |
| S3 key | `prd/a34832f4-76f4-4d2a-aa62-c92deb15675d/ecd93580-63c0-498f-b3c6-07d6be4002d7/86dbf33c-b3c6-40b0-b98a-9b94c248f08f_submission_2026-09-28T02:20:23.492Z.zip` |

- **Difficulty-check artifact:** `s3://daas-blobs/codebuild_uploads/autoeval_artifacts/agent_runner/81402622-2ef9-419c-a165-da3672ba9d6e/difficulty_check/ad0b8d51b3c1/logs_artifact.zip`

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
   1. [Deterministic Execution] MAJOR: An OS-entropy seed generates substantive graded jobs at
      verifier runtime, so clean runs need not grade the same cases.
   2. [Deterministic Execution] MAJOR: The verifier derives DRAW_SEED from os.urandom and uses
      it to select four newly generated graded jobs at verifier runtime, so the central graded
      workload differs across clean runs.

Checked and clean: Coherent Contract, Correct Reference Solution, Protected Ground Truth, Sound
  Verifier.

------------------------------------------------------------------------------------------------
DETAILS
------------------------------------------------------------------------------------------------

1. [Deterministic Execution] MAJOR
   An OS-entropy seed generates substantive graded jobs at verifier runtime, so clean runs need
   not grade the same cases.
   Why this fails:
     Reach: DRAW_SEED initializes the RNG used for four `_draw_job` calls. Each call draws its
     rate-row count from 1 through 40, then draws claim inputs; the resulting job is passed to
     the candidate and its full output is compared with `manual_model.statements(job)`. Flip:
     consider a fixed submission that computes correct statements except when a job has 40 rate
     rows and 20–60 claims, for which it reports an incorrect rate. The sealed 40-row, 200-claim
     job does not trigger that exception. A reachable draw with no 40-row job clears this
     exception in all four runtime jobs; a draw whose first job has 40 rows triggers it and
     fails the exact comparison. These are static reachable draw outcomes, not observed runs.
     There is no fixed default seed or replay of these four jobs.
   Where to look: tests/test_outputs.py:490-503, tests/test_outputs.py:506-509,
     tests/test_outputs.py:540-548, tests/test_outputs.py:399-406

2. [Deterministic Execution] MAJOR -- uncontrolled randomness in grading
   The verifier derives DRAW_SEED from os.urandom and uses it to select four newly generated
   graded jobs at verifier runtime, so the central graded workload differs across clean runs.
   Why this fails:
     Reach: tests/test_outputs.py:490 creates a fresh entropy-derived DRAW_SEED; lines 542-545
     seed Random with it and generate four jobs. In _draw_job, lines 498-503 draw the number and
     effective dates of rate rows, including starts sampled from 0..3999. A sampled start of 1
     yields the valid rate-row date 2016-01-02. Flip: consider a fixed submission that exactly
     implements the reference except it emits an incorrect statement whenever any rate row has
     from="2016-01-02". It clears every sealed comparison and any random run whose four drawn
     jobs omit that date, but fails compare() on a run where a sampled rate start is 1, because
     line 548 compares its output to manual_model.statements(job). The random job is not merely
     renamed or permuted: it has newly selected rate figures, dates, claims, wages, periods, and
     earnings, and is a central model-compared workload.
   Where to look: tests/test_outputs.py:489-548, tests/test_outputs.py:493-537,
     tests/test_outputs.py:228-238
```

## 5. Quality Check Results

### Quality Check Summary

```
## Quality Check Results
✅ pass - verifiable: test.sh runs a pinned pytest (baked into tests/Dockerfile) against tests/test_outputs.py with no runtime installs, no LLM-as-judge, exact integer equality comparisons throughout (compare()), and a fixed 1500s internal time budget. All grading is programmatic subprocess execution and deterministic arithmetic comparison against a sealed/independent model.
✅ pass - solvable: solution/fix.patch (applied by solution/solve.sh) makes small, targeted, mechanically consistent edits to payroll.py, rates.py, partial.py and disability.py that match solution/model.py rule-for-rule and the manual; expert_time_estimate_hours=3 is plausible for an expert who has read the manual.
✅ pass - difficult: The task requires distinguishing seven distinct latent bugs, correctly scoping each fix to exactly what the manual settles (arrears crediting, base-period divisor, 2/3 vs 60%, row-in-force by date, minimum-lift rule, waiting days, rounding) while explicitly leaving two under-specified cases (small corrections, sub-$10 partial weeks) untouched — a genuine judgment-under-ambiguity problem beyond a typical bug-fix exercise.
✅ pass - interesting: Reproducing a workers'-compensation benefits calculator against a claims manual is a realistic task a claims-system engineer or indemnity analyst/software vendor would be paid to do; relevant_experience and difficulty_explanation ground this in a real occupation.
✅ pass - outcome_verified: Tests only check final JSON statement output for exact-match correctness; the only process constraint (leave the driver file unchanged) is a legitimate anti-cheat/scope constraint, not a dictate about implementation method.
✅ pass - anti_cheat_robustness: Ground truth, shipped baseline and generator live only in the separate verifier image; /app is re-sealed root-owned before grading; candidate code runs unprivileged with -I -S and a cleared env; claim numbers/order are shuffled and relabeled at run time, and fresh randomly-generated jobs graded against an independent model prevent any lookup-table shortcut, all explicitly exercised by test_candidate_cannot_read_verifier_state.
✅ pass - task_security: No exfiltration, obfuscation, or destructive operations found in either Dockerfile or any test/solution script; all file/network access is scoped to the task's own directories and matches its stated purpose.
✅ pass - functional_verification: Verification executes python3 /app/tools/tdbenefit_run.py as a real subprocess on real job files and diffs structured JSON output; no string/keyword scanning of source is used.
✅ pass - deterministic_reproducible: Dependencies are pinned (digest-pinned base image, pinned pytest/pytest-json-ctrf versions); no live services are used. Some sub-tests draw jobs from os.urandom seeds each run, but expected values are recomputed on the fly from an independent model rather than cached, so a correct solution always passes and the randomization does not introduce flakiness for the reference solution.
✅ pass - essential_difficulty: Difficulty comes from reasoning about scope of each manual rule and exact-integer arithmetic derivation, not from cosmetic formatting; the output schema itself is simple (ten integer fields) so most failure modes trace back to genuine misapplication of a rule.
✅ pass - test_instruction_alignment: The instruction directs the agent to the manual as sole authority and to the README for statement schema; every family of tests traces to a manual clause (2.1-6.1) referenced in the instruction's description of the domain, and the instruction's explicit 'leave the driver unchanged' requirement is directly tested.
✅ pass - novel: This is a bespoke, invented workers'-comp benefits codebase and manual with many interacting, non-obvious rules; it is not a known textbook exercise and could not be solved from memorized examples.
✅ pass - agentic: Solving requires reading a multi-section manual, cross-referencing it against several interdependent source files, running the driver, and iterating — well beyond a single zero-shot generation.
✅ pass - reviewable: The manual (td-benefits-manual.md) is self-contained and included in the task; solution/model.py is a from-scratch derivation from that manual (not hardcoded values), and solution/fix.patch plus solve.sh's rule table let a careful reviewer trace every change back to a manual clause.
✅ pass - instruction_concision: instruction.md is a short, plain narrative (two paragraphs), uses absolute paths (/app/docs/..., /app/src/tdbenefit, /app/tools/...), has no headings/roleplay/fluff, and does not hint at which lines of code are wrong or how to fix them.
✅ pass - solution_quality: The fix is delivered as a real patch file applied via `patch`, derived from and consistent with an independently-written reference model (solution/model.py); it is not an echoed final answer, and the patch is kept in its own file rather than inlined as a large heredoc in solve.sh.
✅ pass - separate_verifier_configured: artifacts=["/app/"] captures everything the verifier subprocess-execs; tests/Dockerfile pre-installs pytest and pytest-json-ctrf (no runtime installs in test.sh); the shipped baseline copies under tests/shipped are byte-identical to environment/app, and no agent dependency manifest is needed here.
✅ pass - environment_hygiene: environment/Dockerfile only copies app/ and installs generic agent tooling (tmux, asciinema, patch, git) with proper apt-get update/cleanup and unpinned apt packages; tests/ and solution/ are not copied into the agent image; tests/Dockerfile owns all test-only deps (pytest, pytest-json-ctrf).
✅ pass - structured_data_schema: README.md gives an explicit, normative schema for both the job input and the statements output (exact keys, types, ordering), referenced by instruction.md.
✅ pass - typos: Targeted search for common typo patterns and misspellings of key identifiers (tdbenefit, filenames, function names) found nothing; code, manual and metadata are internally consistent.
✅ pass - difficulty_explanation_quality: difficulty_explanation identifies the real occupation (claims adjuster/indemnity analyst), enumerates the specific latent errors and the scope-judgment challenge (the 'harder half'), states the data is synthetic, and avoids citing any benchmark/pass-rate figures.
✅ pass - solution_explanation_quality: solution_explanation summarizes exactly which files and constants change and why, matching solution/fix.patch and solution/model.py; it is congruent with the actual solution files reviewed.
✅ pass - verification_explanation_quality: verification_explanation is dense but concretely describes sealing, byte-checking the driver, per-rule named tests, the differential tests for the two under-specified cases, and run-time random generation graded against an independent model; all checks described are found in test_outputs.py, and no un-justified tolerance/threshold is used since all comparisons are exact integer equality.
✅ pass - category_and_tags: category=Operations / subcategory=Claims fits an insurance-claims benefits-calculation task better than Software/ML/etc.; tags (workers-compensation, temporary-disability, indemnity-benefits, average-weekly-wage) are specific and domain-relevant, not generic.
✅ pass - no_extraneous_files: Every file inventoried (environment/app sources+docs+example, solution/{solve.sh,fix.patch,model.py,jobgen.py,seal.py}, tests/{Dockerfile,test.sh,test_outputs.py,manual_model.py,shipped/*,expected/*}) is referenced by a Dockerfile, the instruction, solve.sh, or the test harness; nothing appears to be leftover cruft.
✅ pass - verifier_execution_isolation: Candidate code is never imported into the root pytest process; it is exec'd via setpriv --reuid to an unprivileged uid (65534) in its own session with -I -S and a cleared environment, output captured via pipes with communicate()+timeout and killpg cleanup, and /logs/verifier is chmod 700 before pytest starts, with the root test.sh deriving reward.txt from pytest's exit code plus a byte-comparison, never letting the executed candidate code touch the reward channel.
✅ pass - ctrf_reporting: test.sh invokes pytest with --ctrf /logs/verifier/ctrf.json, matching the required per-test CTRF reporting pattern.
✅ pass - do_not_modify_enforced: The instruction's 'leave /app/tools/tdbenefit_run.py exactly as it is' is directly enforced by test_submitted_driver_unchanged, which compares the driver's bytes captured before any candidate code ran against the verifier's pristine shipped copy — a violating agent fails this assertion regardless of any other correctness.
✅ pass - binary_reward: test.sh always writes exactly '0' or '1' to /logs/verifier/reward.txt (default 0, then set to 1 only if pytest rc==0 and the driver cmp succeeds); no fractional or weighted scoring path exists.

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
✅ pass - verifiable: test.sh runs a pinned pytest (baked into tests/Dockerfile) against tests/test_outputs.py with no runtime installs, no LLM-as-judge, exact integer equality comparisons throughout (compare()), and a fixed 1500s internal time budget. All grading is programmatic subprocess execution and deterministic arithmetic comparison against a sealed/independent model.
✅ pass - solvable: solution/fix.patch (applied by solution/solve.sh) makes small, targeted, mechanically consistent edits to payroll.py, rates.py, partial.py and disability.py that match solution/model.py rule-for-rule and the manual; expert_time_estimate_hours=3 is plausible for an expert who has read the manual.
✅ pass - difficult: The task requires distinguishing seven distinct latent bugs, correctly scoping each fix to exactly what the manual settles (arrears crediting, base-period divisor, 2/3 vs 60%, row-in-force by date, minimum-lift rule, waiting days, rounding) while explicitly leaving two under-specified cases (small corrections, sub-$10 partial weeks) untouched — a genuine judgment-under-ambiguity problem beyond a typical bug-fix exercise.
✅ pass - interesting: Reproducing a workers'-compensation benefits calculator against a claims manual is a realistic task a claims-system engineer or indemnity analyst/software vendor would be paid to do; relevant_experience and difficulty_explanation ground this in a real occupation.
✅ pass - outcome_verified: Tests only check final JSON statement output for exact-match correctness; the only process constraint (leave the driver file unchanged) is a legitimate anti-cheat/scope constraint, not a dictate about implementation method.
✅ pass - anti_cheat_robustness: Ground truth, shipped baseline and generator live only in the separate verifier image; /app is re-sealed root-owned before grading; candidate code runs unprivileged with -I -S and a cleared env; claim numbers/order are shuffled and relabeled at run time, and fresh randomly-generated jobs graded against an independent model prevent any lookup-table shortcut, all explicitly exercised by test_candidate_cannot_read_verifier_state.
✅ pass - task_security: No exfiltration, obfuscation, or destructive operations found in either Dockerfile or any test/solution script; all file/network access is scoped to the task's own directories and matches its stated purpose.
✅ pass - functional_verification: Verification executes python3 /app/tools/tdbenefit_run.py as a real subprocess on real job files and diffs structured JSON output; no string/keyword scanning of source is used.
✅ pass - deterministic_reproducible: Dependencies are pinned (digest-pinned base image, pinned pytest/pytest-json-ctrf versions); no live services are used. Some sub-tests draw jobs from os.urandom seeds each run, but expected values are recomputed on the fly from an independent model rather than cached, so a correct solution always passes and the randomization does not introduce flakiness for the reference solution.
✅ pass - essential_difficulty: Difficulty comes from reasoning about scope of each manual rule and exact-integer arithmetic derivation, not from cosmetic formatting; the output schema itself is simple (ten integer fields) so most failure modes trace back to genuine misapplication of a rule.
✅ pass - test_instruction_alignment: The instruction directs the agent to the manual as sole authority and to the README for statement schema; every family of tests traces to a manual clause (2.1-6.1) referenced in the instruction's description of the domain, and the instruction's explicit 'leave the driver unchanged' requirement is directly tested.
✅ pass - novel: This is a bespoke, invented workers'-comp benefits codebase and manual with many interacting, non-obvious rules; it is not a known textbook exercise and could not be solved from memorized examples.
✅ pass - agentic: Solving requires reading a multi-section manual, cross-referencing it against several interdependent source files, running the driver, and iterating — well beyond a single zero-shot generation.
✅ pass - reviewable: The manual (td-benefits-manual.md) is self-contained and included in the task; solution/model.py is a from-scratch derivation from that manual (not hardcoded values), and solution/fix.patch plus solve.sh's rule table let a careful reviewer trace every change back to a manual clause.
✅ pass - instruction_concision: instruction.md is a short, plain narrative (two paragraphs), uses absolute paths (/app/docs/..., /app/src/tdbenefit, /app/tools/...), has no headings/roleplay/fluff, and does not hint at which lines of code are wrong or how to fix them.
✅ pass - solution_quality: The fix is delivered as a real patch file applied via `patch`, derived from and consistent with an independently-written reference model (solution/model.py); it is not an echoed final answer, and the patch is kept in its own file rather than inlined as a large heredoc in solve.sh.
✅ pass - separate_verifier_configured: artifacts=["/app/"] captures everything the verifier subprocess-execs; tests/Dockerfile pre-installs pytest and pytest-json-ctrf (no runtime installs in test.sh); the shipped baseline copies under tests/shipped are byte-identical to environment/app, and no agent dependency manifest is needed here.
✅ pass - environment_hygiene: environment/Dockerfile only copies app/ and installs generic agent tooling (tmux, asciinema, patch, git) with proper apt-get update/cleanup and unpinned apt packages; tests/ and solution/ are not copied into the agent image; tests/Dockerfile owns all test-only deps (pytest, pytest-json-ctrf).
✅ pass - structured_data_schema: README.md gives an explicit, normative schema for both the job input and the statements output (exact keys, types, ordering), referenced by instruction.md.
✅ pass - typos: Targeted search for common typo patterns and misspellings of key identifiers (tdbenefit, filenames, function names) found nothing; code, manual and metadata are internally consistent.
✅ pass - difficulty_explanation_quality: difficulty_explanation identifies the real occupation (claims adjuster/indemnity analyst), enumerates the specific latent errors and the scope-judgment challenge (the 'harder half'), states the data is synthetic, and avoids citing any benchmark/pass-rate figures.
✅ pass - solution_explanation_quality: solution_explanation summarizes exactly which files and constants change and why, matching solution/fix.patch and solution/model.py; it is congruent with the actual solution files reviewed.
✅ pass - verification_explanation_quality: verification_explanation is dense but concretely describes sealing, byte-checking the driver, per-rule named tests, the differential tests for the two under-specified cases, and run-time random generation graded against an independent model; all checks described are found in test_outputs.py, and no un-justified tolerance/threshold is used since all comparisons are exact integer equality.
✅ pass - category_and_tags: category=Operations / subcategory=Claims fits an insurance-claims benefits-calculation task better than Software/ML/etc.; tags (workers-compensation, temporary-disability, indemnity-benefits, average-weekly-wage) are specific and domain-relevant, not generic.
✅ pass - no_extraneous_files: Every file inventoried (environment/app sources+docs+example, solution/{solve.sh,fix.patch,model.py,jobgen.py,seal.py}, tests/{Dockerfile,test.sh,test_outputs.py,manual_model.py,shipped/*,expected/*}) is referenced by a Dockerfile, the instruction, solve.sh, or the test harness; nothing appears to be leftover cruft.
✅ pass - verifier_execution_isolation: Candidate code is never imported into the root pytest process; it is exec'd via setpriv --reuid to an unprivileged uid (65534) in its own session with -I -S and a cleared environment, output captured via pipes with communicate()+timeout and killpg cleanup, and /logs/verifier is chmod 700 before pytest starts, with the root test.sh deriving reward.txt from pytest's exit code plus a byte-comparison, never letting the executed candidate code touch the reward channel.
✅ pass - ctrf_reporting: test.sh invokes pytest with --ctrf /logs/verifier/ctrf.json, matching the required per-test CTRF reporting pattern.
✅ pass - do_not_modify_enforced: The instruction's 'leave /app/tools/tdbenefit_run.py exactly as it is' is directly enforced by test_submitted_driver_unchanged, which compares the driver's bytes captured before any candidate code ran against the verifier's pristine shipped copy — a violating agent fails this assertion regardless of any other correctness.
✅ pass - binary_reward: test.sh always writes exactly '0' or '1' to /logs/verifier/reward.txt (default 0, then set to 1 only if pytest rc==0 and the driver cmp succeeds); no fractional or weighted scoring path exists.

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
   1. [Deterministic Execution] MAJOR: An OS-entropy seed generates substantive graded jobs at
      verifier runtime, so clean runs need not grade the same cases.
   2. [Deterministic Execution] MAJOR: The verifier derives DRAW_SEED from os.urandom and uses
      it to select four newly generated graded jobs at verifier runtime, so the central graded
      workload differs across clean runs.

Checked and clean: Coherent Contract, Correct Reference Solution, Protected Ground Truth, Sound
  Verifier.

------------------------------------------------------------------------------------------------
DETAILS
------------------------------------------------------------------------------------------------

1. [Deterministic Execution] MAJOR
   An OS-entropy seed generates substantive graded jobs at verifier runtime, so clean runs need
   not grade the same cases.
   Why this fails:
     Reach: DRAW_SEED initializes the RNG used for four `_draw_job` calls. Each call draws its
     rate-row count from 1 through 40, then draws claim inputs; the resulting job is passed to
     the candidate and its full output is compared with `manual_model.statements(job)`. Flip:
     consider a fixed submission that computes correct statements except when a job has 40 rate
     rows and 20–60 claims, for which it reports an incorrect rate. The sealed 40-row, 200-claim
     job does not trigger that exception. A reachable draw with no 40-row job clears this
     exception in all four runtime jobs; a draw whose first job has 40 rows triggers it and
     fails the exact comparison. These are static reachable draw outcomes, not observed runs.
     There is no fixed default seed or replay of these four jobs.
   Where to look: tests/test_outputs.py:490-503, tests/test_outputs.py:506-509,
     tests/test_outputs.py:540-548, tests/test_outputs.py:399-406

2. [Deterministic Execution] MAJOR -- uncontrolled randomness in grading
   The verifier derives DRAW_SEED from os.urandom and uses it to select four newly generated
   graded jobs at verifier runtime, so the central graded workload differs across clean runs.
   Why this fails:
     Reach: tests/test_outputs.py:490 creates a fresh entropy-derived DRAW_SEED; lines 542-545
     seed Random with it and generate four jobs. In _draw_job, lines 498-503 draw the number and
     effective dates of rate rows, including starts sampled from 0..3999. A sampled start of 1
     yields the valid rate-row date 2016-01-02. Flip: consider a fixed submission that exactly
     implements the reference except it emits an incorrect statement whenever any rate row has
     from="2016-01-02". It clears every sealed comparison and any random run whose four drawn
     jobs omit that date, but fails compare() on a run where a sampled rate start is 1, because
     line 548 compares its output to manual_model.statements(job). The random job is not merely
     renamed or permuted: it has newly selected rate figures, dates, claims, wages, periods, and
     earnings, and is a central model-compared workload.
   Where to look: tests/test_outputs.py:489-548, tests/test_outputs.py:493-537,
     tests/test_outputs.py:228-238
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
  - AutoEval execution succeeded. Build status: SUCCEEDED. Build ID: CodeExecutionEnvironment:c53f9175-4d1c-47d6-87c9-d0b73f1cf7d4.

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
| Eval revision requested at | `2026-09-28T03:28:40.240907Z` |
| Rebuttal notes | `` |

### Evaluation History (oldest first)

| # | Created | Outcome | Blocking stage | Stages |
|---|---|---|---|---|
| 1 | `2026-09-27T14:19:18.607543Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |
| 2 | `2026-09-27T15:35:51.906121Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |
| 3 | `2026-09-28T02:23:40.690532Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |

## 11. Reviewer Decision

| Field | Value |
|---|---|
| Submission Review Decision | **—** |

### Revision Notes

_(none)_

---

_Generated by TB Task Revise Extractor from the Snorkel Experts task payload._
