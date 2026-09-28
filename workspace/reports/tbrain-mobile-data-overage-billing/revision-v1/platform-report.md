# Terminal Bench 2.0 — Task Revise Report

> Comprehensive task information extracted from the Snorkel Experts task payload.
> This is the same data that populates the task's right-hand **Revise panel** (Difficulty Explanation, Solution Explanation, checks, rubrics, agent runs, etc.).

## 1. Task Identity & Metadata

| Field | Value |
|---|---|
| Project | `Terminus-3-Prod` |
| Project ID | `a34832f4-76f4-4d2a-aa62-c92deb15675d` |
| Assignment ID | `e2514166-3a4e-4c06-8a87-84b9b91219ea` |
| Task ID | `0a753a92-aa98-45a1-9151-c633263ce621` |
| Submission ID | `0a753a92-aa98-45a1-9151-c633263ce621` |
| Task category (stage) | `SUBMISSION` |
| Submission task type | `submission-8d482d68-4d7e-449f-9388-b3cb0cefb643` |
| Review task type | `submission-8d482d68-4d7e-449f-9388-b3cb0cefb643` |
| Form schema revision | `9110301d-4bfc-42cc-8185-74945ca1a856` |
| Skippable | `false` |
| Further revisions allowed | `true` |
| Expiry time | `2027-02-25T02:47:33.741530Z` |

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
| Filename | `tbrain-mobile-data-overage-billing.zip` |
| Uploaded at | `2026-09-28T02:29:26.663Z` |
| S3 URI | `s3://daas-blobs/prd/a34832f4-76f4-4d2a-aa62-c92deb15675d/e2514166-3a4e-4c06-8a87-84b9b91219ea/86dbf33c-b3c6-40b0-b98a-9b94c248f08f_submission_2026-09-28T02:29:25.352Z.zip` |
| S3 key | `prd/a34832f4-76f4-4d2a-aa62-c92deb15675d/e2514166-3a4e-4c06-8a87-84b9b91219ea/86dbf33c-b3c6-40b0-b98a-9b94c248f08f_submission_2026-09-28T02:29:25.352Z.zip` |

- **Difficulty-check artifact:** `s3://daas-blobs/codebuild_uploads/autoeval_artifacts/agent_runner/b7d816eb-b4a8-496c-8ad8-eb523cce2dcb/difficulty_check/fb07cdcebf6d/logs_artifact.zip`

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

QUALITY PANEL: NEEDS REVISION -- 1 blocking issue to fix. Details for each are below.

Blocking (fix every one):
   1. [Sound Verifier] MAJOR: All graded account names are uppercase MD2 labels, so account
      normalization can pass despite the requirement to preserve any supplied account string.

Checked and clean: Coherent Contract, Correct Reference Solution, Protected Ground Truth,
  Deterministic Execution.

------------------------------------------------------------------------------------------------
DETAILS
------------------------------------------------------------------------------------------------

1. [Sound Verifier] MAJOR -- missing behavioral coverage
   All graded account names are uppercase MD2 labels, so account normalization can pass despite
   the requirement to preserve any supplied account string.
   Why this fails:
     Reach: use the contract-legal input
     {"account":"a","lines":[{"id":"A","plan":"BASIC","sessions":[1],"rate":1}]}. The account
     may be any string, and this file satisfies every tariff limit. Submit an otherwise correct
     package with only the statement's account expression changed from usage["account"] to
     usage["account"].upper(), leaving the driver unchanged. Correct arithmetic produces used=1,
     allowance=2048, over=-2047, charge=-2047, total=-2047; the required account is "a", but the
     mutation emits "A". Flip: all thirteen sealed accounts are named MD2-0001 through MD2-0013.
     For each, upper() is the identity. The additional runs obtain their names at
     test_outputs.py:264 as "MD2-" plus eight uppercase letters or digits, so upper() is also
     the identity there. run() parses the unchanged driver's JSON output, and compare() receives
     exactly the expected account string, every correct line field, and the correct total. Thus
     all behavioral comparisons pass, while the mutation neither changes driver bytes nor
     affects the isolation assertions. Adding the distinguishing input would fail the account
     comparison at line 199. Reviewer 2's original session value was outside the tariff domain;
     [1] repairs that issue. This is reachable through ordinary overzealous billing-name
     normalization, without knowing the verifier's parsing or comparison internals.
   Where to look: environment/app/README.md:17, environment/app/README.md:25-30,
     environment/app/docs/data-usage-tariff.md:14-22,
     environment/app/src/usagebill/statement.py:14-16, tests/test_outputs.py:143-147,
     tests/test_outputs.py:192-211 (+3 more)
```

## 5. Quality Check Results

### Quality Check Summary

```
## Quality Check Results
✅ pass - verifiable: The verifier is a deterministic pytest suite (tests/test_outputs.py) that runs the delivered driver as an unprivileged user against sealed, SHA-256-pinned expected outputs (tests/expected/*.jsonl + ROSTER). No LLM-as-judge, no network calls, no runtime installs in test.sh (deps baked into tests/Dockerfile). Comparisons are exact equality on JSON keys/types, which is fully reproducible run-to-run.
✅ pass - solvable: solution/fix.patch (applied by solve.sh) makes a small, well-scoped change to usage.py and charges.py (ceil-rounding per session, per-plan allowance dict, tiered overage charge) that matches solution/model.py's independent tariff model and the sealed expected outputs verified by hand-computation (e.g. 01-sessions.jsonl S1: sessions [1999872,97280,1] -> used 2049, over 1, charge 7, matches the patched charge() logic). An expert could implement this in well under the 2-hour estimate.
✅ pass - difficult: The task requires precisely reconciling three tariff rules against existing code while resisting the natural but incorrect urge to clamp/guard undefined cases (FLEX allowance, in-allowance credit) that the tariff does not specify — a genuine, easy-to-miss trap documented and tested (not_over/flex/together families allow negative 'credit' charges). This is tedious-but-error-prone spec-compliance work, which the rubric explicitly allows as legitimate difficulty, though it stops short of requiring deep specialized domain theory.
✅ pass - interesting: Reconciling a billing engine against a published tariff is realistic work for a telecom billing/rating analyst or backend engineer maintaining rating software; this is a small-scale but faithful analogue of real carrier billing-compliance maintenance.
✅ pass - outcome_verified: Tests only run the documented command (python3 /app/tools/usagebill_run.py USAGE.json) and check its JSON output; they do not care which files/tools/approach the agent uses internally, only the resulting statement values and the unmodified driver bytes.
✅ pass - anti_cheat_robustness: Ground truth (tests/expected, model.py, jobgen.py) lives only in the verifier image; the agent image (environment/Dockerfile) copies only app/ and environment/.dockerignore excludes solution/ and tests/. The verifier additionally seals /app root-owned, runs candidate code as a separate low-priv UID with a stripped env, and test_candidate_cannot_read_verifier_state explicitly checks /tests, expected data, the shipped copy, and /logs/verifier are unreadable to the candidate's uid.
✅ pass - task_security: All scripts (Dockerfiles, test.sh, test_outputs.py, solve.sh, seal.py, jobgen.py, model.py) perform only legitimate setup/verification actions (chmod/chown scoped to /app, /tests, /logs/verifier; setpriv for privilege drop). No exfiltration, obfuscation, prompt injection, or destructive operations were found.
✅ pass - functional_verification: Verification executes the actual driver via subprocess and parses/compares its JSON stdout against precomputed expected statements; there is no string/keyword matching against source code.
✅ pass - deterministic_reproducible: Both Docker images pin the base image by digest; pytest/pytest-json-ctrf are version-pinned in tests/Dockerfile; apt packages are unpinned (correct per guidance) with proper update+cleanup. No live services are used (network_mode = no-network for agent and verifier); random relabeling in test_generated_account_files uses os.urandom only to vary labels, not correctness, so any correct solution passes deterministically.
✅ pass - essential_difficulty: Difficulty stems from correctly implementing three tariff rules and correctly leaving two undefined cases unchanged — genuine logical/spec-reasoning work. Output comparison is exact-value JSON matching on a small, clearly documented schema, not fuzzy formatting minutiae.
✅ pass - test_instruction_alignment: Every test (sessions rounding, plan allowances, later-rate tiering, order/total, flex, not_over, together, limits, generated, driver-unchanged, anti-cheat) traces directly to a requirement stated in instruction.md (tariff compliance, rule-1.2 limits, driver preservation, README key/order comparison); no test introduces requirements absent from the instruction.
✅ pass - novel: This is a bespoke, custom billing package and tariff document invented for the task, not a well-known textbook problem; the specific 'don't over-clamp undefined behavior' trap is a novel combination not reproducible from memorized solutions.
✅ pass - agentic: Solving requires reading the tariff doc, exploring three source files and a driver/README, editing code, and iteratively verifying against the example/driver — multi-step file exploration and editing rather than a single zero-shot text answer.
✅ pass - reviewable: The tariff (data-usage-tariff.md) is short and precise, model.py cites tariff rule numbers directly, and expected values are derived programmatically from model.py via seal.py rather than hardcoded, letting a non-specialist trace correctness without deep telecom expertise.
✅ pass - instruction_concision: instruction.md is short (5 paragraphs), uses absolute paths (/app/src/usagebill, /app/docs/data-usage-tariff.md, /app/tools/usagebill_run.py, /app/examples/) with backticks, has no headings/roleplay/fluff, and states the end goal (tariff compliance) rather than an implementation procedure.
✅ pass - solution_quality: solve.sh applies a small, genuine diff (fix.patch) derived from real reasoning about the tariff, rather than echoing a final answer; the patch is kept in its own file rather than inlined as a large heredoc, consistent with guidance.
✅ pass - separate_verifier_configured: environment_mode='separate' in task.toml; verifier reads only the declared artifact (/app/tools/usagebill_run.py, and /app more broadly per artifacts=["/app/"]) plus files baked into tests/ (expected/, shipped/); tests/Dockerfile bakes pytest/pytest-json-ctrf at build time rather than in test.sh; tests/shipped/app files are byte-identical to environment/app's pre-patch source, confirmed by direct comparison.
✅ pass - environment_hygiene: environment/Dockerfile only COPYs app/ (no tests/solution leakage, reinforced by .dockerignore); apt install is followed by rm -rf /var/lib/apt/lists/* with no version pins (correct for apt). tests/Dockerfile owns pytest/ctrf install and /tests/*, with no apt in that image needing cleanup rules.
✅ pass - structured_data_schema: environment/app/README.md normatively documents the exact account-file and statement JSON schemas (field names, types, units) referenced by both instruction.md and the verifier's compare() logic.
✅ pass - typos: No typos were found in filenames, paths, identifiers, or prose across instruction.md, source files, tests, and solution scripts on close inspection.
✅ pass - difficulty_explanation_quality: difficulty_explanation clearly names the three specific bugs and the clamp/guard trap, states the data is synthetic and hand-built to sit on limits, and identifies the real-world role (telecom billing analyst) — meeting all stated content requirements without citing pass rates.
✅ pass - solution_explanation_quality: solution_explanation concisely summarizes the patch strategy (whole-MB rounding, per-plan allowance, tiered overage charge, leaving undefined cases as-is) and is fully consistent with fix.patch and model.py.
✅ pass - verification_explanation_quality: verification_explanation accurately describes the sealed-expectation approach, SHA-256/ROSTER pinning, per-rule test breakdown, unprivileged execution, and anti-cheat checks, all of which are verifiably present in test_outputs.py; checks are exact-equality (no unjustified tolerance ranges) so no calibration justification is needed.
✅ pass - category_and_tags: category='Operations', subcategory='Finance' fits a billing/tariff-compliance engineering task well; tags (telecom-billing, mobile-data, usage-rating, tariff-compliance, overage-charges) are specific and descriptive rather than generic.
✅ pass - no_extraneous_files: Every file traced to a purpose: environment/app is copied by the Dockerfile and referenced by instruction/README; solution/{seal.py,jobgen.py,model.py,fix.patch,solve.sh} are all used in generating/applying the reference fix and expected data; tests/* are all read by test_outputs.py or copied by tests/Dockerfile. No cruft or unused files were found.
✅ pass - verifier_execution_isolation: The verifier drops privileges via setpriv to an unprivileged CANDIDATE_UID (65534) with cleared groups and no-new-privs, in its own session, output captured via pipes with explicit process-group kill afterward; /logs/verifier is chmod 700 before any candidate code runs, and root (test.sh) derives the reward solely from the pytest exit code and a driver-bytes comparison — the executed candidate code never has access to the reward path.
✅ pass - ctrf_reporting: test.sh invokes pytest with --ctrf /logs/verifier/ctrf.json directly, and since the pytest process itself runs as root, no additional copy step is needed; this covers the 11 discrete test cases.
✅ pass - do_not_modify_enforced: The instruction's 'leave that driver exactly as it is; the file you leave has to match ours byte for byte' constraint is directly enforced by test_submitted_driver_unchanged, which byte-compares the delivered driver (recorded before being overwritten by the verifier's own copy) against the shipped reference, and separately checks ownership/permissions to ensure it wasn't writable by the candidate.
✅ pass - binary_reward: test.sh only ever writes literal 0 or 1 to /logs/verifier/reward.txt: initialized to 0, and set to 1 only if the pytest exit code is 0 and the driver bytes match; no fractional or ratio-based reward path exists.

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
✅ pass - verifiable: The verifier is a deterministic pytest suite (tests/test_outputs.py) that runs the delivered driver as an unprivileged user against sealed, SHA-256-pinned expected outputs (tests/expected/*.jsonl + ROSTER). No LLM-as-judge, no network calls, no runtime installs in test.sh (deps baked into tests/Dockerfile). Comparisons are exact equality on JSON keys/types, which is fully reproducible run-to-run.
✅ pass - solvable: solution/fix.patch (applied by solve.sh) makes a small, well-scoped change to usage.py and charges.py (ceil-rounding per session, per-plan allowance dict, tiered overage charge) that matches solution/model.py's independent tariff model and the sealed expected outputs verified by hand-computation (e.g. 01-sessions.jsonl S1: sessions [1999872,97280,1] -> used 2049, over 1, charge 7, matches the patched charge() logic). An expert could implement this in well under the 2-hour estimate.
✅ pass - difficult: The task requires precisely reconciling three tariff rules against existing code while resisting the natural but incorrect urge to clamp/guard undefined cases (FLEX allowance, in-allowance credit) that the tariff does not specify — a genuine, easy-to-miss trap documented and tested (not_over/flex/together families allow negative 'credit' charges). This is tedious-but-error-prone spec-compliance work, which the rubric explicitly allows as legitimate difficulty, though it stops short of requiring deep specialized domain theory.
✅ pass - interesting: Reconciling a billing engine against a published tariff is realistic work for a telecom billing/rating analyst or backend engineer maintaining rating software; this is a small-scale but faithful analogue of real carrier billing-compliance maintenance.
✅ pass - outcome_verified: Tests only run the documented command (python3 /app/tools/usagebill_run.py USAGE.json) and check its JSON output; they do not care which files/tools/approach the agent uses internally, only the resulting statement values and the unmodified driver bytes.
✅ pass - anti_cheat_robustness: Ground truth (tests/expected, model.py, jobgen.py) lives only in the verifier image; the agent image (environment/Dockerfile) copies only app/ and environment/.dockerignore excludes solution/ and tests/. The verifier additionally seals /app root-owned, runs candidate code as a separate low-priv UID with a stripped env, and test_candidate_cannot_read_verifier_state explicitly checks /tests, expected data, the shipped copy, and /logs/verifier are unreadable to the candidate's uid.
✅ pass - task_security: All scripts (Dockerfiles, test.sh, test_outputs.py, solve.sh, seal.py, jobgen.py, model.py) perform only legitimate setup/verification actions (chmod/chown scoped to /app, /tests, /logs/verifier; setpriv for privilege drop). No exfiltration, obfuscation, prompt injection, or destructive operations were found.
✅ pass - functional_verification: Verification executes the actual driver via subprocess and parses/compares its JSON stdout against precomputed expected statements; there is no string/keyword matching against source code.
✅ pass - deterministic_reproducible: Both Docker images pin the base image by digest; pytest/pytest-json-ctrf are version-pinned in tests/Dockerfile; apt packages are unpinned (correct per guidance) with proper update+cleanup. No live services are used (network_mode = no-network for agent and verifier); random relabeling in test_generated_account_files uses os.urandom only to vary labels, not correctness, so any correct solution passes deterministically.
✅ pass - essential_difficulty: Difficulty stems from correctly implementing three tariff rules and correctly leaving two undefined cases unchanged — genuine logical/spec-reasoning work. Output comparison is exact-value JSON matching on a small, clearly documented schema, not fuzzy formatting minutiae.
✅ pass - test_instruction_alignment: Every test (sessions rounding, plan allowances, later-rate tiering, order/total, flex, not_over, together, limits, generated, driver-unchanged, anti-cheat) traces directly to a requirement stated in instruction.md (tariff compliance, rule-1.2 limits, driver preservation, README key/order comparison); no test introduces requirements absent from the instruction.
✅ pass - novel: This is a bespoke, custom billing package and tariff document invented for the task, not a well-known textbook problem; the specific 'don't over-clamp undefined behavior' trap is a novel combination not reproducible from memorized solutions.
✅ pass - agentic: Solving requires reading the tariff doc, exploring three source files and a driver/README, editing code, and iteratively verifying against the example/driver — multi-step file exploration and editing rather than a single zero-shot text answer.
✅ pass - reviewable: The tariff (data-usage-tariff.md) is short and precise, model.py cites tariff rule numbers directly, and expected values are derived programmatically from model.py via seal.py rather than hardcoded, letting a non-specialist trace correctness without deep telecom expertise.
✅ pass - instruction_concision: instruction.md is short (5 paragraphs), uses absolute paths (/app/src/usagebill, /app/docs/data-usage-tariff.md, /app/tools/usagebill_run.py, /app/examples/) with backticks, has no headings/roleplay/fluff, and states the end goal (tariff compliance) rather than an implementation procedure.
✅ pass - solution_quality: solve.sh applies a small, genuine diff (fix.patch) derived from real reasoning about the tariff, rather than echoing a final answer; the patch is kept in its own file rather than inlined as a large heredoc, consistent with guidance.
✅ pass - separate_verifier_configured: environment_mode='separate' in task.toml; verifier reads only the declared artifact (/app/tools/usagebill_run.py, and /app more broadly per artifacts=["/app/"]) plus files baked into tests/ (expected/, shipped/); tests/Dockerfile bakes pytest/pytest-json-ctrf at build time rather than in test.sh; tests/shipped/app files are byte-identical to environment/app's pre-patch source, confirmed by direct comparison.
✅ pass - environment_hygiene: environment/Dockerfile only COPYs app/ (no tests/solution leakage, reinforced by .dockerignore); apt install is followed by rm -rf /var/lib/apt/lists/* with no version pins (correct for apt). tests/Dockerfile owns pytest/ctrf install and /tests/*, with no apt in that image needing cleanup rules.
✅ pass - structured_data_schema: environment/app/README.md normatively documents the exact account-file and statement JSON schemas (field names, types, units) referenced by both instruction.md and the verifier's compare() logic.
✅ pass - typos: No typos were found in filenames, paths, identifiers, or prose across instruction.md, source files, tests, and solution scripts on close inspection.
✅ pass - difficulty_explanation_quality: difficulty_explanation clearly names the three specific bugs and the clamp/guard trap, states the data is synthetic and hand-built to sit on limits, and identifies the real-world role (telecom billing analyst) — meeting all stated content requirements without citing pass rates.
✅ pass - solution_explanation_quality: solution_explanation concisely summarizes the patch strategy (whole-MB rounding, per-plan allowance, tiered overage charge, leaving undefined cases as-is) and is fully consistent with fix.patch and model.py.
✅ pass - verification_explanation_quality: verification_explanation accurately describes the sealed-expectation approach, SHA-256/ROSTER pinning, per-rule test breakdown, unprivileged execution, and anti-cheat checks, all of which are verifiably present in test_outputs.py; checks are exact-equality (no unjustified tolerance ranges) so no calibration justification is needed.
✅ pass - category_and_tags: category='Operations', subcategory='Finance' fits a billing/tariff-compliance engineering task well; tags (telecom-billing, mobile-data, usage-rating, tariff-compliance, overage-charges) are specific and descriptive rather than generic.
✅ pass - no_extraneous_files: Every file traced to a purpose: environment/app is copied by the Dockerfile and referenced by instruction/README; solution/{seal.py,jobgen.py,model.py,fix.patch,solve.sh} are all used in generating/applying the reference fix and expected data; tests/* are all read by test_outputs.py or copied by tests/Dockerfile. No cruft or unused files were found.
✅ pass - verifier_execution_isolation: The verifier drops privileges via setpriv to an unprivileged CANDIDATE_UID (65534) with cleared groups and no-new-privs, in its own session, output captured via pipes with explicit process-group kill afterward; /logs/verifier is chmod 700 before any candidate code runs, and root (test.sh) derives the reward solely from the pytest exit code and a driver-bytes comparison — the executed candidate code never has access to the reward path.
✅ pass - ctrf_reporting: test.sh invokes pytest with --ctrf /logs/verifier/ctrf.json directly, and since the pytest process itself runs as root, no additional copy step is needed; this covers the 11 discrete test cases.
✅ pass - do_not_modify_enforced: The instruction's 'leave that driver exactly as it is; the file you leave has to match ours byte for byte' constraint is directly enforced by test_submitted_driver_unchanged, which byte-compares the delivered driver (recorded before being overwritten by the verifier's own copy) against the shipped reference, and separately checks ownership/permissions to ensure it wasn't writable by the candidate.
✅ pass - binary_reward: test.sh only ever writes literal 0 or 1 to /logs/verifier/reward.txt: initialized to 0, and set to 1 only if the pytest exit code is 0 and the driver bytes match; no fractional or ratio-based reward path exists.

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
QUALITY PANEL: NEEDS REVISION -- 1 blocking issue to fix. Details for each are below.

Blocking (fix every one):
   1. [Sound Verifier] MAJOR: All graded account names are uppercase MD2 labels, so account
      normalization can pass despite the requirement to preserve any supplied account string.

Checked and clean: Coherent Contract, Correct Reference Solution, Protected Ground Truth,
  Deterministic Execution.

------------------------------------------------------------------------------------------------
DETAILS
------------------------------------------------------------------------------------------------

1. [Sound Verifier] MAJOR -- missing behavioral coverage
   All graded account names are uppercase MD2 labels, so account normalization can pass despite
   the requirement to preserve any supplied account string.
   Why this fails:
     Reach: use the contract-legal input
     {"account":"a","lines":[{"id":"A","plan":"BASIC","sessions":[1],"rate":1}]}. The account
     may be any string, and this file satisfies every tariff limit. Submit an otherwise correct
     package with only the statement's account expression changed from usage["account"] to
     usage["account"].upper(), leaving the driver unchanged. Correct arithmetic produces used=1,
     allowance=2048, over=-2047, charge=-2047, total=-2047; the required account is "a", but the
     mutation emits "A". Flip: all thirteen sealed accounts are named MD2-0001 through MD2-0013.
     For each, upper() is the identity. The additional runs obtain their names at
     test_outputs.py:264 as "MD2-" plus eight uppercase letters or digits, so upper() is also
     the identity there. run() parses the unchanged driver's JSON output, and compare() receives
     exactly the expected account string, every correct line field, and the correct total. Thus
     all behavioral comparisons pass, while the mutation neither changes driver bytes nor
     affects the isolation assertions. Adding the distinguishing input would fail the account
     comparison at line 199. Reviewer 2's original session value was outside the tariff domain;
     [1] repairs that issue. This is reachable through ordinary overzealous billing-name
     normalization, without knowing the verifier's parsing or comparison internals.
   Where to look: environment/app/README.md:17, environment/app/README.md:25-30,
     environment/app/docs/data-usage-tariff.md:14-22,
     environment/app/src/usagebill/statement.py:14-16, tests/test_outputs.py:143-147,
     tests/test_outputs.py:192-211 (+3 more)
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
  - AutoEval execution succeeded. Build status: SUCCEEDED. Build ID: CodeExecutionEnvironment:65c00975-081c-4719-b5e1-822ec5840ba9.

## 10. Evaluation Rubrics

### test_rubrics

```
Agent measures each data session on its own in whole megabytes of 1,024 kilobytes, a part megabyte counting as a whole one, and sums the sessions, +2
Agent gives a BASIC line an allowance of 2,048 MB and a PLUS line 10,240 MB, +2
Agent charges a line over its allowance its overage rate for each of the first 1,024 MB of overage and 1 cent for each megabyte after, +2
Agent keeps the statement total as the plain sum of every line's charge, in file order, +1
Agent keeps the package's existing 5,120 MB allowance for a FLEX line, +3
Agent keeps the package's existing overage and charge for a line inside its allowance, its usage less its allowance and that many megabytes at its rate, nought or a credit, +3
Agent leaves /app/tools/usagebill_run.py byte-for-byte as shipped, +1
Agent floors the overage or the charge of a line inside its allowance at nought, -3
Agent gives a FLEX line nought or another plan's allowance, -3
Agent still adds up the cycle's kilobytes before converting, or drops part megabytes, -2
Agent edits the data usage tariff or hardcodes statement figures for particular files instead of repairing the package, -5
```

## 10b. Automated Feedback

| Field | Value |
|---|---|
| Eval revision notes | `Agent Runner Summary: Evaluation FAILED. Pre-difficulty quality or quality panel gate failed; difficulty not run` |
| Eval revision requested at | `2026-09-28T02:47:33.741530Z` |
| Rebuttal notes | `` |

### Evaluation History (oldest first)

| # | Created | Outcome | Blocking stage | Stages |
|---|---|---|---|---|
| 1 | `2026-09-28T02:31:12.838145Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |

## 11. Reviewer Decision

| Field | Value |
|---|---|
| Submission Review Decision | **—** |

### Revision Notes

_(none)_

---

_Generated by TB Task Revise Extractor from the Snorkel Experts task payload._
