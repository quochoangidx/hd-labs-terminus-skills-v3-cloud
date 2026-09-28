# Terminal Bench 2.0 — Task Revise Report

> Comprehensive task information extracted from the Snorkel Experts task payload.
> This is the same data that populates the task's right-hand **Revise panel** (Difficulty Explanation, Solution Explanation, checks, rubrics, agent runs, etc.).

## 1. Task Identity & Metadata

| Field | Value |
|---|---|
| Project | `Terminus-3-Prod` |
| Project ID | `a34832f4-76f4-4d2a-aa62-c92deb15675d` |
| Assignment ID | `ffd1fe4e-1dea-4e6f-bc90-a6e99f468d9a` |
| Task ID | `f0baf65d-5ff7-4d84-974b-8d77ddefa71c` |
| Submission ID | `f0baf65d-5ff7-4d84-974b-8d77ddefa71c` |
| Task category (stage) | `SUBMISSION` |
| Submission task type | `submission-8d482d68-4d7e-449f-9388-b3cb0cefb643` |
| Review task type | `submission-8d482d68-4d7e-449f-9388-b3cb0cefb643` |
| Form schema revision | `9110301d-4bfc-42cc-8185-74945ca1a856` |
| Skippable | `false` |
| Further revisions allowed | `true` |
| Expiry time | `2027-02-25T03:04:22.129745Z` |

### Task Classification (submission_document)

| Field | Value |
|---|---|
| Difficulty | **** |
| Solvable | `` |
| Task category | `Operations` |
| Task subcategories | `["Finance"]` |
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
| Filename | `tbrain-car-rental-agreement-billing.zip` |
| Uploaded at | `2026-09-28T02:21:26.071Z` |
| S3 URI | `s3://daas-blobs/prd/a34832f4-76f4-4d2a-aa62-c92deb15675d/ffd1fe4e-1dea-4e6f-bc90-a6e99f468d9a/86dbf33c-b3c6-40b0-b98a-9b94c248f08f_submission_2026-09-28T02:21:24.666Z.zip` |
| S3 key | `prd/a34832f4-76f4-4d2a-aa62-c92deb15675d/ffd1fe4e-1dea-4e6f-bc90-a6e99f468d9a/86dbf33c-b3c6-40b0-b98a-9b94c248f08f_submission_2026-09-28T02:21:24.666Z.zip` |

- **Difficulty-check artifact:** `s3://daas-blobs/codebuild_uploads/autoeval_artifacts/agent_runner/7db8c7a5-3d58-4567-a8da-124836258d26/difficulty_check/1006d19fc283/logs_artifact.zip`

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

QUALITY PANEL: NEEDS REVISION -- 3 blocking issues to fix. Details for each are below.

Blocking (fix every one):
   1. [Coherent Contract] MAJOR: The bill schema declares all listed fields, including id, to be
      integers, while the disclosed identifier schema and shipped implementation use strings and
      the verifier requires string identifiers.
   2. [Sound Verifier] MAJOR: No graded sub-day rental returns short of fuel, allowing an
      implementation to apply the refuelling fee only to day rentals.
   3. [Sound Verifier] MAJOR: All tested rentals shorter than an hour remain within the mileage
      allowance, so an unconditional zero-mileage-charge shortcut for that duration passes.

Checked and clean: Correct Reference Solution, Protected Ground Truth, Deterministic Execution.

------------------------------------------------------------------------------------------------
DETAILS
------------------------------------------------------------------------------------------------

1. [Coherent Contract] MAJOR -- contradictory authorities
   The bill schema declares all listed fields, including id, to be integers, while the disclosed
   identifier schema and shipped implementation use strings and the verifier requires string
   identifiers.
   Why this fails:
     Reach: tests/expected/07-order_and_totals.jsonl contains the valid agreement id "0", and
     test_bill_order_and_file_totals grades that family. README lines 29–32 list id alongside
     days, miles, and charges and then say 'all integers'. Yet README line 19 defines agreement
     ids as strings, and the candidate-visible run.py line 17 copies agreement["id"] unchanged.
     The conflict is also evident for the reviewer's "G1" example, which has no specified
     integer representation. Flip: for the numeric-looking id "0", following the literal
     integer-output requirement produces id 0; preserving the identifier as the shipped
     implementation does produces id "0". compare() lines 224–227 compares the id, and _same()
     line 214 rejects 0 against the expected "0" because both type and value must match.
     Producing the accepted string instead violates the unqualified 'all integers' output
     declaration. I checked instruction.md, task.toml, README, RC-3, the example, and every
     shipped package/driver file: the starter discloses the intended string behavior, but no
     text explicitly exempts id from the contradictory output-type declaration; instruction.md
     line 5 repeats an overbroad JSON-integer requirement.
   Where to look: environment/app/README.md:17-22, environment/app/README.md:28-32,
     instruction.md:5, environment/app/src/rentcharge/run.py:16-22,
     tests/expected/07-order_and_totals.jsonl:1, tests/test_outputs.py:213-227 (+1 more)

2. [Sound Verifier] MAJOR -- Missing combined-condition coverage
   No graded sub-day rental returns short of fuel, allowing an implementation to apply the
   refuelling fee only to day rentals.
   Why this fails:
     Reach: use one agreement with id A, out 2028-04-04T14:00, in 2028-04-04T14:01, odometer_out
     10000, odometer_in 10005, fuel_out 8, fuel_in 7, day_rate 5000, mile_rate 30, fuel_rate
     600, and branch X. This is within rule 1.3. Correct figures are days 1, miles 5,
     time_charge 5000, mileage_charge 0, fuel_charge 2100, tax 413, total/revenue 7513. Flip: an
     otherwise correct repair that preserves the old fuel difference calculation but adds 1500
     only when fuel_out > fuel_in AND duration >= 1440 instead produces fuel_charge 600 and
     total/revenue 6013. Such an incorrect scoping of the fee to the manual's day-rental branch
     is a plausible repair mistake. It passes every shown graded input: the only families
     permitted to contain sub-day rentals are short_days, short_allowance, and traps_combined;
     their complete fixtures contain only equal or fuller returns. For those, the fee is
     correctly absent under both implementations. All actual shortages in the remaining fixtures
     last at least a day, so the defective extra duration condition is true and all compared
     fields match. Relabelling operates only on generated day rentals and preserves durations
     and fuel levels. Leaving all non-package files untouched also passes the integrity
     assertions.
   Where to look: environment/app/docs/rental-charges-manual.md:48-60, tests/test_outputs.py:55,
     tests/test_outputs.py:189-209, tests/expected/08-short_days.jsonl:1,
     tests/expected/09-short_allowance.jsonl:1, tests/expected/11-traps_combined.jsonl:1

3. [Sound Verifier] MAJOR -- Missing combined-condition coverage
   All tested rentals shorter than an hour remain within the mileage allowance, so an
   unconditional zero-mileage-charge shortcut for that duration passes.
   Why this fails:
     Reach: take a single agreement with id A, branch X, out 2028-04-04T14:00, in
     2028-04-04T14:59, odometer_out 10000, odometer_in 10151, fuel_out and fuel_in 8, day_rate
     5000, mile_rate 30, and fuel_rate 600. Rule 1.3 imposes no speed restriction, so this
     59-minute, 151-mile rental is legal. The preserved days calculation gives 1; the allowance
     is 150, mileage_charge is 30, taxable charges are 5030, tax is 415, and total/revenue is
     5445. Flip: an otherwise correct implementation with `if length(agreement) < 60: return 0`
     in mileage_charge instead produces mileage_charge 0, tax 413, and total/revenue 5413. This
     is a plausible but unauthorized short-trip shortcut. It passes every shown test: the
     sub-hour S1, S2, and S3 cases drive 5, 12, and 40 miles, and C1 drives 130, all correctly
     owing zero mileage charge anyway. The excess-mileage sub-day cases L3 and L4 last 90 and
     1439 minutes, so they do not exercise the shortcut. Every other graded rental lasts at
     least an hour. Consequently the added guard changes no graded bill field or aggregate,
     while the distinguishing legal input would fail the exact comparison.
   Where to look: instruction.md:3, environment/app/docs/rental-charges-manual.md:25-31,
     environment/app/docs/rental-charges-manual.md:55-57, tests/expected/08-short_days.jsonl:1,
     tests/expected/09-short_allowance.jsonl:1, tests/expected/11-traps_combined.jsonl:1 (+1
     more)
```

## 5. Quality Check Results

### Quality Check Summary

```
## Quality Check Results
✅ pass - verifiable: tests/test_outputs.py runs the actual driver via subprocess against sealed inputs and compares to pre-sealed expected JSON (SHA-256 pinned in tests/expected/ROSTER). No LLM-as-judge, no runtime network installs in test.sh (pytest/ctrf are baked into tests/Dockerfile). Randomness (RELABEL_SEED from os.urandom) is used only to vary branch labels/ids/time-shift of already-correct fixtures, with expected outputs recomputed by the same deterministic relabel transform, so results are reproducible and self-consistent across reruns.
✅ pass - solvable: solution/fix.patch is a small, self-contained diff (5 files) applied by solution/solve.sh via `patch -p1`, matching exactly the manual's rules (grace days, 150-mile allowance, odometer turnover, refuelling fee, tax base/rounding) while leaving undefined behavior (sub-day rentals, over-full returns) untouched. This is clearly implementable by an expert in well under a few hours.
✅ pass - difficult: The task requires simultaneously fixing five interacting numeric rules while precisely scoping changes to only what the manual governs and resisting several natural but wrong generalizations (applying the grace rule to sub-day rentals, flooring the fuel credit at zero). The verifier's own documentation of 22 near-miss one-edit mutants that must each fail shows the intended difficulty is real and calibrated, not merely tedious.
✅ pass - interesting: Reconciling a legacy billing package against an authoritative rate-card/manual, without over- or under-fixing behavior, is a realistic software-maintenance scenario for a car-rental billing team; someone could genuinely be paid to do this.
✅ pass - outcome_verified: Tests only check the JSON bill-run output of the documented command against expected values; instruction never mandates specific tools, editors, or implementation steps, only the end-state behavior.
✅ pass - anti_cheat_robustness: Ground truth (tests/expected/*, solution/model.py, solution/jobgen.py) lives only in the verifier image, never shipped to the agent image. The verifier runs candidate code unprivileged (setpriv), seals /app root-owned before grading, keeps a separate shipped copy under a different uid, and explicitly tests that the candidate's uid cannot read /tests, ROSTER, the shipped copy, or /logs/verifier.
✅ pass - task_security: No exfiltration, obfuscation, destructive commands, or prompt injection found; grep for curl/wget/eval/base64/network calls across the whole task tree returned nothing. Privilege-dropping and chown/chmod operations are all legitimate anti-cheat isolation, scoped to /app, /tests, /logs/verifier.
✅ pass - functional_verification: Verification executes the real driver (`python3 /app/tools/rentcharge_run.py`) as a subprocess and compares its parsed JSON output field-by-field to computed expected bills; no source-code string/keyword matching is used.
✅ pass - deterministic_reproducible: Both Dockerfiles pin the exact same base image by digest; pip deps in tests/Dockerfile are version-pinned; no live services are used. Random elements only vary labels/timing of already-verified fixtures and the expected values are recomputed by the same transform, so pass/fail is not sensitive to the random draw.
✅ pass - essential_difficulty: Difficulty stems from correctly reasoning about which of five interacting billing rules apply and where the specification is silent, not from output formatting; the compared JSON schema is a small, fixed set of integer fields already documented in the README.
✅ pass - test_instruction_alignment: Every graded family (grace, allowance, turnover, refuelling, tax_base, tax_rounding, order_and_totals, short_days/allowance, fuel_not_short, traps_combined, limits, generated) traces directly to a rule or scope statement in instruction.md/the manual; the driver-preservation and README/manual/example-integrity checks track the instruction's explicit 'leave the driver as is' and 'only change what the manual governs' constraints.
✅ pass - novel: This is a bespoke synthetic billing domain (Pellham Car & Van Hire, manual RC-3) with custom rule numbering and deliberately crafted traps; it is not a reproducible textbook exercise available in training data.
✅ pass - agentic: Solving requires exploring and editing multiple interacting source files under /app/src/rentcharge, cross-referencing a separate manual document, and reasoning about the driver and README — genuine multi-file, multi-step terminal work rather than a single zero-shot generation.
✅ pass - reviewable: Expected outputs are derived by solution/model.py (an independent implementation of the manual) run through solution/seal.py, not hand-typed; a non-specialist reviewer can read the short manual and model.py side by side and verify correctness, or recompute the shipped-file SHA-256 checks directly.
✅ pass - instruction_concision: Uses backticked absolute paths throughout, no headings/roleplay/tool-listing, and describes the desired end state and scope constraints rather than implementation steps. It restates rule 1.3's numeric limits (already in the manual) for clarity, which is slightly redundant but not a solution hint.
✅ pass - solution_quality: solution/fix.patch is a genuine unified diff altering the actual logic (day-charging formula, allowance constant, odometer turnover math, fuel fee/base, tax rounding), not a hardcoded answer; files are reasonably small and not bloated heredocs in solve.sh.
✅ pass - separate_verifier_configured: tests/Dockerfile bakes pytest/pytest-json-ctrf and pre-creates /app and /logs/verifier; all verifier inputs (agreement files, driver, expected fixtures) come from the artifacts=['/app/'] declaration or tests/ itself. tests/shipped/app files are byte-identical to environment/app (verified for driver, mileage.py, fuel.py, time_charge.py), and the base-image digest matches between environment/Dockerfile and tests/Dockerfile.
✅ pass - environment_hygiene: environment/Dockerfile only COPYs app/ and installs task-relevant packages (tmux, asciinema, patch, git); no tests/solution content or test-only deps (pytest, ctrf) leak into the agent image. tests/Dockerfile owns pytest/ctrf and its own mkdir/chmod setup; apt is properly updated/cleaned in the agent Dockerfile.
✅ pass - structured_data_schema: environment/app/README.md normatively documents the exact agreement-file and bill-run JSON schemas (field names and types), which the instruction explicitly references as authoritative alongside the manual.
✅ pass - typos: No typos found in filenames, paths, commands, or variable names. Minor inline comment mislabeling exists (jobgen.py/model.py tag turnover as rule '2.5' and refuelling as '2.6' instead of the manual's 2.4/2.5), but this is a comment cross-reference slip, not a filename/path/command/variable-name typo, and test names and the manual itself use the correct numbers.
✅ pass - difficulty_explanation_quality: difficulty_explanation clearly identifies the specific bugs, the two undefined-behavior traps, why a naive/well-intentioned fix would fail, states the data is synthetic and hand-built at the limits, and names the real-world persona (a rental-billing analyst) who would do this work.
✅ pass - solution_explanation_quality: solution_explanation concisely summarizes each rule change and matches fix.patch exactly (day formula, 150-mile allowance, turnover addition, refuelling fee, tax base/rounding), and correctly notes the driver is untouched.
✅ pass - verification_explanation_quality: verification_explanation is dense and concrete: it describes the sealing/isolation mechanism, the sealed-fixture SHA-256 pinning, the specific edge-case inputs used per family, the mutant/alternative-solution validation, and the anti-cheat unreadability test — all consistent with the actual test_outputs.py content. No unjustified numeric tolerances are used (all comparisons are exact integers).
✅ pass - category_and_tags: category='Operations'/subcategory='Finance' fits a billing-rule-compliance task (the Python tooling is incidental to the finance/business-rules domain), and tags (car-rental, billing, rental-agreements, sales-tax, revenue-operations) are specific and descriptive rather than generic.
✅ pass - no_extraneous_files: Every file inventoried (instruction.md, task.toml, environment/*, solution/*, tests/*) is referenced by a Dockerfile, the instruction, solve.sh, or the test suite; no editor cruft, backups, or unused assets were found.
✅ pass - verifier_execution_isolation: Agent-produced code is only ever executed via setpriv as an unprivileged uid (65534) in its own session, never imported in-process by the root pytest process; /logs/verifier is chmod 700 before any candidate code runs, and reward is derived by root from pytest's exit code plus a byte-comparison. A theoretical pipe-hold-open-by-a-detached-daemon edge case (stdout/stderr as PIPE rather than temp files) could cause a hang, but that only risks a false failure/timeout, not a forged pass, since reward defaults to 0 until pytest explicitly succeeds.
✅ pass - ctrf_reporting: test.sh invokes `python3 -I -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA`, matching the standard per-test CTRF reporting pattern with pinned pytest/pytest-json-ctrf versions baked into tests/Dockerfile.
✅ pass - do_not_modify_enforced: The instruction's 'leave that driver exactly as it is... byte for byte' constraint is enforced both directly (test_submitted_driver_unchanged hashes the delivered bytes captured before the verifier's overwrite) and via isolation (the verifier immediately replaces the driver with its own shipped copy before any grading run, so a tampered driver can never influence functional results). The implicit 'only change the package' scope is enforced via SHA-256 checks on README/manual/example (test_only_the_package_changed).
✅ pass - binary_reward: tests/test.sh only ever writes exactly '0' or '1' to /logs/verifier/reward.txt: it defaults to 0, and sets 1 only when pytest's exit code is 0 and a `cmp -s` byte-comparison of the driver succeeds; no fractional or weighted scoring path exists.

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
✅ pass - verifiable: tests/test_outputs.py runs the actual driver via subprocess against sealed inputs and compares to pre-sealed expected JSON (SHA-256 pinned in tests/expected/ROSTER). No LLM-as-judge, no runtime network installs in test.sh (pytest/ctrf are baked into tests/Dockerfile). Randomness (RELABEL_SEED from os.urandom) is used only to vary branch labels/ids/time-shift of already-correct fixtures, with expected outputs recomputed by the same deterministic relabel transform, so results are reproducible and self-consistent across reruns.
✅ pass - solvable: solution/fix.patch is a small, self-contained diff (5 files) applied by solution/solve.sh via `patch -p1`, matching exactly the manual's rules (grace days, 150-mile allowance, odometer turnover, refuelling fee, tax base/rounding) while leaving undefined behavior (sub-day rentals, over-full returns) untouched. This is clearly implementable by an expert in well under a few hours.
✅ pass - difficult: The task requires simultaneously fixing five interacting numeric rules while precisely scoping changes to only what the manual governs and resisting several natural but wrong generalizations (applying the grace rule to sub-day rentals, flooring the fuel credit at zero). The verifier's own documentation of 22 near-miss one-edit mutants that must each fail shows the intended difficulty is real and calibrated, not merely tedious.
✅ pass - interesting: Reconciling a legacy billing package against an authoritative rate-card/manual, without over- or under-fixing behavior, is a realistic software-maintenance scenario for a car-rental billing team; someone could genuinely be paid to do this.
✅ pass - outcome_verified: Tests only check the JSON bill-run output of the documented command against expected values; instruction never mandates specific tools, editors, or implementation steps, only the end-state behavior.
✅ pass - anti_cheat_robustness: Ground truth (tests/expected/*, solution/model.py, solution/jobgen.py) lives only in the verifier image, never shipped to the agent image. The verifier runs candidate code unprivileged (setpriv), seals /app root-owned before grading, keeps a separate shipped copy under a different uid, and explicitly tests that the candidate's uid cannot read /tests, ROSTER, the shipped copy, or /logs/verifier.
✅ pass - task_security: No exfiltration, obfuscation, destructive commands, or prompt injection found; grep for curl/wget/eval/base64/network calls across the whole task tree returned nothing. Privilege-dropping and chown/chmod operations are all legitimate anti-cheat isolation, scoped to /app, /tests, /logs/verifier.
✅ pass - functional_verification: Verification executes the real driver (`python3 /app/tools/rentcharge_run.py`) as a subprocess and compares its parsed JSON output field-by-field to computed expected bills; no source-code string/keyword matching is used.
✅ pass - deterministic_reproducible: Both Dockerfiles pin the exact same base image by digest; pip deps in tests/Dockerfile are version-pinned; no live services are used. Random elements only vary labels/timing of already-verified fixtures and the expected values are recomputed by the same transform, so pass/fail is not sensitive to the random draw.
✅ pass - essential_difficulty: Difficulty stems from correctly reasoning about which of five interacting billing rules apply and where the specification is silent, not from output formatting; the compared JSON schema is a small, fixed set of integer fields already documented in the README.
✅ pass - test_instruction_alignment: Every graded family (grace, allowance, turnover, refuelling, tax_base, tax_rounding, order_and_totals, short_days/allowance, fuel_not_short, traps_combined, limits, generated) traces directly to a rule or scope statement in instruction.md/the manual; the driver-preservation and README/manual/example-integrity checks track the instruction's explicit 'leave the driver as is' and 'only change what the manual governs' constraints.
✅ pass - novel: This is a bespoke synthetic billing domain (Pellham Car & Van Hire, manual RC-3) with custom rule numbering and deliberately crafted traps; it is not a reproducible textbook exercise available in training data.
✅ pass - agentic: Solving requires exploring and editing multiple interacting source files under /app/src/rentcharge, cross-referencing a separate manual document, and reasoning about the driver and README — genuine multi-file, multi-step terminal work rather than a single zero-shot generation.
✅ pass - reviewable: Expected outputs are derived by solution/model.py (an independent implementation of the manual) run through solution/seal.py, not hand-typed; a non-specialist reviewer can read the short manual and model.py side by side and verify correctness, or recompute the shipped-file SHA-256 checks directly.
✅ pass - instruction_concision: Uses backticked absolute paths throughout, no headings/roleplay/tool-listing, and describes the desired end state and scope constraints rather than implementation steps. It restates rule 1.3's numeric limits (already in the manual) for clarity, which is slightly redundant but not a solution hint.
✅ pass - solution_quality: solution/fix.patch is a genuine unified diff altering the actual logic (day-charging formula, allowance constant, odometer turnover math, fuel fee/base, tax rounding), not a hardcoded answer; files are reasonably small and not bloated heredocs in solve.sh.
✅ pass - separate_verifier_configured: tests/Dockerfile bakes pytest/pytest-json-ctrf and pre-creates /app and /logs/verifier; all verifier inputs (agreement files, driver, expected fixtures) come from the artifacts=['/app/'] declaration or tests/ itself. tests/shipped/app files are byte-identical to environment/app (verified for driver, mileage.py, fuel.py, time_charge.py), and the base-image digest matches between environment/Dockerfile and tests/Dockerfile.
✅ pass - environment_hygiene: environment/Dockerfile only COPYs app/ and installs task-relevant packages (tmux, asciinema, patch, git); no tests/solution content or test-only deps (pytest, ctrf) leak into the agent image. tests/Dockerfile owns pytest/ctrf and its own mkdir/chmod setup; apt is properly updated/cleaned in the agent Dockerfile.
✅ pass - structured_data_schema: environment/app/README.md normatively documents the exact agreement-file and bill-run JSON schemas (field names and types), which the instruction explicitly references as authoritative alongside the manual.
✅ pass - typos: No typos found in filenames, paths, commands, or variable names. Minor inline comment mislabeling exists (jobgen.py/model.py tag turnover as rule '2.5' and refuelling as '2.6' instead of the manual's 2.4/2.5), but this is a comment cross-reference slip, not a filename/path/command/variable-name typo, and test names and the manual itself use the correct numbers.
✅ pass - difficulty_explanation_quality: difficulty_explanation clearly identifies the specific bugs, the two undefined-behavior traps, why a naive/well-intentioned fix would fail, states the data is synthetic and hand-built at the limits, and names the real-world persona (a rental-billing analyst) who would do this work.
✅ pass - solution_explanation_quality: solution_explanation concisely summarizes each rule change and matches fix.patch exactly (day formula, 150-mile allowance, turnover addition, refuelling fee, tax base/rounding), and correctly notes the driver is untouched.
✅ pass - verification_explanation_quality: verification_explanation is dense and concrete: it describes the sealing/isolation mechanism, the sealed-fixture SHA-256 pinning, the specific edge-case inputs used per family, the mutant/alternative-solution validation, and the anti-cheat unreadability test — all consistent with the actual test_outputs.py content. No unjustified numeric tolerances are used (all comparisons are exact integers).
✅ pass - category_and_tags: category='Operations'/subcategory='Finance' fits a billing-rule-compliance task (the Python tooling is incidental to the finance/business-rules domain), and tags (car-rental, billing, rental-agreements, sales-tax, revenue-operations) are specific and descriptive rather than generic.
✅ pass - no_extraneous_files: Every file inventoried (instruction.md, task.toml, environment/*, solution/*, tests/*) is referenced by a Dockerfile, the instruction, solve.sh, or the test suite; no editor cruft, backups, or unused assets were found.
✅ pass - verifier_execution_isolation: Agent-produced code is only ever executed via setpriv as an unprivileged uid (65534) in its own session, never imported in-process by the root pytest process; /logs/verifier is chmod 700 before any candidate code runs, and reward is derived by root from pytest's exit code plus a byte-comparison. A theoretical pipe-hold-open-by-a-detached-daemon edge case (stdout/stderr as PIPE rather than temp files) could cause a hang, but that only risks a false failure/timeout, not a forged pass, since reward defaults to 0 until pytest explicitly succeeds.
✅ pass - ctrf_reporting: test.sh invokes `python3 -I -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA`, matching the standard per-test CTRF reporting pattern with pinned pytest/pytest-json-ctrf versions baked into tests/Dockerfile.
✅ pass - do_not_modify_enforced: The instruction's 'leave that driver exactly as it is... byte for byte' constraint is enforced both directly (test_submitted_driver_unchanged hashes the delivered bytes captured before the verifier's overwrite) and via isolation (the verifier immediately replaces the driver with its own shipped copy before any grading run, so a tampered driver can never influence functional results). The implicit 'only change the package' scope is enforced via SHA-256 checks on README/manual/example (test_only_the_package_changed).
✅ pass - binary_reward: tests/test.sh only ever writes exactly '0' or '1' to /logs/verifier/reward.txt: it defaults to 0, and sets 1 only when pytest's exit code is 0 and a `cmp -s` byte-comparison of the driver succeeds; no fractional or weighted scoring path exists.

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
QUALITY PANEL: NEEDS REVISION -- 3 blocking issues to fix. Details for each are below.

Blocking (fix every one):
   1. [Coherent Contract] MAJOR: The bill schema declares all listed fields, including id, to be
      integers, while the disclosed identifier schema and shipped implementation use strings and
      the verifier requires string identifiers.
   2. [Sound Verifier] MAJOR: No graded sub-day rental returns short of fuel, allowing an
      implementation to apply the refuelling fee only to day rentals.
   3. [Sound Verifier] MAJOR: All tested rentals shorter than an hour remain within the mileage
      allowance, so an unconditional zero-mileage-charge shortcut for that duration passes.

Checked and clean: Correct Reference Solution, Protected Ground Truth, Deterministic Execution.

------------------------------------------------------------------------------------------------
DETAILS
------------------------------------------------------------------------------------------------

1. [Coherent Contract] MAJOR -- contradictory authorities
   The bill schema declares all listed fields, including id, to be integers, while the disclosed
   identifier schema and shipped implementation use strings and the verifier requires string
   identifiers.
   Why this fails:
     Reach: tests/expected/07-order_and_totals.jsonl contains the valid agreement id "0", and
     test_bill_order_and_file_totals grades that family. README lines 29–32 list id alongside
     days, miles, and charges and then say 'all integers'. Yet README line 19 defines agreement
     ids as strings, and the candidate-visible run.py line 17 copies agreement["id"] unchanged.
     The conflict is also evident for the reviewer's "G1" example, which has no specified
     integer representation. Flip: for the numeric-looking id "0", following the literal
     integer-output requirement produces id 0; preserving the identifier as the shipped
     implementation does produces id "0". compare() lines 224–227 compares the id, and _same()
     line 214 rejects 0 against the expected "0" because both type and value must match.
     Producing the accepted string instead violates the unqualified 'all integers' output
     declaration. I checked instruction.md, task.toml, README, RC-3, the example, and every
     shipped package/driver file: the starter discloses the intended string behavior, but no
     text explicitly exempts id from the contradictory output-type declaration; instruction.md
     line 5 repeats an overbroad JSON-integer requirement.
   Where to look: environment/app/README.md:17-22, environment/app/README.md:28-32,
     instruction.md:5, environment/app/src/rentcharge/run.py:16-22,
     tests/expected/07-order_and_totals.jsonl:1, tests/test_outputs.py:213-227 (+1 more)

2. [Sound Verifier] MAJOR -- Missing combined-condition coverage
   No graded sub-day rental returns short of fuel, allowing an implementation to apply the
   refuelling fee only to day rentals.
   Why this fails:
     Reach: use one agreement with id A, out 2028-04-04T14:00, in 2028-04-04T14:01, odometer_out
     10000, odometer_in 10005, fuel_out 8, fuel_in 7, day_rate 5000, mile_rate 30, fuel_rate
     600, and branch X. This is within rule 1.3. Correct figures are days 1, miles 5,
     time_charge 5000, mileage_charge 0, fuel_charge 2100, tax 413, total/revenue 7513. Flip: an
     otherwise correct repair that preserves the old fuel difference calculation but adds 1500
     only when fuel_out > fuel_in AND duration >= 1440 instead produces fuel_charge 600 and
     total/revenue 6013. Such an incorrect scoping of the fee to the manual's day-rental branch
     is a plausible repair mistake. It passes every shown graded input: the only families
     permitted to contain sub-day rentals are short_days, short_allowance, and traps_combined;
     their complete fixtures contain only equal or fuller returns. For those, the fee is
     correctly absent under both implementations. All actual shortages in the remaining fixtures
     last at least a day, so the defective extra duration condition is true and all compared
     fields match. Relabelling operates only on generated day rentals and preserves durations
     and fuel levels. Leaving all non-package files untouched also passes the integrity
     assertions.
   Where to look: environment/app/docs/rental-charges-manual.md:48-60, tests/test_outputs.py:55,
     tests/test_outputs.py:189-209, tests/expected/08-short_days.jsonl:1,
     tests/expected/09-short_allowance.jsonl:1, tests/expected/11-traps_combined.jsonl:1

3. [Sound Verifier] MAJOR -- Missing combined-condition coverage
   All tested rentals shorter than an hour remain within the mileage allowance, so an
   unconditional zero-mileage-charge shortcut for that duration passes.
   Why this fails:
     Reach: take a single agreement with id A, branch X, out 2028-04-04T14:00, in
     2028-04-04T14:59, odometer_out 10000, odometer_in 10151, fuel_out and fuel_in 8, day_rate
     5000, mile_rate 30, and fuel_rate 600. Rule 1.3 imposes no speed restriction, so this
     59-minute, 151-mile rental is legal. The preserved days calculation gives 1; the allowance
     is 150, mileage_charge is 30, taxable charges are 5030, tax is 415, and total/revenue is
     5445. Flip: an otherwise correct implementation with `if length(agreement) < 60: return 0`
     in mileage_charge instead produces mileage_charge 0, tax 413, and total/revenue 5413. This
     is a plausible but unauthorized short-trip shortcut. It passes every shown test: the
     sub-hour S1, S2, and S3 cases drive 5, 12, and 40 miles, and C1 drives 130, all correctly
     owing zero mileage charge anyway. The excess-mileage sub-day cases L3 and L4 last 90 and
     1439 minutes, so they do not exercise the shortcut. Every other graded rental lasts at
     least an hour. Consequently the added guard changes no graded bill field or aggregate,
     while the distinguishing legal input would fail the exact comparison.
   Where to look: instruction.md:3, environment/app/docs/rental-charges-manual.md:25-31,
     environment/app/docs/rental-charges-manual.md:55-57, tests/expected/08-short_days.jsonl:1,
     tests/expected/09-short_allowance.jsonl:1, tests/expected/11-traps_combined.jsonl:1 (+1
     more)
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
  - AutoEval execution succeeded. Build status: SUCCEEDED. Build ID: CodeExecutionEnvironment:8cf808e1-c499-4636-8982-522a1f2f5df1.

## 10. Evaluation Rubrics

### test_rubrics

```
Agent charges a rental of a day or more for its whole days of 1,440 minutes and one more day only when more than 59 minutes are left over, instead of every day begun, +2
Agent allows 150 free miles for each day charged instead of the old 100, and charges the mile rate only for miles beyond the allowance, +2
Agent adds 1,000,000 miles when the odometer came back reading less than it went out, so a turned-over odometer gives the true miles driven, +2
Agent charges a car brought back short of fuel the fuel rate for each eighth short plus the 1,500-cent refuelling fee, +2
Agent taxes only the time and mileage charges at 8.25 per cent and rounds the tax to the nearest cent with an exact half cent going up, +2
Agent keeps the package's existing every-day-begun step for a rental under a day, so a rental of under an hour is still charged one day, +3
Agent keeps the package's existing fuel line for a car brought back with as much fuel or more, nought or a credit of the fuel rate per eighth over, with no refuelling fee, +3
Agent leaves /app/tools/rentcharge_run.py byte-for-byte as shipped, +1
Agent returns the branch exactly as the file gives it, whatever the string, and bills a file passed under any pathname, +1
Agent applies the 59-minute grace rule to rentals under a day, so a rental of under an hour is charged for no days, -3
Agent floors the fuel line at nought, or adds the refuelling fee, for a car brought back with as much fuel or more, -3
Agent still taxes the fuel charge or rounds the tax down, -2
Agent edits the rental charges manual, the README or the example file, or hardcodes bill figures for particular agreements, instead of repairing the package, -5
```

## 10b. Automated Feedback

| Field | Value |
|---|---|
| Eval revision notes | `Agent Runner Summary: Evaluation FAILED. Pre-difficulty quality or quality panel gate failed; difficulty not run` |
| Eval revision requested at | `2026-09-28T03:04:22.129745Z` |
| Rebuttal notes | `` |

### Evaluation History (oldest first)

| # | Created | Outcome | Blocking stage | Stages |
|---|---|---|---|---|
| 1 | `2026-09-27T15:37:27.370586Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |
| 2 | `2026-09-28T02:23:32.378512Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |

## 11. Reviewer Decision

| Field | Value |
|---|---|
| Submission Review Decision | **—** |

### Revision Notes

_(none)_

---

_Generated by TB Task Revise Extractor from the Snorkel Experts task payload._
