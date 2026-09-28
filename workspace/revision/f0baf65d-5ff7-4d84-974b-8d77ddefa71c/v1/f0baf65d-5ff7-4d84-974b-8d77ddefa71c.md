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
| Expiry time | `2027-02-24T16:11:35.568191Z` |

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
| Uploaded at | `2026-09-27T15:35:23.093Z` |
| S3 URI | `s3://daas-blobs/prd/a34832f4-76f4-4d2a-aa62-c92deb15675d/ffd1fe4e-1dea-4e6f-bc90-a6e99f468d9a/86dbf33c-b3c6-40b0-b98a-9b94c248f08f_submission_2026-09-27T15:35:21.640Z.zip` |
| S3 key | `prd/a34832f4-76f4-4d2a-aa62-c92deb15675d/ffd1fe4e-1dea-4e6f-bc90-a6e99f468d9a/86dbf33c-b3c6-40b0-b98a-9b94c248f08f_submission_2026-09-27T15:35:21.640Z.zip` |

- **Difficulty-check artifact:** `s3://daas-blobs/codebuild_uploads/autoeval_artifacts/agent_runner/89e4075a-ca96-4ace-82f0-2d3046c909f4/difficulty_check/ebb73a2f590f/logs_artifact.zip`

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

QUALITY PANEL: NEEDS REVISION -- 4 blocking issues to fix. Details for each are below.

Blocking (fix every one):
   1. [Sound Verifier] MAJOR: No graded file has an empty branch string, so an unauthorized
      guard rejecting that covered input passes the verifier.
   2. [Sound Verifier] MINOR: All billed fixture and generated branch names have the RC3 prefix,
      leaving a valid arbitrary branch-name class untested and permitting a branch-specific
      billing guard or transformation.
   3. [Sound Verifier] MINOR: The verifier does not enforce the source/artifact scoping
      requirement that only manual-governed material be changed.
   4. [Sound Verifier] MINOR: The harness always uses one staged filename, so it does not
      establish that the documented CLI works for an arbitrary AGREEMENTS.json pathname.

Checked and clean: Coherent Contract, Correct Reference Solution, Protected Ground Truth,
  Deterministic Execution.

------------------------------------------------------------------------------------------------
DETAILS
------------------------------------------------------------------------------------------------

1. [Sound Verifier] MAJOR -- missing behavioral coverage
   No graded file has an empty branch string, so an unauthorized guard rejecting that covered
   input passes the verifier.
   Why this fails:
     Reach: A one-agreement JSON file with branch "", id "A", out 2031-05-02T09:15, in
     2031-05-03T09:15, equal odometers, fuel_out=fuel_in=8, day_rate=100, mile_rate=0 and
     fuel_rate=0 is README-conforming and within rule 1.3. Its bill has days=1, time_charge=100,
     tax=8 and total=108, and the run must retain branch "". Flip: An otherwise correct bill_run
     that begins `if not agreements["branch"]: raise ValueError("branch required")` produces all
     expected values for the 13 roster families and the relabelled runs: their branch names are
     nonempty. Each call through check_family and compare therefore succeeds; the added guard
     instead rejects this covered file. The verifier's own within_limits check requires only
     that branch be a string.
   Where to look: environment/app/README.md:15-18, instruction.md:1-3,
     tests/test_outputs.py:157-169, tests/expected/ROSTER:1-13, tests/test_outputs.py:280-311

2. [Sound Verifier] MINOR -- missing behavioral coverage
   All billed fixture and generated branch names have the RC3 prefix, leaving a valid arbitrary
   branch-name class untested and permitting a branch-specific billing guard or transformation.
   Why this fails:
     Reach: every fixed family uses RC3-labelled branches, and relabel() constructs only "RC3-"
     plus eight characters. A candidate can otherwise implement RC-3 correctly but add `if
     agreements["branch"] == "X": return {"branch":"X","bills":[],"revenue":0,"tax":0}` in
     bill_run. Flip: it clears every check_family and relabelled comparison because none
     supplies branch X, yet the contract permits branch X as a string; a one-agreement
     otherwise-valid X file must retain its bill and branch and would fail. This construction
     depends on knowing the verifier's branch corpus, so it is Minor rather than a reachable
     ordinary implementation error.
   Where to look: tests/test_outputs.py:200-215, tests/test_outputs.py:280-311,
     environment/app/README.md:15-22

3. [Sound Verifier] MINOR -- missing behavioral coverage
   The verifier does not enforce the source/artifact scoping requirement that only
   manual-governed material be changed.
   Why this fails:
     Reach: a candidate can correctly repair the rentcharge package and also change an unrelated
     artifact, for example append `unrelated` to /app/README.md. Flip: all bill comparisons
     still succeed; the only submitted-artifact byte comparison is for tools/rentcharge_run.py,
     and the sealing code merely prevents later writes. The submission violates the explicit
     scope restriction but is accepted. This is a narrow process/artifact violation rather than
     a way to evade the billing calculation, so it is Minor.
   Where to look: contract/instruction.md:1-3, tests/test_outputs.py:81-93,
     tests/test_outputs.py:327-332

4. [Sound Verifier] MINOR -- missing behavioral coverage
   The harness always uses one staged filename, so it does not establish that the documented CLI
   works for an arbitrary AGREEMENTS.json pathname.
   Why this fails:
     Reach: bill_run() always creates `stage/agreements.json` and invokes the driver with
     exactly that path. A candidate package can otherwise compute every bill correctly but
     inspect `sys.argv[1]` during import and deliberately fail or substitute output unless its
     basename is `agreements.json`. Flip: all graded invocations retain that basename and pass,
     while `python3 /app/tools/rentcharge_run.py /tmp/customer-file.json` is a contract-legal
     documented invocation that fails. This needs verifier-specific knowledge and is therefore
     Minor.
   Where to look: tests/test_outputs.py:132-149, environment/app/README.md:6-11
```

## 5. Quality Check Results

### Quality Check Summary

```
## Quality Check Results
✅ pass - verifiable: test_outputs.py runs the delivered driver via subprocess with fixed inputs and compares exact JSON keys against expectations sealed by an independent model (solution/model.py). All comparisons are exact equality (type and value), no LLM-as-judge, no network calls, and the harness (test.sh) derives a deterministic 0/1 reward from the pytest exit code plus a byte-comparison. No runtime installs of verifier tooling occur in test.sh (pytest/ctrf are baked into tests/Dockerfile).
✅ pass - solvable: solution/fix.patch (applied by solution/solve.sh via `patch -p1`) makes exactly the four targeted, small edits (grace-period day count, 150-mile allowance + odometer turnover, refuelling fee, tax base/rounding) that the reference model in solution/model.py encodes. Hand-checking several expected rows (e.g. 01-grace.jsonl, 06-tax_rounding.jsonl) against the manual confirms the patch reproduces them, and the fix is a few dozen lines — clearly achievable by an expert in a few hours, consistent with the stated expert_time_estimate_hours=2.
✅ pass - difficult: The task requires precisely scoping a fix to a multi-rule specification: fixing five interacting bugs (grace period, mileage allowance, odometer turnover, refuelling fee, tax base/rounding) while deliberately NOT 'fixing' two areas the manual leaves silent (sub-day rentals, fuller-than-out returns), where the natural/'obvious' correction is explicitly wrong. This is a genuine spec-compliance/scope-discipline challenge with subtle boundary conditions (59-minute grace, floor vs ceiling day counts, negative fuel credits) that a naive fix or ordinary fuzz-testing would not catch, evidenced by the described 22 one-edit mutants each targeting a plausible over/under-correction.
✅ pass - interesting: Fixing rental/billing software to match a written charges policy exactly (while not overreaching into undefined behavior) is realistic professional work for billing/finance-ops engineers and analysts at car-rental or similarly billed-by-usage businesses; the relevant_experience field in task.toml plausibly describes this real occupation.
✅ pass - outcome_verified: Verification runs the documented CLI command against the agent's own /app/src and checks only the JSON output values (branch, bills[*] keys, revenue, tax) — never inspecting how the fix was implemented. The instruction states end goals ('follows it', 'each rule holds ... within the limits') and restricts scope conceptually, but does not mandate any particular implementation technique, and tests never grep source code.
✅ pass - anti_cheat_robustness: Ground truth (model.py, jobgen.py, tests/expected/*, ROSTER) lives only in the verifier image (tests/), which environment/.dockerignore explicitly excludes from the agent build context. The verifier overwrites /app/tools/rentcharge_run.py with its own copy, seals /app root-owned, and test_candidate_cannot_read_verifier_state explicitly asserts the candidate's unprivileged user cannot read /tests, ROSTER, the shipped copy, or /logs/verifier, with a positive control proving the probe itself works.
✅ pass - task_security: No exfiltration, obfuscation, destructive commands, or prompt injection found in environment/Dockerfile, tests/Dockerfile, instruction.md, or any script. All privileged operations (chown/chmod, setpriv-drop) are narrowly scoped to enforcing the sandbox and are legitimate to the task's anti-cheat design.
✅ pass - functional_verification: Tests execute the actual driver (python3 /app/tools/rentcharge_run.py) as a subprocess for every agreement file and parse/compare its JSON stdout; there is no source-code keyword or string-pattern scanning anywhere in test_outputs.py.
✅ pass - deterministic_reproducible: Base image is pinned by digest sha256 in both Dockerfiles; pytest/pytest-json-ctrf are version-pinned; expected fixtures are generated with a fixed random seed (SEED=20260928) and pinned via SHA-256/row-count in ROSTER. The one randomized element (RELABEL_SEED from os.urandom) only reshuffles labels/order for the 'generated' family via a transformation whose expected output is recomputed consistently for any seed, so correctness does not depend on the draw and no flakiness is introduced.
✅ pass - essential_difficulty: Comparisons use exact integer equality on a small, well-defined set of README-documented keys with generous 'set(actual) >= {...}' superset checks (extra keys ignored), so failures stem from genuine business-rule/arithmetic errors (wrong day-grace logic, wrong allowance, missed turnover, missed fee, wrong tax base/rounding) rather than formatting or precision minutiae.
✅ pass - test_instruction_alignment: Each manual rule referenced by the instruction (grace days 2.3, allowance 3.2, turnover 2.4, refuelling fee 3.3, tax base 4.1, tax rounding 1.2, bill order/totals) has a corresponding named test family, and the 'do not add unrequested clamps/guards' constraint from the instruction is exercised by the short_days/short_allowance/fuel_not_short/traps_combined families. No test checks behavior the instruction does not implicate (the anti-cheat and driver-preservation tests derive from the instruction's explicit 'leave that driver exactly as it is' requirement).
✅ pass - novel: The scenario (a fictional 'Rental Charges Manual RC-3' and a bespoke rentcharge package) is custom-built for this task; there is no widely available reference solution to memorize, and correct behavior requires reading and correctly scoping the invented manual's specific rules.
✅ pass - agentic: Solving requires exploring multiple files (manual, README, several source modules), iteratively editing and testing the package, and reasoning about which of several interacting figures the manual governs — this is not a single-shot generation task.
✅ pass - reviewable: The manual, package, and solution/model.py are self-contained and short; a non-specialist reviewer can directly compare the manual's rules 1-4 against model.py's implementation and the fix.patch diff without needing real car-rental domain expertise, and expected values are derived from a documented independent model rather than hardcoded.
✅ pass - instruction_concision: instruction.md is five short paragraphs, uses absolute paths and backticks throughout, has no headings/roleplay/tool-listing, states the end goal (bills must follow the manual) and necessary hard constraints (driver must be byte-identical) without prescribing an implementation approach.
✅ pass - solution_quality: solve.sh applies solution/fix.patch, a genuine multi-file source diff implementing the manual's rules (not an echoed/hardcoded answer); the patch is kept as its own file rather than inlined as a heredoc, consistent with guidance for larger changes.
✅ pass - separate_verifier_configured: All verifier inputs are either the /app artifact or files baked into tests/ (expected/, shipped/); tests/Dockerfile pre-installs pytest and pytest-json-ctrf, and test.sh performs no runtime installs. The duplicated package/driver sources in tests/shipped/app were verified byte-identical to environment/app's originals for every file (mileage.py, fuel.py, tax.py, time_charge.py, run.py, clock.py, __init__.py, rentcharge_run.py).
✅ pass - environment_hygiene: environment/.dockerignore excludes tests/ and solution/ from the agent image build context, and environment/Dockerfile only COPYs app/; apt packages (tmux, asciinema, patch, git, ca-certificates) are unpinned with `apt-get update` and `rm -rf /var/lib/apt/lists/*` cleanup, appropriately. tests/Dockerfile installs only pinned pytest/ctrf and creates artifact directories, with no apt usage.
✅ pass - structured_data_schema: The exact output schema (branch, bills[] with id/days/miles/time_charge/mileage_charge/fuel_charge/tax/total, revenue, tax, all integers) is normatively documented in environment/app/README.md, which is present in the agent's filesystem and referenced by the instruction's 'Every key the README lists is compared exactly' sentence.
✅ pass - typos: No typos found in filenames, paths, commands, or identifiers across the reviewed files; 'refuelling' is a consistent, intentional British spelling used throughout, not a typo.
✅ pass - difficulty_explanation_quality: The explanation identifies the concrete real-world role (rental-billing analyst), the specific bugs, and — critically — explains why the task is hard for both humans and models (knowing exactly where the manual's authority stops, and that natural 'improvements' like flooring the fuel credit are wrong but would evade naive fuzz-testing). It also discloses the data is synthetic and purpose-built to sit on rule limits.
✅ pass - solution_explanation_quality: The explanation concisely summarizes the four fixed areas and the rationale for leaving 'today's step' unchanged where the manual is silent, and is fully congruent with fix.patch and model.py.
✅ pass - verification_explanation_quality: The explanation accurately describes the isolation model (unprivileged execution, sealed /app, staged files), the exact-match comparison strategy, the SHA-256/row-count pinning via ROSTER, the 15 tests over 13 families, and the anti-cheat read-access test — all verified consistent with test_outputs.py's actual contents; no inequality/tolerance-based checks are used that would need separate calibration justification.
✅ pass - category_and_tags: category='Operations', subcategory='Finance' fit the billing/business-rule-compliance nature of the task well; tags (car-rental, billing, rental-agreements, sales-tax, revenue-operations) are specific and descriptive rather than generic.
✅ pass - no_extraneous_files: Every file present is referenced: environment/app/* is copied by environment/Dockerfile and referenced by README/instructions; solution/{model.py, jobgen.py, seal.py} generate tests/expected/ and tests/shipped (used by solve.sh's dependency chain and for provenance); fix.patch/solve.sh are the solution entrypoint; tests/* are the verifier's own files. No leftover or unused files were found.
✅ pass - verifier_execution_isolation: The verifier drops privileges via `setpriv --reuid=<uid> --regid=<uid> --clear-groups --no-new-privs` to run the candidate driver as an unprivileged, isolated user (CANDIDATE_UID=65534) in its own session, with the child's stdout/stderr captured via pipes to a Popen.communicate() call and the process group killed afterward; /logs/verifier and /tests are chmod 700 (root-only) in test.sh before pytest (running as root) executes any candidate code; the reward is derived by root from the pytest exit code, never by the executed candidate code.
✅ pass - ctrf_reporting: test.sh invokes `python3 -I -m pytest ... --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA`, writing a per-test CTRF report directly to the collected path, consistent with the recommended pattern.
✅ pass - do_not_modify_enforced: The instruction's 'leave that driver exactly as it is ... byte for byte' constraint on /app/tools/rentcharge_run.py is directly enforced: test_submitted_driver_unchanged compares the driver's bytes as delivered (captured before the verifier's own overwrite) against the pristine shipped copy, failing any agent that modifies, deletes, or replaces the file.
✅ pass - binary_reward: test.sh only ever writes the literal characters `0` or `1` to /logs/verifier/reward.txt on every code path (initial default, working-directory guard, and the final rc/cmp-based branch); no fractional or computed score is ever written.

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
✅ pass - verifiable: test_outputs.py runs the delivered driver via subprocess with fixed inputs and compares exact JSON keys against expectations sealed by an independent model (solution/model.py). All comparisons are exact equality (type and value), no LLM-as-judge, no network calls, and the harness (test.sh) derives a deterministic 0/1 reward from the pytest exit code plus a byte-comparison. No runtime installs of verifier tooling occur in test.sh (pytest/ctrf are baked into tests/Dockerfile).
✅ pass - solvable: solution/fix.patch (applied by solution/solve.sh via `patch -p1`) makes exactly the four targeted, small edits (grace-period day count, 150-mile allowance + odometer turnover, refuelling fee, tax base/rounding) that the reference model in solution/model.py encodes. Hand-checking several expected rows (e.g. 01-grace.jsonl, 06-tax_rounding.jsonl) against the manual confirms the patch reproduces them, and the fix is a few dozen lines — clearly achievable by an expert in a few hours, consistent with the stated expert_time_estimate_hours=2.
✅ pass - difficult: The task requires precisely scoping a fix to a multi-rule specification: fixing five interacting bugs (grace period, mileage allowance, odometer turnover, refuelling fee, tax base/rounding) while deliberately NOT 'fixing' two areas the manual leaves silent (sub-day rentals, fuller-than-out returns), where the natural/'obvious' correction is explicitly wrong. This is a genuine spec-compliance/scope-discipline challenge with subtle boundary conditions (59-minute grace, floor vs ceiling day counts, negative fuel credits) that a naive fix or ordinary fuzz-testing would not catch, evidenced by the described 22 one-edit mutants each targeting a plausible over/under-correction.
✅ pass - interesting: Fixing rental/billing software to match a written charges policy exactly (while not overreaching into undefined behavior) is realistic professional work for billing/finance-ops engineers and analysts at car-rental or similarly billed-by-usage businesses; the relevant_experience field in task.toml plausibly describes this real occupation.
✅ pass - outcome_verified: Verification runs the documented CLI command against the agent's own /app/src and checks only the JSON output values (branch, bills[*] keys, revenue, tax) — never inspecting how the fix was implemented. The instruction states end goals ('follows it', 'each rule holds ... within the limits') and restricts scope conceptually, but does not mandate any particular implementation technique, and tests never grep source code.
✅ pass - anti_cheat_robustness: Ground truth (model.py, jobgen.py, tests/expected/*, ROSTER) lives only in the verifier image (tests/), which environment/.dockerignore explicitly excludes from the agent build context. The verifier overwrites /app/tools/rentcharge_run.py with its own copy, seals /app root-owned, and test_candidate_cannot_read_verifier_state explicitly asserts the candidate's unprivileged user cannot read /tests, ROSTER, the shipped copy, or /logs/verifier, with a positive control proving the probe itself works.
✅ pass - task_security: No exfiltration, obfuscation, destructive commands, or prompt injection found in environment/Dockerfile, tests/Dockerfile, instruction.md, or any script. All privileged operations (chown/chmod, setpriv-drop) are narrowly scoped to enforcing the sandbox and are legitimate to the task's anti-cheat design.
✅ pass - functional_verification: Tests execute the actual driver (python3 /app/tools/rentcharge_run.py) as a subprocess for every agreement file and parse/compare its JSON stdout; there is no source-code keyword or string-pattern scanning anywhere in test_outputs.py.
✅ pass - deterministic_reproducible: Base image is pinned by digest sha256 in both Dockerfiles; pytest/pytest-json-ctrf are version-pinned; expected fixtures are generated with a fixed random seed (SEED=20260928) and pinned via SHA-256/row-count in ROSTER. The one randomized element (RELABEL_SEED from os.urandom) only reshuffles labels/order for the 'generated' family via a transformation whose expected output is recomputed consistently for any seed, so correctness does not depend on the draw and no flakiness is introduced.
✅ pass - essential_difficulty: Comparisons use exact integer equality on a small, well-defined set of README-documented keys with generous 'set(actual) >= {...}' superset checks (extra keys ignored), so failures stem from genuine business-rule/arithmetic errors (wrong day-grace logic, wrong allowance, missed turnover, missed fee, wrong tax base/rounding) rather than formatting or precision minutiae.
✅ pass - test_instruction_alignment: Each manual rule referenced by the instruction (grace days 2.3, allowance 3.2, turnover 2.4, refuelling fee 3.3, tax base 4.1, tax rounding 1.2, bill order/totals) has a corresponding named test family, and the 'do not add unrequested clamps/guards' constraint from the instruction is exercised by the short_days/short_allowance/fuel_not_short/traps_combined families. No test checks behavior the instruction does not implicate (the anti-cheat and driver-preservation tests derive from the instruction's explicit 'leave that driver exactly as it is' requirement).
✅ pass - novel: The scenario (a fictional 'Rental Charges Manual RC-3' and a bespoke rentcharge package) is custom-built for this task; there is no widely available reference solution to memorize, and correct behavior requires reading and correctly scoping the invented manual's specific rules.
✅ pass - agentic: Solving requires exploring multiple files (manual, README, several source modules), iteratively editing and testing the package, and reasoning about which of several interacting figures the manual governs — this is not a single-shot generation task.
✅ pass - reviewable: The manual, package, and solution/model.py are self-contained and short; a non-specialist reviewer can directly compare the manual's rules 1-4 against model.py's implementation and the fix.patch diff without needing real car-rental domain expertise, and expected values are derived from a documented independent model rather than hardcoded.
✅ pass - instruction_concision: instruction.md is five short paragraphs, uses absolute paths and backticks throughout, has no headings/roleplay/tool-listing, states the end goal (bills must follow the manual) and necessary hard constraints (driver must be byte-identical) without prescribing an implementation approach.
✅ pass - solution_quality: solve.sh applies solution/fix.patch, a genuine multi-file source diff implementing the manual's rules (not an echoed/hardcoded answer); the patch is kept as its own file rather than inlined as a heredoc, consistent with guidance for larger changes.
✅ pass - separate_verifier_configured: All verifier inputs are either the /app artifact or files baked into tests/ (expected/, shipped/); tests/Dockerfile pre-installs pytest and pytest-json-ctrf, and test.sh performs no runtime installs. The duplicated package/driver sources in tests/shipped/app were verified byte-identical to environment/app's originals for every file (mileage.py, fuel.py, tax.py, time_charge.py, run.py, clock.py, __init__.py, rentcharge_run.py).
✅ pass - environment_hygiene: environment/.dockerignore excludes tests/ and solution/ from the agent image build context, and environment/Dockerfile only COPYs app/; apt packages (tmux, asciinema, patch, git, ca-certificates) are unpinned with `apt-get update` and `rm -rf /var/lib/apt/lists/*` cleanup, appropriately. tests/Dockerfile installs only pinned pytest/ctrf and creates artifact directories, with no apt usage.
✅ pass - structured_data_schema: The exact output schema (branch, bills[] with id/days/miles/time_charge/mileage_charge/fuel_charge/tax/total, revenue, tax, all integers) is normatively documented in environment/app/README.md, which is present in the agent's filesystem and referenced by the instruction's 'Every key the README lists is compared exactly' sentence.
✅ pass - typos: No typos found in filenames, paths, commands, or identifiers across the reviewed files; 'refuelling' is a consistent, intentional British spelling used throughout, not a typo.
✅ pass - difficulty_explanation_quality: The explanation identifies the concrete real-world role (rental-billing analyst), the specific bugs, and — critically — explains why the task is hard for both humans and models (knowing exactly where the manual's authority stops, and that natural 'improvements' like flooring the fuel credit are wrong but would evade naive fuzz-testing). It also discloses the data is synthetic and purpose-built to sit on rule limits.
✅ pass - solution_explanation_quality: The explanation concisely summarizes the four fixed areas and the rationale for leaving 'today's step' unchanged where the manual is silent, and is fully congruent with fix.patch and model.py.
✅ pass - verification_explanation_quality: The explanation accurately describes the isolation model (unprivileged execution, sealed /app, staged files), the exact-match comparison strategy, the SHA-256/row-count pinning via ROSTER, the 15 tests over 13 families, and the anti-cheat read-access test — all verified consistent with test_outputs.py's actual contents; no inequality/tolerance-based checks are used that would need separate calibration justification.
✅ pass - category_and_tags: category='Operations', subcategory='Finance' fit the billing/business-rule-compliance nature of the task well; tags (car-rental, billing, rental-agreements, sales-tax, revenue-operations) are specific and descriptive rather than generic.
✅ pass - no_extraneous_files: Every file present is referenced: environment/app/* is copied by environment/Dockerfile and referenced by README/instructions; solution/{model.py, jobgen.py, seal.py} generate tests/expected/ and tests/shipped (used by solve.sh's dependency chain and for provenance); fix.patch/solve.sh are the solution entrypoint; tests/* are the verifier's own files. No leftover or unused files were found.
✅ pass - verifier_execution_isolation: The verifier drops privileges via `setpriv --reuid=<uid> --regid=<uid> --clear-groups --no-new-privs` to run the candidate driver as an unprivileged, isolated user (CANDIDATE_UID=65534) in its own session, with the child's stdout/stderr captured via pipes to a Popen.communicate() call and the process group killed afterward; /logs/verifier and /tests are chmod 700 (root-only) in test.sh before pytest (running as root) executes any candidate code; the reward is derived by root from the pytest exit code, never by the executed candidate code.
✅ pass - ctrf_reporting: test.sh invokes `python3 -I -m pytest ... --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA`, writing a per-test CTRF report directly to the collected path, consistent with the recommended pattern.
✅ pass - do_not_modify_enforced: The instruction's 'leave that driver exactly as it is ... byte for byte' constraint on /app/tools/rentcharge_run.py is directly enforced: test_submitted_driver_unchanged compares the driver's bytes as delivered (captured before the verifier's own overwrite) against the pristine shipped copy, failing any agent that modifies, deletes, or replaces the file.
✅ pass - binary_reward: test.sh only ever writes the literal characters `0` or `1` to /logs/verifier/reward.txt on every code path (initial default, working-directory guard, and the final rc/cmp-based branch); no fractional or computed score is ever written.

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
QUALITY PANEL: NEEDS REVISION -- 4 blocking issues to fix. Details for each are below.

Blocking (fix every one):
   1. [Sound Verifier] MAJOR: No graded file has an empty branch string, so an unauthorized
      guard rejecting that covered input passes the verifier.
   2. [Sound Verifier] MINOR: All billed fixture and generated branch names have the RC3 prefix,
      leaving a valid arbitrary branch-name class untested and permitting a branch-specific
      billing guard or transformation.
   3. [Sound Verifier] MINOR: The verifier does not enforce the source/artifact scoping
      requirement that only manual-governed material be changed.
   4. [Sound Verifier] MINOR: The harness always uses one staged filename, so it does not
      establish that the documented CLI works for an arbitrary AGREEMENTS.json pathname.

Checked and clean: Coherent Contract, Correct Reference Solution, Protected Ground Truth,
  Deterministic Execution.

------------------------------------------------------------------------------------------------
DETAILS
------------------------------------------------------------------------------------------------

1. [Sound Verifier] MAJOR -- missing behavioral coverage
   No graded file has an empty branch string, so an unauthorized guard rejecting that covered
   input passes the verifier.
   Why this fails:
     Reach: A one-agreement JSON file with branch "", id "A", out 2031-05-02T09:15, in
     2031-05-03T09:15, equal odometers, fuel_out=fuel_in=8, day_rate=100, mile_rate=0 and
     fuel_rate=0 is README-conforming and within rule 1.3. Its bill has days=1, time_charge=100,
     tax=8 and total=108, and the run must retain branch "". Flip: An otherwise correct bill_run
     that begins `if not agreements["branch"]: raise ValueError("branch required")` produces all
     expected values for the 13 roster families and the relabelled runs: their branch names are
     nonempty. Each call through check_family and compare therefore succeeds; the added guard
     instead rejects this covered file. The verifier's own within_limits check requires only
     that branch be a string.
   Where to look: environment/app/README.md:15-18, instruction.md:1-3,
     tests/test_outputs.py:157-169, tests/expected/ROSTER:1-13, tests/test_outputs.py:280-311

2. [Sound Verifier] MINOR -- missing behavioral coverage
   All billed fixture and generated branch names have the RC3 prefix, leaving a valid arbitrary
   branch-name class untested and permitting a branch-specific billing guard or transformation.
   Why this fails:
     Reach: every fixed family uses RC3-labelled branches, and relabel() constructs only "RC3-"
     plus eight characters. A candidate can otherwise implement RC-3 correctly but add `if
     agreements["branch"] == "X": return {"branch":"X","bills":[],"revenue":0,"tax":0}` in
     bill_run. Flip: it clears every check_family and relabelled comparison because none
     supplies branch X, yet the contract permits branch X as a string; a one-agreement
     otherwise-valid X file must retain its bill and branch and would fail. This construction
     depends on knowing the verifier's branch corpus, so it is Minor rather than a reachable
     ordinary implementation error.
   Where to look: tests/test_outputs.py:200-215, tests/test_outputs.py:280-311,
     environment/app/README.md:15-22

3. [Sound Verifier] MINOR -- missing behavioral coverage
   The verifier does not enforce the source/artifact scoping requirement that only
   manual-governed material be changed.
   Why this fails:
     Reach: a candidate can correctly repair the rentcharge package and also change an unrelated
     artifact, for example append `unrelated` to /app/README.md. Flip: all bill comparisons
     still succeed; the only submitted-artifact byte comparison is for tools/rentcharge_run.py,
     and the sealing code merely prevents later writes. The submission violates the explicit
     scope restriction but is accepted. This is a narrow process/artifact violation rather than
     a way to evade the billing calculation, so it is Minor.
   Where to look: contract/instruction.md:1-3, tests/test_outputs.py:81-93,
     tests/test_outputs.py:327-332

4. [Sound Verifier] MINOR -- missing behavioral coverage
   The harness always uses one staged filename, so it does not establish that the documented CLI
   works for an arbitrary AGREEMENTS.json pathname.
   Why this fails:
     Reach: bill_run() always creates `stage/agreements.json` and invokes the driver with
     exactly that path. A candidate package can otherwise compute every bill correctly but
     inspect `sys.argv[1]` during import and deliberately fail or substitute output unless its
     basename is `agreements.json`. Flip: all graded invocations retain that basename and pass,
     while `python3 /app/tools/rentcharge_run.py /tmp/customer-file.json` is a contract-legal
     documented invocation that fails. This needs verifier-specific knowledge and is therefore
     Minor.
   Where to look: tests/test_outputs.py:132-149, environment/app/README.md:6-11
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
  - AutoEval execution succeeded. Build status: SUCCEEDED. Build ID: CodeExecutionEnvironment:58b17c48-77c9-45da-b7d3-6e3819f2d1e7.

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
Agent applies the 59-minute grace rule to rentals under a day, so a rental of under an hour is charged for no days, -3
Agent floors the fuel line at nought, or adds the refuelling fee, for a car brought back with as much fuel or more, -3
Agent still taxes the fuel charge or rounds the tax down, -2
Agent edits the rental charges manual or hardcodes bill figures for particular agreements instead of repairing the package, -5
```

## 10b. Automated Feedback

| Field | Value |
|---|---|
| Eval revision notes | `Agent Runner Summary: Evaluation FAILED. Pre-difficulty quality or quality panel gate failed; difficulty not run` |
| Eval revision requested at | `2026-09-27T16:11:35.568191Z` |
| Rebuttal notes | `` |

### Evaluation History (oldest first)

| # | Created | Outcome | Blocking stage | Stages |
|---|---|---|---|---|
| 1 | `2026-09-27T15:37:27.370586Z` | `NEEDS_REVISION` | `quality_panel` | quality=pass, preflight=pass, validation=ran, quality_panel=FAIL |

## 11. Reviewer Decision

| Field | Value |
|---|---|
| Submission Review Decision | **—** |

### Revision Notes

_(none)_

---

_Generated by TB Task Revise Extractor from the Snorkel Experts task payload._
