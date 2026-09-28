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
| Expiry time | `2027-02-22T10:45:03.217778Z` |

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
| Uploaded at | `2026-09-25T05:13:39.455Z` |
| S3 URI | `s3://daas-blobs/prd/a34832f4-76f4-4d2a-aa62-c92deb15675d/2b0ac80a-32f9-4d2f-b66c-3b7bf235a842/9353db02-8890-4cf8-94fb-b5eaacb85392_submission_2026-09-25T05:13:37.410Z.zip` |
| S3 key | `prd/a34832f4-76f4-4d2a-aa62-c92deb15675d/2b0ac80a-32f9-4d2f-b66c-3b7bf235a842/9353db02-8890-4cf8-94fb-b5eaacb85392_submission_2026-09-25T05:13:37.410Z.zip` |

- **Difficulty-check artifact:** `s3://daas-blobs/codebuild_uploads/autoeval_artifacts/agent_runner/caa31ab9-2184-4a93-b007-efad3e2699ae/difficulty_check/ecede137bf2e/logs_artifact.zip`

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

QUALITY PANEL: NEEDS REVISION -- 5 blocking issues to fix. Details for each are below.

Blocking (fix every one):
   1. [Correct Reference Solution] MAJOR: The port's UNSTRING emulation records the full
      source-field length instead of the number of characters transferred into PL-ACCT, wrongly
      rejecting an over-width account field whose first eight characters identify an account.
   2. [Correct Reference Solution] MAJOR: The reference computes the ledger WHOLE field with
      ROUND_FLOOR instead of the COBOL FUNCTION INTEGER operation, so accepted negative
      fractional postings print a whole amount one lower than the job step prints.
   3. [Protected Ground Truth] MAJOR: The graded production-sample comparison reuses the
      complete input/output example disclosed to the candidate, allowing answer replay for that
      assertion.
   4. [Protected Ground Truth] MAJOR: The verifier exposes hidden scenario identities through
      argv and cwd, permitting a canned empty-run response selected by the empty_file label
      rather than input behavior.
   5. [Sound Verifier] MINOR: Coverage of the promised 500-record input range cannot be
      established from the visible scale test, leaving a smaller fixed processing cap as an
      unverified acceptance path.

Checked and clean: Coherent Contract, Deterministic Execution.

------------------------------------------------------------------------------------------------
DETAILS
------------------------------------------------------------------------------------------------

1. [Correct Reference Solution] MAJOR -- core domain and business logic
   The port's UNSTRING emulation records the full source-field length instead of the number of
   characters transferred into PL-ACCT, wrongly rejecting an over-width account field whose
   first eight characters identify an account.
   Why this fails:
     Reach: Use the sample readings containing account 10004821 and a payment line
     `10004821X;PAY;1.00;cash`. COBOL's eight-character PL-ACCT receives `10004821`; COUNT IN
     PL-ACCT-LEN is 8 characters transferred, so the payment passes the account-length check,
     finds that account, and posts 1.00. The reference likewise stores `10004821` in the
     eight-character field, but sets first_count to len(piece), which is 9. Flip: its BAD
     ACCOUNT check emits `LINE   1 REJECTED BAD ACCOUNT` instead of a PAY ledger entry and
     changes the posted and rejected totals.
   Where to look: environment/app/legacy/WBILL.cbl:418-445, solution/wbill.py:247-258,
     solution/wbill.py:269-290, instruction.md:1-3

2. [Correct Reference Solution] MAJOR -- core domain and business logic
   The reference computes the ledger WHOLE field with ROUND_FLOOR instead of the COBOL FUNCTION
   INTEGER operation, so accepted negative fractional postings print a whole amount one lower
   than the job step prints.
   Why this fails:
     Reach: use a valid readings file with a billed account 10000001 (for example a first H
     record followed by a valid 64+ byte C10000001...D...090+00000000000000 record), and payment
     line `10000001;ADJ;-1.20;x`. The amount syntax is contract-valid: optional leading `-`,
     then digits and decimal point. COBOL accepts ADJ, rounds -1.20 to cents unchanged, adds it
     to the account, then executes `COMPUTE WS-WHOLE = FUNCTION INTEGER(WS-AMT)`; under the
     required GnuCOBOL, INTEGER(-1.20) is -1 (the least integer not less than its argument).
     Flip: the reference reaches its ADJ branch with amt Decimal('-1.20'), but line 313 applies
     ROUND_FLOOR and sets whole to Decimal('-2'), so its emitted ADJ ledger record contains
     `WHOLE     -2` instead of the required `WHOLE     -1`. The output bytes therefore differ on
     a reachable, accepted input.
   Where to look: environment/app/legacy/RUNBOOK.md:8-13,
     environment/app/legacy/RUNBOOK.md:34-38, environment/app/legacy/WBILL.cbl:455-489,
     solution/wbill.py:297-321

3. [Protected Ground Truth] MAJOR
   The graded production-sample comparison reuses the complete input/output example disclosed to
   the candidate, allowing answer replay for that assertion.
   Why this fails:
     Reach: test_supplied_production_sample invokes the port on 2025q1-north.dat and
     2025q1-north.pay and compares its output with the verifier's 2025q1-north.stmt. These are
     the same production example supplied through environment/app/legacy/samples and explicitly
     disclosed by instruction.md. The candidate can embed the visible statement bytes in
     /app/port/wbill.py, together with a recognition check for the visible input pair; no
     additional transferred artifact is necessary. Flip: on that pair, write the embedded
     statement to argv[3] rather than calculate bills and postings. The regular-file read
     succeeds, and compare(got, fh.read()) at lines 376–377 accepts the replay, including the
     disclosed totals of 18 billed accounts, 2 rejected accounts, 2 credits, and 10 posted
     payments. Other pairs can use the ordinary implementation, so their independent comparisons
     do not invalidate this shortcut. The build-time COBOL comparison verifies that the public
     answer is accurate, not that the candidate independently computed it. The failed
     lookup-only execution experiment does not test this localized construction.
   Where to look: instruction.md:1, environment/Dockerfile:5-6,
     environment/app/legacy/samples/2025q1-north.stmt:153-171, tests/test_outputs.py:370-377,
     tests/Dockerfile:14-16, task.toml:1

4. [Protected Ground Truth] MAJOR
   The verifier exposes hidden scenario identities through argv and cwd, permitting a canned
   empty-run response selected by the empty_file label rather than input behavior.
   Why this fails:
     Reach: test_empty_file calls check('empty_file'); _run_port passes that name as tag. The
     submitted program receives paths ending in empty_file.readings, empty_file-postings.txt,
     and STMT.empty_file and runs in cwd-empty_file. Both supplied empty_file case files are
     empty. Thus the candidate learns the meaningful scenario label directly at execution,
     without reading /tests. Flip: a submission can retain its billing implementation for other
     scenarios but fail on empty input unless the argv label is empty_file. For that label it
     writes a precomputed constant statement: zero billed/rejected/credit counts, zero units and
     monetary totals, the PAYMENTS AND ADJUSTMENTS heading, and zero posting totals. The
     candidate-visible COBOL declarations give the exact field widths, while WRITE-TOTALS and
     POST-PAYMENTS specify the complete empty-run output, so this constant needs no hidden
     answer access or general billing implementation. The verifier reads those regular-file
     bytes and accepts them through check -> compare against empty_file.stmt. The same
     submission remains wrong for an ordinary empty input pair under different filenames. No
     shown test reruns this empty pair under a neutral label. The failed experiment used only
     the canned stub, rather than retaining behavior for the other cases, and therefore does not
     rebut this construction.
   Where to look: tests/test_outputs.py:48-68, tests/test_outputs.py:95-114,
     tests/test_outputs.py:174-175, environment/app/legacy/WBILL.cbl:183-211,
     environment/app/legacy/WBILL.cbl:377-411

5. [Sound Verifier] MINOR -- missing or degenerate behavioral coverage
   Coverage of the promised 500-record input range cannot be established from the visible scale
   test, leaving a smaller fixed processing cap as an unverified acceptance path.
   Why this fails:
     Reach: unverified — test_long_run invokes check('long_run'), but long_run.dat and
     long_run.pay are explicitly NOT SHOWN. No displayed cardinality assertion establishes their
     size; the corpus consistency assertion checks filenames, not record counts. A cheap
     distinguishing legal input is 101 copies of a valid zero-usage, 90-day domestic customer
     record, without a header, with an empty payments file. The COBOL loop processes all 101 and
     prints ACCOUNTS BILLED with count 101. A plausible otherwise-correct streaming port that
     stops after 100 readings instead prints 100 and omits one statement. Flip: that port would
     pass every displayed fixture's reading cardinality and retain the correct output on those
     fixtures, while failing the distinguishing input. Whether it passes the entire grader is
     unresolved because long_run and other omitted fixture contents cannot be inspected. Thus
     Reviewer 1's construction is conditional, not proven, but no visible fixture or other
     exclusion rules it out. The byte comparison would reject it if an omitted case crosses its
     cap; if none does, the reward decision admits the violating port. This is reported only at
     Minor, with reachability explicitly unverified.
   Where to look: instruction.md:3, tests/test_outputs.py:117-120,
     tests/test_outputs.py:194-195, environment/app/legacy/WBILL.cbl:221-228,
     environment/app/legacy/WBILL.cbl:325-332
```

## 5. Quality Check Results

### Quality Check Summary

```
## Quality Check Results
✅ pass - verifiable: The verifier builds WBILL.cbl with a pinned GnuCOBOL 3.1.2 in a build stage, generates expected .stmt bytes deterministically, then runs the submitted Python port as a subprocess and does an exact byte comparison. No LLM-as-judge, no live services, no runtime installs at test.sh time (all deps baked into tests/Dockerfile). This is fully deterministic and programmatic.
✅ pass - solvable: solution/wbill.py is a complete ~360-line Python port that reimplements the COBOL numeric-edit formatting, decimal rounding modes, UNSTRING/STRING semantics, and posting logic. It is provided as a real, runnable artifact installed by solution/solve.sh, demonstrating the task is solvable by an expert within the stated 4-hour estimate given deep COBOL familiarity.
✅ pass - difficult: The task requires reproducing exact byte-for-byte COBOL numeric-edited PIC output (floating currency symbols, CR/sign handling, BLANK WHEN ZERO, truncation vs. ROUNDED with different modes per statement, DIVIDE...REMAINDER semantics, UNSTRING COUNT IN behavior, FUNCTION NUMVAL with CR/DB suffixes) without a compiler present. This requires genuine COBOL/mainframe-modernization expertise beyond typical undergraduate coursework.
✅ pass - interesting: COBOL-to-modern-language ports of legacy billing/batch jobs are a well-known, real paid activity (mainframe modernization consulting). The scenario (a water utility's quarterly billing job) is a realistic proxy for genuine legacy migration work.
✅ pass - outcome_verified: Instruction only specifies the end state (write byte-identical STMTOUT given CUSTIN/PAYIN, run as `python3 /app/port/wbill.py <readings> <payments> <output>`); it does not prescribe how to implement the port. Tests check output bytes, not implementation approach.
✅ pass - anti_cheat_robustness: Ground-truth statement files and the COBOL source needed to regenerate them exist only in the verifier image (tests/Dockerfile build stage compiles WBILL.cbl and produces /tests/expected); the agent's environment/Dockerfile never includes a COBOL compiler or the hidden test cases. The agent image only ships the stub port, legacy source, copybooks, and one sample pair — no answer keys.
✅ pass - task_security: No malicious code, exfiltration, obfuscation, or destructive operations found in any Dockerfile, test.sh, test_outputs.py, or solution files. All actions are scoped to the task's stated purpose.
✅ pass - functional_verification: Verification executes the submitted wbill.py as a subprocess against 53 hidden case pairs plus a production sample and compares actual output bytes to the COBOL-produced ground truth — not string/keyword matching against source code.
✅ pass - deterministic_reproducible: Base images are pinned by digest, GnuCOBOL version is checked with `cobc --version | grep 3.1.2`, pytest/plugin versions are pinned, and the whole pipeline (compile once at build time, compare bytes) is deterministic with no live-service dependency.
✅ pass - essential_difficulty: Difficulty stems from correctly reasoning about COBOL semantics (rounding modes, numeric editing, UNSTRING/STRING truncation rules) rather than arbitrary output formatting choices invented by the task author — the exact output format is dictated by the legacy program itself, which is a genuine domain-fidelity challenge, not clerical busywork.
✅ pass - test_instruction_alignment: The instruction states the port must reproduce STMTOUT bytes exactly for any accepted CUSTIN/PAYIN pair and lists the categories of edge cases (rejected records, meter rollover, credits, large commercial accounts, name shapes, rounding boundaries, short/missing/misplaced headers, posting kinds/forms/field counts/unknown accounts/memos) that will be run; test_outputs.py's case names map directly onto these categories, and RUNBOOK.md (referenced by instruction) supplies the exact input-format contract the tests exercise.
✅ pass - novel: This is a bespoke, custom COBOL program (WBILL) with idiosyncratic business rules (tariff bands, arrears, GnuCOBOL-specific numeric-edit corner cases) that would not appear verbatim in any training corpus; success requires exploring the specific program and RUNBOOK rather than recalling a known algorithm.
✅ pass - agentic: Solving requires iteratively exploring the COBOL source and copybooks, reasoning about numeric-edit and rounding semantics, writing a substantial Python program, and testing/debugging against the provided sample — this cannot be done in a single zero-shot generation with any reliability.
✅ pass - reviewable: Expected outputs are derived by actually compiling and running the real COBOL program with a pinned GnuCOBOL version rather than hand-crafted/hardcoded values, so a reviewer can regenerate and verify correctness independently; RUNBOOK.md and comments in solution/wbill.py explain rationale (e.g. the floating-insertion overflow behaviour) for non-specialist review.
✅ pass - instruction_concision: Instruction is two short paragraphs, uses absolute paths (/app/legacy/WBILL.cbl, /app/port/wbill.py, /app/legacy/samples), states the end goal upfront, and does not prescribe implementation steps or list unrelated tools. It reads as human-written and domain-grounded rather than templated/LLM-generated boilerplate.
✅ pass - solution_quality: solution/wbill.py performs genuine computation (decimal arithmetic with COBOL rounding semantics, a general numeric-edit formatter, UNSTRING/NUMVAL emulation) rather than echoing a hardcoded answer; per guidance, the large file is kept in solution/wbill.py rather than inlined as a heredoc in solve.sh, which itself is a concise 4-line installer.
✅ pass - separate_verifier_configured: All verifier inputs (cases/, legacy/, samples/, precompiled expected/) are baked into tests/Dockerfile via the legacy build stage and COPY statements; verifier tooling (pytest, pytest-json-ctrf) is preinstalled in a root-only venv, no runtime pip/apt installs occur in test.sh; duplicated legacy/copybook/sample assets in environment/ and tests/ were verified byte-identical.
✅ pass - environment_hygiene: environment/Dockerfile only COPYs app/ (stub port, legacy source, one sample, README) and installs tmux/asciinema/patch/ca-certificates with apt-get update + list cleanup; no test-only or solution-only dependencies are baked in, and tests/solution are not copied into the agent image. tests/Dockerfile owns all test-only tooling and does apt cleanup as well.
✅ pass - structured_data_schema: The expected output is not a generic structured format but an exact byte-for-byte reproduction of a fixed record layout; RUNBOOK.md and CUSTREC.cpy/TARIFFS.cpy/WBILL.cbl fully and normatively specify field widths/positions, and the sample .stmt file plus the legacy source constitute the canonical, derivable spec rather than mere illustrative examples.
✅ pass - typos: No typos found in filenames, paths, commands, or identifiers across instruction.md, Dockerfiles, test scripts, and solution files; environment/app/legacy files and tests/legacy files are verified byte-identical, and paths referenced in instruction.md correctly match actual file locations.
✅ pass - difficulty_explanation_quality: The difficulty_explanation is detailed and concrete, naming specific COBOL semantics (numeric-edited moves, floating-currency overflow, STRING/UNSTRING delimiter rules, NUMVAL CR/DB handling, per-statement ROUNDED modes, DIVIDE...REMAINDER) that make the port hard for both humans and agents, and names the real-world persona (mainframe-modernisation engineer) who would face this.
✅ pass - solution_explanation_quality: solution_explanation accurately summarizes the approach actually implemented in solution/wbill.py (fixed-width/UNSTRING-accurate parsing, exact-decimal arithmetic with per-statement rounding rules, a unified numeric-edit formatting routine, line-sequential output trimming) and is congruent with the code; it also documents the fuzzing validation process used to build confidence.
✅ pass - verification_explanation_quality: verification_explanation precisely and concretely describes the build-time compilation of the real COBOL program, the 53 hidden case pairs (29 targeted + 24 seeded-random) plus the production sample check, the unprivileged/isolated execution model, and the exact-byte comparison — all of which match tests/Dockerfile and tests/test_outputs.py exactly, with no unjustified tolerance/threshold logic requiring calibration.
✅ pass - category_and_tags: category="Software", subcategory="Languages" fits a COBOL-to-Python legacy migration task; tags (cobol, legacy-migration, numeric-editing, fixed-point-arithmetic, gnucobol) are specific and directly descriptive of the skills involved, not generic filler.
✅ pass - no_extraneous_files: Every file traced back to a purpose: environment/app/* is copied into the agent image and referenced by instruction/README, solution/* is used by solve.sh, tests/cases and tests/legacy/tests/samples are consumed by tests/Dockerfile and test_outputs.py, and environment/.dockerignore is a legitimate build hygiene file. No stray scratch, backup, or unused assets were found.
✅ pass - verifier_execution_isolation: test_outputs.py runs the agent's wbill.py via subprocess with setpriv --reuid=65534 --regid=65534 --clear-groups --no-new-privs (demoting from root), captures stdout/stderr via pipes with an explicit timeout and killpg cleanup of the process group, and reads output via O_NOFOLLOW + regular-file checks. The reward file is placed under /logs/verifier which is chmod 700 (root-only) before any agent code executes, and test.sh (running as root) derives the reward solely from pytest's exit code, never from anything the demoted subprocess could write to the reward path.
✅ pass - ctrf_reporting: test.sh invokes pytest with `--ctrf /logs/verifier/ctrf.json`, matching the required CTRF pattern and covering the ~55 discrete named test functions in test_outputs.py.
➖ not_applicable - do_not_modify_enforced: The instruction contains no 'do not modify/preserve' constraint on a concrete artifact; it only specifies what to write and where. The COBOL source and copybooks are reference material the agent is free to read but there's no explicit prohibition against editing them, and doing so would have no effect on verification since the verifier builds its own separately-baked copy.
✅ pass - binary_reward: test.sh writes exactly `0` or `1` to /logs/verifier/reward.txt based solely on the pytest exit code (0 for success, else 0/failure branch writes 0); there is no intermediate scoring, weighting, or partial-credit computation on any reachable path.

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
✅ pass - verifiable: The verifier builds WBILL.cbl with a pinned GnuCOBOL 3.1.2 in a build stage, generates expected .stmt bytes deterministically, then runs the submitted Python port as a subprocess and does an exact byte comparison. No LLM-as-judge, no live services, no runtime installs at test.sh time (all deps baked into tests/Dockerfile). This is fully deterministic and programmatic.
✅ pass - solvable: solution/wbill.py is a complete ~360-line Python port that reimplements the COBOL numeric-edit formatting, decimal rounding modes, UNSTRING/STRING semantics, and posting logic. It is provided as a real, runnable artifact installed by solution/solve.sh, demonstrating the task is solvable by an expert within the stated 4-hour estimate given deep COBOL familiarity.
✅ pass - difficult: The task requires reproducing exact byte-for-byte COBOL numeric-edited PIC output (floating currency symbols, CR/sign handling, BLANK WHEN ZERO, truncation vs. ROUNDED with different modes per statement, DIVIDE...REMAINDER semantics, UNSTRING COUNT IN behavior, FUNCTION NUMVAL with CR/DB suffixes) without a compiler present. This requires genuine COBOL/mainframe-modernization expertise beyond typical undergraduate coursework.
✅ pass - interesting: COBOL-to-modern-language ports of legacy billing/batch jobs are a well-known, real paid activity (mainframe modernization consulting). The scenario (a water utility's quarterly billing job) is a realistic proxy for genuine legacy migration work.
✅ pass - outcome_verified: Instruction only specifies the end state (write byte-identical STMTOUT given CUSTIN/PAYIN, run as `python3 /app/port/wbill.py <readings> <payments> <output>`); it does not prescribe how to implement the port. Tests check output bytes, not implementation approach.
✅ pass - anti_cheat_robustness: Ground-truth statement files and the COBOL source needed to regenerate them exist only in the verifier image (tests/Dockerfile build stage compiles WBILL.cbl and produces /tests/expected); the agent's environment/Dockerfile never includes a COBOL compiler or the hidden test cases. The agent image only ships the stub port, legacy source, copybooks, and one sample pair — no answer keys.
✅ pass - task_security: No malicious code, exfiltration, obfuscation, or destructive operations found in any Dockerfile, test.sh, test_outputs.py, or solution files. All actions are scoped to the task's stated purpose.
✅ pass - functional_verification: Verification executes the submitted wbill.py as a subprocess against 53 hidden case pairs plus a production sample and compares actual output bytes to the COBOL-produced ground truth — not string/keyword matching against source code.
✅ pass - deterministic_reproducible: Base images are pinned by digest, GnuCOBOL version is checked with `cobc --version | grep 3.1.2`, pytest/plugin versions are pinned, and the whole pipeline (compile once at build time, compare bytes) is deterministic with no live-service dependency.
✅ pass - essential_difficulty: Difficulty stems from correctly reasoning about COBOL semantics (rounding modes, numeric editing, UNSTRING/STRING truncation rules) rather than arbitrary output formatting choices invented by the task author — the exact output format is dictated by the legacy program itself, which is a genuine domain-fidelity challenge, not clerical busywork.
✅ pass - test_instruction_alignment: The instruction states the port must reproduce STMTOUT bytes exactly for any accepted CUSTIN/PAYIN pair and lists the categories of edge cases (rejected records, meter rollover, credits, large commercial accounts, name shapes, rounding boundaries, short/missing/misplaced headers, posting kinds/forms/field counts/unknown accounts/memos) that will be run; test_outputs.py's case names map directly onto these categories, and RUNBOOK.md (referenced by instruction) supplies the exact input-format contract the tests exercise.
✅ pass - novel: This is a bespoke, custom COBOL program (WBILL) with idiosyncratic business rules (tariff bands, arrears, GnuCOBOL-specific numeric-edit corner cases) that would not appear verbatim in any training corpus; success requires exploring the specific program and RUNBOOK rather than recalling a known algorithm.
✅ pass - agentic: Solving requires iteratively exploring the COBOL source and copybooks, reasoning about numeric-edit and rounding semantics, writing a substantial Python program, and testing/debugging against the provided sample — this cannot be done in a single zero-shot generation with any reliability.
✅ pass - reviewable: Expected outputs are derived by actually compiling and running the real COBOL program with a pinned GnuCOBOL version rather than hand-crafted/hardcoded values, so a reviewer can regenerate and verify correctness independently; RUNBOOK.md and comments in solution/wbill.py explain rationale (e.g. the floating-insertion overflow behaviour) for non-specialist review.
✅ pass - instruction_concision: Instruction is two short paragraphs, uses absolute paths (/app/legacy/WBILL.cbl, /app/port/wbill.py, /app/legacy/samples), states the end goal upfront, and does not prescribe implementation steps or list unrelated tools. It reads as human-written and domain-grounded rather than templated/LLM-generated boilerplate.
✅ pass - solution_quality: solution/wbill.py performs genuine computation (decimal arithmetic with COBOL rounding semantics, a general numeric-edit formatter, UNSTRING/NUMVAL emulation) rather than echoing a hardcoded answer; per guidance, the large file is kept in solution/wbill.py rather than inlined as a heredoc in solve.sh, which itself is a concise 4-line installer.
✅ pass - separate_verifier_configured: All verifier inputs (cases/, legacy/, samples/, precompiled expected/) are baked into tests/Dockerfile via the legacy build stage and COPY statements; verifier tooling (pytest, pytest-json-ctrf) is preinstalled in a root-only venv, no runtime pip/apt installs occur in test.sh; duplicated legacy/copybook/sample assets in environment/ and tests/ were verified byte-identical.
✅ pass - environment_hygiene: environment/Dockerfile only COPYs app/ (stub port, legacy source, one sample, README) and installs tmux/asciinema/patch/ca-certificates with apt-get update + list cleanup; no test-only or solution-only dependencies are baked in, and tests/solution are not copied into the agent image. tests/Dockerfile owns all test-only tooling and does apt cleanup as well.
✅ pass - structured_data_schema: The expected output is not a generic structured format but an exact byte-for-byte reproduction of a fixed record layout; RUNBOOK.md and CUSTREC.cpy/TARIFFS.cpy/WBILL.cbl fully and normatively specify field widths/positions, and the sample .stmt file plus the legacy source constitute the canonical, derivable spec rather than mere illustrative examples.
✅ pass - typos: No typos found in filenames, paths, commands, or identifiers across instruction.md, Dockerfiles, test scripts, and solution files; environment/app/legacy files and tests/legacy files are verified byte-identical, and paths referenced in instruction.md correctly match actual file locations.
✅ pass - difficulty_explanation_quality: The difficulty_explanation is detailed and concrete, naming specific COBOL semantics (numeric-edited moves, floating-currency overflow, STRING/UNSTRING delimiter rules, NUMVAL CR/DB handling, per-statement ROUNDED modes, DIVIDE...REMAINDER) that make the port hard for both humans and agents, and names the real-world persona (mainframe-modernisation engineer) who would face this.
✅ pass - solution_explanation_quality: solution_explanation accurately summarizes the approach actually implemented in solution/wbill.py (fixed-width/UNSTRING-accurate parsing, exact-decimal arithmetic with per-statement rounding rules, a unified numeric-edit formatting routine, line-sequential output trimming) and is congruent with the code; it also documents the fuzzing validation process used to build confidence.
✅ pass - verification_explanation_quality: verification_explanation precisely and concretely describes the build-time compilation of the real COBOL program, the 53 hidden case pairs (29 targeted + 24 seeded-random) plus the production sample check, the unprivileged/isolated execution model, and the exact-byte comparison — all of which match tests/Dockerfile and tests/test_outputs.py exactly, with no unjustified tolerance/threshold logic requiring calibration.
✅ pass - category_and_tags: category="Software", subcategory="Languages" fits a COBOL-to-Python legacy migration task; tags (cobol, legacy-migration, numeric-editing, fixed-point-arithmetic, gnucobol) are specific and directly descriptive of the skills involved, not generic filler.
✅ pass - no_extraneous_files: Every file traced back to a purpose: environment/app/* is copied into the agent image and referenced by instruction/README, solution/* is used by solve.sh, tests/cases and tests/legacy/tests/samples are consumed by tests/Dockerfile and test_outputs.py, and environment/.dockerignore is a legitimate build hygiene file. No stray scratch, backup, or unused assets were found.
✅ pass - verifier_execution_isolation: test_outputs.py runs the agent's wbill.py via subprocess with setpriv --reuid=65534 --regid=65534 --clear-groups --no-new-privs (demoting from root), captures stdout/stderr via pipes with an explicit timeout and killpg cleanup of the process group, and reads output via O_NOFOLLOW + regular-file checks. The reward file is placed under /logs/verifier which is chmod 700 (root-only) before any agent code executes, and test.sh (running as root) derives the reward solely from pytest's exit code, never from anything the demoted subprocess could write to the reward path.
✅ pass - ctrf_reporting: test.sh invokes pytest with `--ctrf /logs/verifier/ctrf.json`, matching the required CTRF pattern and covering the ~55 discrete named test functions in test_outputs.py.
➖ not_applicable - do_not_modify_enforced: The instruction contains no 'do not modify/preserve' constraint on a concrete artifact; it only specifies what to write and where. The COBOL source and copybooks are reference material the agent is free to read but there's no explicit prohibition against editing them, and doing so would have no effect on verification since the verifier builds its own separately-baked copy.
✅ pass - binary_reward: test.sh writes exactly `0` or `1` to /logs/verifier/reward.txt based solely on the pytest exit code (0 for success, else 0/failure branch writes 0); there is no intermediate scoring, weighting, or partial-credit computation on any reachable path.

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
QUALITY PANEL: NEEDS REVISION -- 5 blocking issues to fix. Details for each are below.

Blocking (fix every one):
   1. [Correct Reference Solution] MAJOR: The port's UNSTRING emulation records the full
      source-field length instead of the number of characters transferred into PL-ACCT, wrongly
      rejecting an over-width account field whose first eight characters identify an account.
   2. [Correct Reference Solution] MAJOR: The reference computes the ledger WHOLE field with
      ROUND_FLOOR instead of the COBOL FUNCTION INTEGER operation, so accepted negative
      fractional postings print a whole amount one lower than the job step prints.
   3. [Protected Ground Truth] MAJOR: The graded production-sample comparison reuses the
      complete input/output example disclosed to the candidate, allowing answer replay for that
      assertion.
   4. [Protected Ground Truth] MAJOR: The verifier exposes hidden scenario identities through
      argv and cwd, permitting a canned empty-run response selected by the empty_file label
      rather than input behavior.
   5. [Sound Verifier] MINOR: Coverage of the promised 500-record input range cannot be
      established from the visible scale test, leaving a smaller fixed processing cap as an
      unverified acceptance path.

Checked and clean: Coherent Contract, Deterministic Execution.

------------------------------------------------------------------------------------------------
DETAILS
------------------------------------------------------------------------------------------------

1. [Correct Reference Solution] MAJOR -- core domain and business logic
   The port's UNSTRING emulation records the full source-field length instead of the number of
   characters transferred into PL-ACCT, wrongly rejecting an over-width account field whose
   first eight characters identify an account.
   Why this fails:
     Reach: Use the sample readings containing account 10004821 and a payment line
     `10004821X;PAY;1.00;cash`. COBOL's eight-character PL-ACCT receives `10004821`; COUNT IN
     PL-ACCT-LEN is 8 characters transferred, so the payment passes the account-length check,
     finds that account, and posts 1.00. The reference likewise stores `10004821` in the
     eight-character field, but sets first_count to len(piece), which is 9. Flip: its BAD
     ACCOUNT check emits `LINE   1 REJECTED BAD ACCOUNT` instead of a PAY ledger entry and
     changes the posted and rejected totals.
   Where to look: environment/app/legacy/WBILL.cbl:418-445, solution/wbill.py:247-258,
     solution/wbill.py:269-290, instruction.md:1-3

2. [Correct Reference Solution] MAJOR -- core domain and business logic
   The reference computes the ledger WHOLE field with ROUND_FLOOR instead of the COBOL FUNCTION
   INTEGER operation, so accepted negative fractional postings print a whole amount one lower
   than the job step prints.
   Why this fails:
     Reach: use a valid readings file with a billed account 10000001 (for example a first H
     record followed by a valid 64+ byte C10000001...D...090+00000000000000 record), and payment
     line `10000001;ADJ;-1.20;x`. The amount syntax is contract-valid: optional leading `-`,
     then digits and decimal point. COBOL accepts ADJ, rounds -1.20 to cents unchanged, adds it
     to the account, then executes `COMPUTE WS-WHOLE = FUNCTION INTEGER(WS-AMT)`; under the
     required GnuCOBOL, INTEGER(-1.20) is -1 (the least integer not less than its argument).
     Flip: the reference reaches its ADJ branch with amt Decimal('-1.20'), but line 313 applies
     ROUND_FLOOR and sets whole to Decimal('-2'), so its emitted ADJ ledger record contains
     `WHOLE     -2` instead of the required `WHOLE     -1`. The output bytes therefore differ on
     a reachable, accepted input.
   Where to look: environment/app/legacy/RUNBOOK.md:8-13,
     environment/app/legacy/RUNBOOK.md:34-38, environment/app/legacy/WBILL.cbl:455-489,
     solution/wbill.py:297-321

3. [Protected Ground Truth] MAJOR
   The graded production-sample comparison reuses the complete input/output example disclosed to
   the candidate, allowing answer replay for that assertion.
   Why this fails:
     Reach: test_supplied_production_sample invokes the port on 2025q1-north.dat and
     2025q1-north.pay and compares its output with the verifier's 2025q1-north.stmt. These are
     the same production example supplied through environment/app/legacy/samples and explicitly
     disclosed by instruction.md. The candidate can embed the visible statement bytes in
     /app/port/wbill.py, together with a recognition check for the visible input pair; no
     additional transferred artifact is necessary. Flip: on that pair, write the embedded
     statement to argv[3] rather than calculate bills and postings. The regular-file read
     succeeds, and compare(got, fh.read()) at lines 376–377 accepts the replay, including the
     disclosed totals of 18 billed accounts, 2 rejected accounts, 2 credits, and 10 posted
     payments. Other pairs can use the ordinary implementation, so their independent comparisons
     do not invalidate this shortcut. The build-time COBOL comparison verifies that the public
     answer is accurate, not that the candidate independently computed it. The failed
     lookup-only execution experiment does not test this localized construction.
   Where to look: instruction.md:1, environment/Dockerfile:5-6,
     environment/app/legacy/samples/2025q1-north.stmt:153-171, tests/test_outputs.py:370-377,
     tests/Dockerfile:14-16, task.toml:1

4. [Protected Ground Truth] MAJOR
   The verifier exposes hidden scenario identities through argv and cwd, permitting a canned
   empty-run response selected by the empty_file label rather than input behavior.
   Why this fails:
     Reach: test_empty_file calls check('empty_file'); _run_port passes that name as tag. The
     submitted program receives paths ending in empty_file.readings, empty_file-postings.txt,
     and STMT.empty_file and runs in cwd-empty_file. Both supplied empty_file case files are
     empty. Thus the candidate learns the meaningful scenario label directly at execution,
     without reading /tests. Flip: a submission can retain its billing implementation for other
     scenarios but fail on empty input unless the argv label is empty_file. For that label it
     writes a precomputed constant statement: zero billed/rejected/credit counts, zero units and
     monetary totals, the PAYMENTS AND ADJUSTMENTS heading, and zero posting totals. The
     candidate-visible COBOL declarations give the exact field widths, while WRITE-TOTALS and
     POST-PAYMENTS specify the complete empty-run output, so this constant needs no hidden
     answer access or general billing implementation. The verifier reads those regular-file
     bytes and accepts them through check -> compare against empty_file.stmt. The same
     submission remains wrong for an ordinary empty input pair under different filenames. No
     shown test reruns this empty pair under a neutral label. The failed experiment used only
     the canned stub, rather than retaining behavior for the other cases, and therefore does not
     rebut this construction.
   Where to look: tests/test_outputs.py:48-68, tests/test_outputs.py:95-114,
     tests/test_outputs.py:174-175, environment/app/legacy/WBILL.cbl:183-211,
     environment/app/legacy/WBILL.cbl:377-411

5. [Sound Verifier] MINOR -- missing or degenerate behavioral coverage
   Coverage of the promised 500-record input range cannot be established from the visible scale
   test, leaving a smaller fixed processing cap as an unverified acceptance path.
   Why this fails:
     Reach: unverified — test_long_run invokes check('long_run'), but long_run.dat and
     long_run.pay are explicitly NOT SHOWN. No displayed cardinality assertion establishes their
     size; the corpus consistency assertion checks filenames, not record counts. A cheap
     distinguishing legal input is 101 copies of a valid zero-usage, 90-day domestic customer
     record, without a header, with an empty payments file. The COBOL loop processes all 101 and
     prints ACCOUNTS BILLED with count 101. A plausible otherwise-correct streaming port that
     stops after 100 readings instead prints 100 and omits one statement. Flip: that port would
     pass every displayed fixture's reading cardinality and retain the correct output on those
     fixtures, while failing the distinguishing input. Whether it passes the entire grader is
     unresolved because long_run and other omitted fixture contents cannot be inspected. Thus
     Reviewer 1's construction is conditional, not proven, but no visible fixture or other
     exclusion rules it out. The byte comparison would reject it if an omitted case crosses its
     cap; if none does, the reward decision admits the violating port. This is reported only at
     Minor, with reachability explicitly unverified.
   Where to look: instruction.md:3, tests/test_outputs.py:117-120,
     tests/test_outputs.py:194-195, environment/app/legacy/WBILL.cbl:221-228,
     environment/app/legacy/WBILL.cbl:325-332
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
  - AutoEval execution succeeded. Build status: SUCCEEDED. Build ID: CodeExecutionEnvironment:f737bc65-5ad9-402f-a467-c7d5680737ec.

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
| Eval revision requested at | `2026-09-25T10:45:03.217778Z` |
| Rebuttal notes | `` |

### Evaluation History (oldest first)

| # | Created | Outcome | Blocking stage | Stages |
|---|---|---|---|---|
| 1 | `2026-09-24T15:49:34.919970Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |
| 2 | `2026-09-24T19:19:38.993860Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |
| 3 | `2026-09-25T03:09:45.820162Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |
| 4 | `2026-09-25T04:41:03.954925Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |
| 5 | `2026-09-25T05:16:02.350524Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |

## 11. Reviewer Decision

| Field | Value |
|---|---|
| Submission Review Decision | **—** |

### Revision Notes

_(none)_

---

_Generated by TB Task Revise Extractor from the Snorkel Experts task payload._
