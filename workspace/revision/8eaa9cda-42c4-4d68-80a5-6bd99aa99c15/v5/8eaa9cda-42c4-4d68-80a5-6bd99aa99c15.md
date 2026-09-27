# Terminal Bench 2.0 — Task Revise Report

> Comprehensive task information extracted from the Snorkel Experts task payload.
> This is the same data that populates the task's right-hand **Revise panel** (Difficulty Explanation, Solution Explanation, checks, rubrics, agent runs, etc.).

## 1. Task Identity & Metadata

| Field | Value |
|---|---|
| Project | `Terminus-3-Prod` |
| Project ID | `a34832f4-76f4-4d2a-aa62-c92deb15675d` |
| Assignment ID | `2b0ac80a-32f9-4d2f-b66c-3b7bf235a842` |
| Task ID | `8eaa9cda-42c4-4d68-80a5-6bd99aa99c15` |
| Submission ID | `8eaa9cda-42c4-4d68-80a5-6bd99aa99c15` |
| Task category (stage) | `SUBMISSION` |
| Submission task type | `submission-8d482d68-4d7e-449f-9388-b3cb0cefb643` |
| Review task type | `submission-8d482d68-4d7e-449f-9388-b3cb0cefb643` |
| Form schema revision | `9110301d-4bfc-42cc-8185-74945ca1a856` |
| Skippable | `false` |
| Further revisions allowed | `true` |
| Expiry time | `2027-02-22T23:52:05.935694Z` |

### Task Classification (submission_document)

| Field | Value |
|---|---|
| Difficulty | **** |
| Solvable | `` |
| Task category | `Software` |
| Task subcategories | `["Languages"]` |
| Task languages | `python`, `cobol` |
| Codebase size | `` |
| Number of milestones | `` |
| Submission AHT (min) | `150` |
| Uses approved canonical base image | `true` |
| Used Task Gallery inspiration | `false` |
| Send to reviewer | `` |
| Generate rubrics | `false` |

## 2. Submission Artifact

| Field | Value |
|---|---|
| Filename | `tbrain-cobol-statement-port.zip` |
| Uploaded at | `2026-09-25T11:52:05.940Z` |
| S3 URI | `s3://daas-blobs/prd/a34832f4-76f4-4d2a-aa62-c92deb15675d/2b0ac80a-32f9-4d2f-b66c-3b7bf235a842/9353db02-8890-4cf8-94fb-b5eaacb85392_submission_2026-09-25T11:52:02.707Z.zip` |
| S3 key | `prd/a34832f4-76f4-4d2a-aa62-c92deb15675d/2b0ac80a-32f9-4d2f-b66c-3b7bf235a842/9353db02-8890-4cf8-94fb-b5eaacb85392_submission_2026-09-25T11:52:02.707Z.zip` |

- **Difficulty-check artifact:** `s3://daas-blobs/codebuild_uploads/autoeval_artifacts/agent_runner/e3483662-eaa3-4c0b-beca-a5b2e7680310/difficulty_check/87869705c5d5/logs_artifact.zip`

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
   1. [Sound Verifier] MAJOR: The capacity test contains 499 customers and a header, leaving a
      plausible 499-customer allocation bug undetected on permitted headerless 500-customer
      inputs.

Checked and clean: Coherent Contract, Correct Reference Solution, Protected Ground Truth,
  Deterministic Execution.

------------------------------------------------------------------------------------------------
DETAILS
------------------------------------------------------------------------------------------------

1. [Sound Verifier] MAJOR -- missing behavioral coverage
   The capacity test contains 499 customers and a header, leaving a plausible 499-customer
   allocation bug undetected on permitted headerless 500-customer inputs.
   Why this fails:
     Reach: Use an empty payments file and a headerless readings file containing 500 distinct,
     valid C records, with account identifiers 00000001 through 00000500. Each record has a
     blank 24-character name, tariff D, previous and current readings 000000, billing days 001,
     arrears +0000000, paid 0000000, and the normal filler. These inputs satisfy the 500-record
     limit and the runbook's numeric and charge limits. The COBOL main loop processes the first
     customer without requiring a header (lines 214–225). Each customer has zero usage, standing
     charge 0.31, VAT 0.02, and current charge and balance 0.33. It therefore bills 500
     customers and totals 165.00.
     Flip: Consider an otherwise faithful Python port that reserves 500 input slots but assumes
     one is the header, retaining only the first 499 customer records for processing. This
     ordinary fixed-capacity/off-by-one implementation produces exactly the correct bytes
     whenever there are at most 499 customers. Every fully shown readings fixture is below that
     threshold, and test_long_run explicitly asserts 500 total records but only 499 C records
     before invoking the same byte comparison. Its payments logic remains unchanged, so the
     500-payment test does not distinguish it. On the distinguishing headerless input it omits
     account 00000500, reports 499 billed, and totals 164.67 instead of 165.00. No shown graded
     invocation exercises that difference. The unshown fixtures cannot independently establish
     additional coverage. This construction arises naturally from assuming the normal header
     consumes one record, without needing knowledge of the verifier's comparison or parsing
     implementation.
   Where to look: instruction.md:3, tests/test_outputs.py:194-204,
     tests/cases/header_missing.dat:1-5, environment/app/legacy/WBILL.cbl:214-228,
     environment/app/legacy/WBILL.cbl:301-332
```

## 5. Quality Check Results

### Quality Check Summary

```
## Quality Check Results
✅ pass - verifiable: The verifier builds the real GnuCOBOL 3.1.2 program in a separate build stage of tests/Dockerfile, generates expected .stmt files for 53 fixed fixture pairs at image-build time, and test_outputs.py does a deterministic byte-for-byte comparison between the agent's port output and those pre-generated files. No LLM-as-judge, no runtime network installs in test.sh (all tooling is baked into tests/Dockerfile), and comparisons are exact byte equality with no tolerance.
✅ pass - solvable: solution/wbill.py is a complete ~370-line reference port; spot-checking it by hand against the disclosed sample (JANE O'HARA record: units=267, bands 30/60/177, usage charge $579.66, standing $28.13, VAT 30.39, current $638.18, balance 573.18) reproduces the shipped tests/samples/2025q1-north.stmt exactly. The solution is implementable by a COBOL-literate expert in the few hours the metadata estimates (4 hours), consistent with rubric guidance.
✅ pass - difficult: The task requires precise reproduction of COBOL numeric-edited PICTURE clauses (floating currency symbols, zero suppression, CR/DB signs, BLANK WHEN ZERO), STRING/UNSTRING delimiter semantics, FUNCTION NUMVAL/TEST-NUMVAL parsing, and four different ROUNDED MODE behaviours plus DIVIDE...REMAINDER truncation quirks — genuine COBOL/mainframe-modernization domain expertise well beyond an undergraduate exercise.
✅ pass - interesting: Porting COBOL batch billing jobs to Python is a real, paid mainframe-modernization activity (utilities, banks); the task's own relevant_experience field names this profession directly, and the scenario (quarterly water billing job step) is realistic rather than a gimmick.
✅ pass - outcome_verified: Tests only compare final output bytes to the job step's own output; the 'Python 3, standard library only' constraint is an anti-cheat/technology constraint (enforced by restricting what programs the unprivileged runner can execute), not a procedural instruction about how to write the port.
✅ pass - anti_cheat_robustness: Ground-truth .stmt files and the GnuCOBOL compiler exist only in the verifier image (built and discarded in an earlier stage); the agent image never receives tests/ or solution/ (Dockerfile only COPYs app/, and .dockerignore also excludes tests/ and solution/). The verifier further locks the unprivileged runner to only the Python interpreter, preventing delegation to any other installed program.
✅ pass - task_security: All Dockerfiles and scripts perform only legitimate build/verify actions (apt installs of gnucobol3/tmux/asciinema, permission hardening, pytest execution); no exfiltration, obfuscation, or destructive operations were found.
✅ pass - functional_verification: test_outputs.py actually executes the submitted wbill.py as a subprocess on real input files and diffs the produced bytes against the oracle output; there is no string/keyword scanning of source.
✅ pass - deterministic_reproducible: Base images are pinned by sha256 digest, pytest/pytest-json-ctrf are version-pinned, all 53 test fixtures are static files (no runtime randomness), and no live external services are used; gnucobol3 is an unpinned apt package which is acceptable per guidance.
✅ pass - essential_difficulty: The hard part is genuine COBOL semantic reasoning (rounding modes, numeric editing, UNSTRING counting rules) rather than arbitrary formatting minutiae for its own sake — the exact byte format is dictated by the domain (COBOL PICTURE clauses), which is the core subject matter being tested.
✅ pass - test_instruction_alignment: Every edge-case category enumerated in instruction.md paragraph 2 (rejected records, meter rollover, credit balances, large commercial accounts, names of every shape, rounding boundaries, short/missing/misplaced headers, every posting kind/amount form/field count/account shape/memo length) has a corresponding named test case in tests/test_outputs.py, and no test introduces requirements outside that contract.
✅ pass - novel: WBILL.cbl is a bespoke, task-specific COBOL program with an invented billing domain; it cannot be solved by recalling a known public program or textbook algorithm.
✅ pass - agentic: Solving requires reading multiple source files (COBOL program, two copybooks, run notes, one sample), iteratively writing and testing a substantial Python program against limited ground truth, and reasoning about many interacting edge cases — well beyond a single zero-shot generation.
✅ pass - reviewable: The verifier derives expected outputs by actually compiling and running the disclosed COBOL source rather than hardcoding them, and the metadata explanations plus the disclosed sample/statement let a non-specialist reviewer sanity-check at least one case by hand, as verified in this audit.
✅ pass - instruction_concision: instruction.md is three short paragraphs, uses absolute paths (/app/legacy/WBILL.cbl, /app/port/wbill.py, /app/legacy/samples), states the goal and required edge-case coverage without prescribing implementation steps, and contains no fluff or headings.
✅ pass - solution_quality: solution/wbill.py performs genuine computation (decimal arithmetic, custom PICTURE-editing routine, UNSTRING/NUMVAL emulation) rather than echoing an answer, and solve.sh simply installs this one real file rather than inlining a large heredoc, matching the guidance to keep long files separate.
✅ pass - separate_verifier_configured: The only file the verifier reads from the agent is the declared artifact /app/port/wbill.py; all verifier tooling (gnucobol3, pytest, pytest-json-ctrf) is baked into tests/Dockerfile with no runtime installs in test.sh; and the WBILL.cbl/CUSTREC.cpy/TARIFFS.cpy/sample files duplicated between environment/app/legacy and tests/legacy+tests/samples were confirmed byte-identical.
✅ pass - environment_hygiene: environment/Dockerfile only COPYs app/ (no tests/ or solution/), installs no test-only dependencies, and cleans apt lists; tests/Dockerfile owns pytest/gnucobol3 and all /tests/* content with proper apt cleanup in both Dockerfiles.
✅ pass - structured_data_schema: The exact output byte format is normatively specified by the COBOL PICTURE clauses in WBILL.cbl (referenced directly by instruction.md) and the run notes in RUNBOOK.md describing line-sequential trimming rules — this is a precise formal specification, not merely illustrative examples.
✅ pass - typos: No typos were found in filenames, paths, commands, or identifiers across instruction.md, task.toml, Dockerfiles, test scripts, or the COBOL/Python sources reviewed.
✅ pass - difficulty_explanation_quality: difficulty_explanation names concrete COBOL semantic pitfalls (numeric-edited high-order truncation, STRING DELIMITED BY double space, UNSTRING COUNT IN semantics, NUMVAL CR/DB handling, per-statement ROUNDED MODE, DIVIDE...REMAINDER truncation) and states who does this work (mainframe-modernisation engineer), without citing pass rates.
✅ pass - solution_explanation_quality: solution_explanation accurately describes the approach actually implemented in solution/wbill.py (fixed-width/delimited parsing, exact-decimal arithmetic with per-field rounding rules, a unified numeric-edit formatting routine, line-sequential trailing-space trimming) and states it was fuzz-tested against the real GnuCOBOL build, congruent with the code.
✅ pass - verification_explanation_quality: verification_explanation precisely matches test_outputs.py/tests/Dockerfile: it describes the two-stage build separating the compiler from the final image, the 29 hand-written + 24 seeded-random cases, the unprivileged unidentifiable-path execution, and the sandboxing that limits the runner to the Python interpreter — all confirmed present in the actual files, with no unexplained tolerance/threshold to justify.
✅ pass - category_and_tags: category=Software/subcategory=Languages fits a COBOL-to-Python language port, and tags (cobol, legacy-migration, numeric-editing, fixed-point-arithmetic, gnucobol) are specific and directly descriptive of the task's skills.
✅ pass - no_extraneous_files: Every file present (instruction.md, task.toml, environment/*, solution/*, tests/* including 53 fixture pairs and duplicated legacy/samples for the verifier build) is referenced by a Dockerfile, the instruction, solve.sh, or the test harness; no cruft, backups, or unused assets were found.
✅ pass - verifier_execution_isolation: test.sh sets /logs/verifier to mode 700 and writes an initial reward before any agent code runs; test_outputs.py executes the submitted port via setpriv --reuid=65534 --regid=65534 --clear-groups --no-new-privs (dropping root), and root's test.sh derives the final reward from pytest's exit code after the run, so the executed agent code can neither discover nor write the reward channel.
✅ pass - ctrf_reporting: test.sh invokes the pinned pytest via '/opt/verifier-venv/bin/python -I -m pytest ... --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA', writing the required CTRF report directly since pytest itself runs as root throughout.
➖ not_applicable - do_not_modify_enforced: instruction.md contains no 'do not modify / preserve' constraint on any concrete artifact for the agent to violate; the port is meant to be written from scratch, so this criterion does not apply.
✅ pass - binary_reward: test.sh only ever writes 'echo 0' or 'echo 1' to /logs/verifier/reward.txt, derived directly from pytest's exit code with no weighted or fractional scoring path.

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
✅ pass - verifiable: The verifier builds the real GnuCOBOL 3.1.2 program in a separate build stage of tests/Dockerfile, generates expected .stmt files for 53 fixed fixture pairs at image-build time, and test_outputs.py does a deterministic byte-for-byte comparison between the agent's port output and those pre-generated files. No LLM-as-judge, no runtime network installs in test.sh (all tooling is baked into tests/Dockerfile), and comparisons are exact byte equality with no tolerance.
✅ pass - solvable: solution/wbill.py is a complete ~370-line reference port; spot-checking it by hand against the disclosed sample (JANE O'HARA record: units=267, bands 30/60/177, usage charge $579.66, standing $28.13, VAT 30.39, current $638.18, balance 573.18) reproduces the shipped tests/samples/2025q1-north.stmt exactly. The solution is implementable by a COBOL-literate expert in the few hours the metadata estimates (4 hours), consistent with rubric guidance.
✅ pass - difficult: The task requires precise reproduction of COBOL numeric-edited PICTURE clauses (floating currency symbols, zero suppression, CR/DB signs, BLANK WHEN ZERO), STRING/UNSTRING delimiter semantics, FUNCTION NUMVAL/TEST-NUMVAL parsing, and four different ROUNDED MODE behaviours plus DIVIDE...REMAINDER truncation quirks — genuine COBOL/mainframe-modernization domain expertise well beyond an undergraduate exercise.
✅ pass - interesting: Porting COBOL batch billing jobs to Python is a real, paid mainframe-modernization activity (utilities, banks); the task's own relevant_experience field names this profession directly, and the scenario (quarterly water billing job step) is realistic rather than a gimmick.
✅ pass - outcome_verified: Tests only compare final output bytes to the job step's own output; the 'Python 3, standard library only' constraint is an anti-cheat/technology constraint (enforced by restricting what programs the unprivileged runner can execute), not a procedural instruction about how to write the port.
✅ pass - anti_cheat_robustness: Ground-truth .stmt files and the GnuCOBOL compiler exist only in the verifier image (built and discarded in an earlier stage); the agent image never receives tests/ or solution/ (Dockerfile only COPYs app/, and .dockerignore also excludes tests/ and solution/). The verifier further locks the unprivileged runner to only the Python interpreter, preventing delegation to any other installed program.
✅ pass - task_security: All Dockerfiles and scripts perform only legitimate build/verify actions (apt installs of gnucobol3/tmux/asciinema, permission hardening, pytest execution); no exfiltration, obfuscation, or destructive operations were found.
✅ pass - functional_verification: test_outputs.py actually executes the submitted wbill.py as a subprocess on real input files and diffs the produced bytes against the oracle output; there is no string/keyword scanning of source.
✅ pass - deterministic_reproducible: Base images are pinned by sha256 digest, pytest/pytest-json-ctrf are version-pinned, all 53 test fixtures are static files (no runtime randomness), and no live external services are used; gnucobol3 is an unpinned apt package which is acceptable per guidance.
✅ pass - essential_difficulty: The hard part is genuine COBOL semantic reasoning (rounding modes, numeric editing, UNSTRING counting rules) rather than arbitrary formatting minutiae for its own sake — the exact byte format is dictated by the domain (COBOL PICTURE clauses), which is the core subject matter being tested.
✅ pass - test_instruction_alignment: Every edge-case category enumerated in instruction.md paragraph 2 (rejected records, meter rollover, credit balances, large commercial accounts, names of every shape, rounding boundaries, short/missing/misplaced headers, every posting kind/amount form/field count/account shape/memo length) has a corresponding named test case in tests/test_outputs.py, and no test introduces requirements outside that contract.
✅ pass - novel: WBILL.cbl is a bespoke, task-specific COBOL program with an invented billing domain; it cannot be solved by recalling a known public program or textbook algorithm.
✅ pass - agentic: Solving requires reading multiple source files (COBOL program, two copybooks, run notes, one sample), iteratively writing and testing a substantial Python program against limited ground truth, and reasoning about many interacting edge cases — well beyond a single zero-shot generation.
✅ pass - reviewable: The verifier derives expected outputs by actually compiling and running the disclosed COBOL source rather than hardcoding them, and the metadata explanations plus the disclosed sample/statement let a non-specialist reviewer sanity-check at least one case by hand, as verified in this audit.
✅ pass - instruction_concision: instruction.md is three short paragraphs, uses absolute paths (/app/legacy/WBILL.cbl, /app/port/wbill.py, /app/legacy/samples), states the goal and required edge-case coverage without prescribing implementation steps, and contains no fluff or headings.
✅ pass - solution_quality: solution/wbill.py performs genuine computation (decimal arithmetic, custom PICTURE-editing routine, UNSTRING/NUMVAL emulation) rather than echoing an answer, and solve.sh simply installs this one real file rather than inlining a large heredoc, matching the guidance to keep long files separate.
✅ pass - separate_verifier_configured: The only file the verifier reads from the agent is the declared artifact /app/port/wbill.py; all verifier tooling (gnucobol3, pytest, pytest-json-ctrf) is baked into tests/Dockerfile with no runtime installs in test.sh; and the WBILL.cbl/CUSTREC.cpy/TARIFFS.cpy/sample files duplicated between environment/app/legacy and tests/legacy+tests/samples were confirmed byte-identical.
✅ pass - environment_hygiene: environment/Dockerfile only COPYs app/ (no tests/ or solution/), installs no test-only dependencies, and cleans apt lists; tests/Dockerfile owns pytest/gnucobol3 and all /tests/* content with proper apt cleanup in both Dockerfiles.
✅ pass - structured_data_schema: The exact output byte format is normatively specified by the COBOL PICTURE clauses in WBILL.cbl (referenced directly by instruction.md) and the run notes in RUNBOOK.md describing line-sequential trimming rules — this is a precise formal specification, not merely illustrative examples.
✅ pass - typos: No typos were found in filenames, paths, commands, or identifiers across instruction.md, task.toml, Dockerfiles, test scripts, or the COBOL/Python sources reviewed.
✅ pass - difficulty_explanation_quality: difficulty_explanation names concrete COBOL semantic pitfalls (numeric-edited high-order truncation, STRING DELIMITED BY double space, UNSTRING COUNT IN semantics, NUMVAL CR/DB handling, per-statement ROUNDED MODE, DIVIDE...REMAINDER truncation) and states who does this work (mainframe-modernisation engineer), without citing pass rates.
✅ pass - solution_explanation_quality: solution_explanation accurately describes the approach actually implemented in solution/wbill.py (fixed-width/delimited parsing, exact-decimal arithmetic with per-field rounding rules, a unified numeric-edit formatting routine, line-sequential trailing-space trimming) and states it was fuzz-tested against the real GnuCOBOL build, congruent with the code.
✅ pass - verification_explanation_quality: verification_explanation precisely matches test_outputs.py/tests/Dockerfile: it describes the two-stage build separating the compiler from the final image, the 29 hand-written + 24 seeded-random cases, the unprivileged unidentifiable-path execution, and the sandboxing that limits the runner to the Python interpreter — all confirmed present in the actual files, with no unexplained tolerance/threshold to justify.
✅ pass - category_and_tags: category=Software/subcategory=Languages fits a COBOL-to-Python language port, and tags (cobol, legacy-migration, numeric-editing, fixed-point-arithmetic, gnucobol) are specific and directly descriptive of the task's skills.
✅ pass - no_extraneous_files: Every file present (instruction.md, task.toml, environment/*, solution/*, tests/* including 53 fixture pairs and duplicated legacy/samples for the verifier build) is referenced by a Dockerfile, the instruction, solve.sh, or the test harness; no cruft, backups, or unused assets were found.
✅ pass - verifier_execution_isolation: test.sh sets /logs/verifier to mode 700 and writes an initial reward before any agent code runs; test_outputs.py executes the submitted port via setpriv --reuid=65534 --regid=65534 --clear-groups --no-new-privs (dropping root), and root's test.sh derives the final reward from pytest's exit code after the run, so the executed agent code can neither discover nor write the reward channel.
✅ pass - ctrf_reporting: test.sh invokes the pinned pytest via '/opt/verifier-venv/bin/python -I -m pytest ... --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA', writing the required CTRF report directly since pytest itself runs as root throughout.
➖ not_applicable - do_not_modify_enforced: instruction.md contains no 'do not modify / preserve' constraint on any concrete artifact for the agent to violate; the port is meant to be written from scratch, so this criterion does not apply.
✅ pass - binary_reward: test.sh only ever writes 'echo 0' or 'echo 1' to /logs/verifier/reward.txt, derived directly from pytest's exit code with no weighted or fractional scoring path.

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
   1. [Sound Verifier] MAJOR: The capacity test contains 499 customers and a header, leaving a
      plausible 499-customer allocation bug undetected on permitted headerless 500-customer
      inputs.

Checked and clean: Coherent Contract, Correct Reference Solution, Protected Ground Truth,
  Deterministic Execution.

------------------------------------------------------------------------------------------------
DETAILS
------------------------------------------------------------------------------------------------

1. [Sound Verifier] MAJOR -- missing behavioral coverage
   The capacity test contains 499 customers and a header, leaving a plausible 499-customer
   allocation bug undetected on permitted headerless 500-customer inputs.
   Why this fails:
     Reach: Use an empty payments file and a headerless readings file containing 500 distinct,
     valid C records, with account identifiers 00000001 through 00000500. Each record has a
     blank 24-character name, tariff D, previous and current readings 000000, billing days 001,
     arrears +0000000, paid 0000000, and the normal filler. These inputs satisfy the 500-record
     limit and the runbook's numeric and charge limits. The COBOL main loop processes the first
     customer without requiring a header (lines 214–225). Each customer has zero usage, standing
     charge 0.31, VAT 0.02, and current charge and balance 0.33. It therefore bills 500
     customers and totals 165.00.
     Flip: Consider an otherwise faithful Python port that reserves 500 input slots but assumes
     one is the header, retaining only the first 499 customer records for processing. This
     ordinary fixed-capacity/off-by-one implementation produces exactly the correct bytes
     whenever there are at most 499 customers. Every fully shown readings fixture is below that
     threshold, and test_long_run explicitly asserts 500 total records but only 499 C records
     before invoking the same byte comparison. Its payments logic remains unchanged, so the
     500-payment test does not distinguish it. On the distinguishing headerless input it omits
     account 00000500, reports 499 billed, and totals 164.67 instead of 165.00. No shown graded
     invocation exercises that difference. The unshown fixtures cannot independently establish
     additional coverage. This construction arises naturally from assuming the normal header
     consumes one record, without needing knowledge of the verifier's comparison or parsing
     implementation.
   Where to look: instruction.md:3, tests/test_outputs.py:194-204,
     tests/cases/header_missing.dat:1-5, environment/app/legacy/WBILL.cbl:214-228,
     environment/app/legacy/WBILL.cbl:301-332
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
  - AutoEval execution succeeded. Build status: SUCCEEDED. Build ID: CodeExecutionEnvironment:17639d92-0371-49c4-ac21-28bae95c9546.

## 10. Evaluation Rubrics

### test_rubrics

```
Agent writes /app/port/wbill.py as a Python 3 standard-library program that takes the readings, payments and output paths as its three arguments and writes the statement file, +2
Agent formats every numeric-edited field as the picture defines it, including zero suppression, floating currency and sign, check protection, CR and trailing minus, BLANK WHEN ZERO and dropped high-order digits, +3
Agent reproduces the job step's floating-currency output when a value is too large for its field, as the production sample shows, +2
Agent applies each statement's rounding exactly: ROUNDED half away from zero, NEAREST-EVEN for payments, TOWARD-LESSER for refunds, truncation for the relief discount and fees, +3
Agent splits a fee with the part rounded and the remainder computed from the truncated quotient, +2
Agent parses payments lines as UNSTRING does, leaving fields from an earlier line in place when a line has fewer fields and checking the account length by characters examined, +3
Agent accepts, refuses and values amounts exactly as the program's NUMVAL functions do, including trailing CR and DB as negative, +2
Agent prints names cut at the first double space and uppercased, with the no-name text when nothing is left, +1
Agent handles rejected records, meter rollover, credit carry-forward, missing or misplaced headers and short lines as the program does, +2
Agent writes line sequential output with trailing spaces removed and one line feed per record, +1
Agent uses binary floating point for money amounts, -3
Agent runs a COBOL compiler or runtime instead of porting the program's logic, -5
Agent hardcodes statement text for particular input files, -5
Agent edits the legacy program, copybooks, run notes or sample files, -2
```

## 10b. Automated Feedback

| Field | Value |
|---|---|
| Eval revision notes | `Agent Runner Summary: Evaluation FAILED. Pre-difficulty quality or quality panel gate failed; difficulty not run` |
| Eval revision requested at | `2026-09-25T23:52:05.935694Z` |
| Rebuttal notes | `` |

### Evaluation History (oldest first)

| # | Created | Outcome | Blocking stage | Stages |
|---|---|---|---|---|
| 1 | `2026-09-24T15:49:34.919970Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |
| 2 | `2026-09-24T19:19:38.993860Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |
| 3 | `2026-09-25T03:09:45.820162Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |
| 4 | `2026-09-25T04:41:03.954925Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |
| 5 | `2026-09-25T05:16:02.350524Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |
| 6 | `2026-09-25T11:38:21.698570Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |
| 7 | `2026-09-25T11:53:55.051370Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |
| 8 | `2026-09-25T17:50:02.313189Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |
| 9 | `2026-09-25T23:02:58.210149Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |

## 11. Reviewer Decision

| Field | Value |
|---|---|
| Submission Review Decision | **—** |

### Revision Notes

_(none)_

---

_Generated by TB Task Revise Extractor from the Snorkel Experts task payload._
