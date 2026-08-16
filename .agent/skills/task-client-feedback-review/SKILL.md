---
name: task-client-feedback-review
description: Use when reviewing a Terminus task folder or submission ZIP against current client feedback before upload or resubmission. Produces a blocker/should-fix/polish report, checks prompt/rubric leakage, packaging hygiene, verifier dependency placement, metadata, environment leakage, and recommends which existing skill should handle each fix. Review-only by default; do not auto-fix unless explicitly asked.
---

# Task Client Feedback Review

Use this skill when the user asks to review, audit, preflight, or recheck a
Terminus task folder or ZIP against client feedback.

This is a review gate, not an authoring workflow. Do not modify tasks unless
the user explicitly asks for fixes.

## Review Order

1. Run the bundled scanner:

```bash
python .agent/skills/task-client-feedback-review/scripts/review_task.py <task-or-zip> [...]
```

(The script lives in-repo at
`.agent/skills/task-client-feedback-review/scripts/review_task.py` — run it
from the repo root.)

Use `--json` when another script will consume the result.

For `task-batch`, run the same scanner/manual review twice at different trust
boundaries. Before counted probes, review the task folder and save:

```bash
python3 .agent/skills/task-client-feedback-review/scripts/review_task.py \
  workspace/tasks/<slug> --json --manual-review-pass \
  --review-transcript workspace/reports/<slug>/consolidated-pre-freeze-audit.md \
  --review-runtime <actual-runtime> --review-model <actual-model> \
  --review-session-id <actual-session-id> \
  --evidence-output workspace/reports/<slug>/pre-freeze-review.json
```

After probes and final packaging, review the exact ZIP and save:

```bash
python3 .agent/skills/task-client-feedback-review/scripts/review_task.py \
  workspace/submissions/<slug>.zip --json --manual-review-pass \
  --review-transcript workspace/reports/<slug>/client-review-transcript.md \
  --review-runtime <actual-runtime> --review-model <actual-model> \
  --review-session-id <actual-session-id> \
  --evidence-output workspace/reports/<slug>/client-review.json
```

In `task-batch`, this manual judgment belongs to the one consolidated auditor,
not a separate client-review agent. Before freeze, that auditor also performs
semantic realism and the task-tree style audit; all three receipts use the same
runtime/model/session/transcript provenance. After probes, reuse the same
auditor identity in a new turn for the exact ZIP, submission prose, and
handover surfaces. The scanner is deterministic and consumes no additional
agent session. Its static scan may run alongside the auditor's prose inventory,
but final Docker/package/handover commands stay sequential.

Use `--manual-review-pass` only after completing the manual checks below and
recording their real findings and disposition in the transcript. The batch
handover rejects a missing, empty, out-of-directory, or hash-mismatched
transcript.

Also run `scripts/preflight.sh <task-dir>` (repo root) for the mechanical
subset review_task.py doesn't itself check (.dockerignore contents,
`# syntax=` line, CRLF/arcnames, rubric closed-set).

For a workspace task, require schema version 3 in
`workspace/reports/<slug>/instruction-sufficiency.json` and validate it with
`sufficiency_manifest_check.py --require-v3`. Missing or failing evidence is a blocker. For a standalone ZIP,
the report is correctly absent from the archive; recreate the goal/evidence/
inference matrix manually from the ZIP and apply the fairness-review procedure in
`terminus-regular-task-authoring/references/instruction-sufficiency-gate.md`.
The automated scanner cannot certify semantic inferability.

For a counted-probe or batch task, also require
`workspace/reports/<slug>/semantic-coverage.json` and validate it against the
final task plus `verifier-matrix.json` with `semantic_coverage_check.py`
(`--advanced-plus` for that campaign). Confirm the receipt covers every public
entry point and that each mechanism/interaction mutant is a plausible partial
fix with both passing and failing CTRF units. Raw case count or cluster labels
do not substitute for this review.

2. Read `instruction.md` and any provided/generated rubric manually for prompt
   realism:
   - Would a real developer who did not already know the solution include each
     sentence?
   - Does the prompt state desired behavior, or does it reveal root cause,
     implementation path, or exact patch shape?
   - Niche behavioral detail is acceptable when it makes tests fair.
     Implementation/root-cause detail is not.
   - Flag these solution-giving anti-patterns (the #1 client reject, June 2026
     trial feedback) as `should_fix` (or `blocker` if blatant): "Right now the
     <component> does X internally" sentences that narrate the mechanism instead
     of the observable symptom; "the other path already enforces/handles it"
     tells that point at where to copy the fix; and fix-shaped requirements that
     restate the implementation (e.g. "reject a line whose host field begins
     with `@`" instead of "reject a line with more than one marker"). The scanner
     does not catch these; read for them. Specific thresholds/API/preservation
     cases the tests assert are NOT this problem (keep them for symmetry).
   - Two-way instruction/test symmetry (scanner does not catch; read for both
     directions; confirmed 2026-06 ssh-rsa-privatekey-dos hit BOTH at once):
     - **No unobtainable success-surface value.** If a test asserts an arbitrary
       numeric threshold or exact interface value that no visible source defines,
       the instruction must state it. "reject a too-large exponent" while
       the test requires `> 24 bits` made 8/9 agents guess 31/33/64 and fail.
       Flag any arbitrary cutoff/value absent from all task-visible evidence.
       Do not require a derived threshold, causal rule, protocol transition, or
       domain convention to be handed over when realistic evidence supports the
       inference. In that case audit the evidence graph and trajectory instead.
       The non-inferable interface surface means VALUES (output keys, public
       schema, exact-match constants, arbitrary policy numbers) — docs want these explicit
       (`structured_data_schema`, `behavior_in_task_description`). Distinguish
       these from CODE IDENTIFIERS the test pins (function signatures, struct
       field names/types, project layout). A test that reads `cp.CompressedOffset
       int64` / `cp.BitOffset uint8` does force the agent to produce those exact
       names, and omitting them makes agents compile-fail (confirmed 2026-06
       flate-inflate-checkpoint: 5/6 guessed `window` vs `Window`,
       `CompressedByteOffset` vs `CompressedOffset`). BUT do NOT flag this by
       telling the author to paste the struct schema/signature into the prompt —
       prompt-styling.md section 4 ("Overly Prescriptive Guidelines") calls
       listing exact signatures/struct layouts BAD, and that is exactly what the
       `instruction_check`/design-document reviewer rejects (flate hit
       a compile-time interface gap when names were omitted, then the design-doc WARN when
       the full schema was pasted in — the schema route cannot win). The
       docs-aligned fix is to make the verifier BEHAVIORAL/OPAQUE: pass the new
       value straight back into the consuming API as a black box and assert
       OBSERVABLE output, never reading its fields, so the instruction can say
       "you choose its fields" and fold per-field semantics into one coherence
       sentence. Only when a brand-new exported symbol genuinely cannot be made
       behavioral, name that single symbol minimally (the type/function the test
       must call) and nothing more. Recommend the redesign via `task-clone`.
     - **Config dependence is real.** When the instruction tells the agent to
       read a config/input file whose values may vary, mutate one meaningful
       value and rerun the verifier. It must read that value at runtime; a
       submission that ignores the file and hardcodes the original parameter
       must fail. Do not apply this to fixed output constants or golden results.
     - **Not broader than the tests (else Test Quality VULNERABLE).** Every
       condition the instruction promises must have a DISCRIMINATING test (one
       that fails on a partial fix omitting it). If the instruction lists a
       condition no test covers, flag it. Resolve by adding a discriminating
       test, or by removing the condition from the instruction when it cannot be
       made discriminating (e.g. an even/`<3` RSA exponent that the buggy
       build's own `Validate` already rejects, so a test passes on both nop and
       oracle = a dud). The oracle may legitimately do more than the instruction
       promises; the instruction must not promise more than the tests verify.
   - Numeric exact-string match on floating/irrational results (scanner does not
     catch; read the verifier; confirmed 2026-06 decimal-pow-precision FAILED +
     0/10 same two tests). If a test asserts `someFloatResult.String() ==
     "<literal>"` for an irrational/fractional value (a power, root, log, trig,
     division to many places), flag it `should_fix`: the literal is usually one
     implementation's undocumented rounding (often a float64 artifact LESS
     correct than the true value), so a more-accurate agent fails unfairly, and
     `precision`-style params get read as a rounding ceiling when the reference
     treats them as a minimum floor. Fix = assert accuracy tolerance against a
     high-precision TRUE reference (tol the oracle clears, naive misses by
     orders of magnitude; precision=N -> tol 1e-N), and state the precision
     contract in the instruction. Exact match is fine for genuinely exact values
     (integer results, defined truncations, edge-case zero/error).
   - Terminus 3 rubrics are a flat list of `Agent ...` criteria generated and
     edited in the platform UI; the submitted ZIP does not contain `rubrics.txt`.
   - Rubrics need at least one negative criterion, signed positive scores, only
     ±1/2/3/5 values, and 10–40 total positive points.

3. Review the four Terminus 3 submission explanations under `[metadata]` in
   `task.toml`: `difficulty_explanation`, `solution_explanation`,
   `verification_explanation`, and `relevant_experience`. Older external drafts
   may exist at:

```text
workspace/reports/<task-slug>/submission-explanations-source.md   (factual source notes)
workspace/submissions/SUBMISSION-<task-slug>.md                   (UI-ready platform packet)
```

   These files are optional authoring notes and must remain outside the submitted
   task and ZIP; the authoritative submitted values are in `task.toml`, from
   which Snorkel assembles `README.md`.

   Review each field separately:

   - **Difficulty Explanation:** names intrinsic technical interactions and a
     plausible partial-fix trap; does not use repository size, test count,
     timeout rate, cold builds, instruction ambiguity, or verifier defects as
     evidence of difficulty. It also names the origin/realism of accompanying
     data (or explicitly says there is none) and the professional role that
     would normally perform the work.
   - **Solution Explanation:** matches the oracle and root cause at a high
     level; does not paste the patch, invent extra work, or leak back into
     `instruction.md`, environment docs, or rubrics.
   - **Verification Explanation:** maps behavioral cases to requirements,
     explains what catches partial fixes, and reports oracle/nop outcomes only
     when validation logs support them.
   - **Relevant Experience:** gives concrete domain background without policy,
     model, or reviewer-directed language.

   Compare the UI-ready file against the factual source draft. Flag removed
   thresholds, changed API names, altered paths, unsupported validation claims,
   or softened preservation requirements.

   Apply a final prose check:

   - no references to LLMs, AI, models, agents, anti-LLM mechanisms, detection
     avoidance, guidelines, reviewer criteria, or policy dates
   - no generic claims such as "comprehensive", "robust", or "high confidence"
     without concrete support
   - the three fields do not repeat one identical template
   - the prose starts with task-specific facts and remains copy-paste ready

   Missing explanations are `should_fix` before reviewer submission, not a ZIP
   structure blocker. Unsupported facts, leaked solution material in
   agent-visible files, or claims contradicted by the oracle/verifier are
   `blocker`.

4. Classify findings:
   - `blocker`: likely reject or high-severity client feedback issue.
   - `should_fix`: not always fatal, but fix before a new submission.
   - `polish`: useful prompt/rubric quality improvement.

## Current Client Blockers

- missing `tests/Dockerfile`, missing `[verifier].environment_mode = "separate"`,
  or an agent-facing `environment/Dockerfile` that copies `tests/`/`solution/`
- missing top-level `artifacts`, artifact paths not covering everything the
  verifier reads, or missing artifact parent directories in `tests/Dockerfile`
- verifier dependencies not baked into `tests/Dockerfile` with exact pins
- stale Terminus 2 metadata (`allow_internet`, `codebase_size`,
  `number_of_milestones`, `subcategories`, `junior_time_estimate_min`, or
  `easy`/`medium`/`hard` difficulty)
- category/subcategory not using one exact Title Case Terminus 3 taxonomy pair
- `[agent].timeout_sec` below 1800 or above 18000
- root-level `pyproject.toml`
- dependency wheels under `tests/`
- dependency installation or downloads in `tests/test.sh`
- instructions or rubrics referencing tests, verifier logic, `test.sh`,
  `test_outputs.py`, `/tests/`, hidden tests, CI, reward files, pytest, or final
  test results. NOTE: the feedback scanner also matches the BARE WORD
  (`\bverifier\b`) in `instruction.md` and environment comments, so an innocent
  sentence like "the verifier binary reads stdin" trips it as a false positive —
  rename to "binary"/"program"/"the checks" to dodge it
- canary strings (`CANARY-*`)
- `/logs/verifier` not prepared before pytest runs in `tests/test.sh`
- `/logs/verifier` created without mode `0700` before reward/CTRF creation or
  before candidate execution; existence alone does not isolate the reward channel
- candidate subprocesses run without a fresh process group/session and without
  whole-group kill+reap on timeout and teardown. Dropping only the direct child
  to `nobody` does not stop descendants from holding pipes or surviving cases
- `environment/data` used as an oversized prompt/spec extension
- hidden solution walkthroughs or bug hints in environment docs/comments
- missing `tmux`/`asciinema` in the task image (agent runs fail with
  `Failed to start tmux session` / `verifier_did_not_run`)
- `tests/` or `solution/` copied into the Docker image
- `privileged: true`, `SYS_ADMIN`/`NET_ADMIN`/`SYS_MODULE` capabilities, or
  `/var/run/docker.sock` mounts in docker-compose
- AI-scaffolding filenames in the environment (`CLAUDE.md`, `AGENTS.md`,
  `skills.md`, `.cursor/`)
- `ruff` errors anywhere ruff scans the task dir — INCLUDING upstream `.py`
  under `environment/repo` (CI lints the whole tree, default E4/E7/E9/F). Common
  hits: `F401`/`E741` in `tests/test_outputs.py`, `E402`/`E701`/`E731` in
  upstream dev/codegen scripts. Fix per `upstream-repo-sanitizer`.
- `agent.timeout_sec` outside `[1800, 18000]` — 1800 seconds is the Terminus 3
  minimum, not the old maximum. Most substantial tasks should use 3600–5400.
- commercial-DB blacklist (CI `check_blacklisted_databases`, SUBSTRING match):
  the confirmed blocking token is `maxscale` (MariaDB MaxScale), which commonly
  false-matches a decimal `MaxScale` identifier in SQL-engine repos and still
  fails. Bare oracle/mysql/postgres/mariadb/mssql/snowflake were observed NOT
  flagged. Fix by renaming the identifier or removing a non-build-required file
  (see `upstream-repo-sanitizer`).
- reviewer-facing explanation text copied into `instruction.md`,
  `environment/`, or a rubric when it reveals root cause, oracle strategy, or
  verifier behavior
- submission explanations that materially contradict the task, oracle, or
  verifier, including unrun oracle/nop claims
- `tests/test.sh` using `set -e`, omitting `--ctrf`, or returning a non-zero
  script status. The current Terminus 3 form captures pytest's status, writes
  reward 1/0, then ends with `exit 0`; if the published skeleton differs, the
  skeleton wins.
- when the instruction requires source changes, a verifier that checks only a
  prebuilt binary does not enforce the source contract. Declare the project
  directory as an artifact, bake the compiler into `tests/Dockerfile`, and
  rebuild inside the separate verifier before cases. If the deliverable itself
  is a binary, declaring and testing that binary is valid.
- environment reference docs (`CANONICAL_FORM.md`, `FORMAT.md`, `SPEC.md`) that
  use GRADER vocabulary ("grading", "grader", "compares", "checks", "verifier",
  "test", "reward") OR contradict the instruction/rubric (e.g. doc says "key
  order is ignored" while the prompt requires sorted keys). Rewrite as a neutral
  product/format contract and reconcile doc↔instruction↔rubric to one story.
- reject/invalid-case asymmetry: `instruction.md` says an invalid input "writes
  nothing useful to stdout" but the verifier's invalid branch only asserts
  `returncode != 0`. Either assert `proc.stdout == b""` (if the oracle emits
  empty stdout on reject) or drop the stdout clause from the prompt.
- an output property the value-based verifier can't enforce still stated as a
  requirement: prompt/rubric demand lexicographically SORTED keys (or any
  ordering) while `test_outputs.py` compares PARSED values (order-independent,
  often to tolerate a float-repr gap). Drop the ungraded requirement from
  prompt/rubric/format-doc, or switch to a canonical-byte assertion.
- an output-write failure promise without a discriminating preservation test:
  pre-create a root-owned sentinel destination that the demoted candidate cannot
  write, then assert exit 1, non-empty stderr, and byte-identical contents; also
  cover the no-preexisting-file branch when the contract promises no creation
- `difficulty` in `task.toml` not matching the measured Terminus 3 tier:
  Frontier <20%, Advanced 20–<50%, Core 50–<80%, Base 80–<100%, averaged across
  both current reference models. A 100% iteration result cannot proceed.
- category chosen by coding activity instead of domain. Use `Software` only when
  software itself is the subject; otherwise choose the domain category and its
  exact subcategory (for example ML training repair is `ML / Training`).

## Existing Skills To Use For Fixes

- `terminus-regular-task-authoring`: prompt, metadata, verifier, rubric, and
  `tests/test.sh` shape.
- `upstream-repo-sanitizer`: environment size, license files, secret-shaped
  files, hidden hint leakage, and build-context hygiene.
- `task-zip-submit`: ZIP structure, allowlist, cleanup, metadata author fields,
  and final packaging.
- `task-harbor-runner`: oracle/nop/CI/Harbor validation and Docker triage.
- `task-clone`: redesign or restaging when a task is too small, too leaky, or
  structurally wrong. Minimal codebases are accepted when honest; redesign only
  when the task lacks realistic context or difficulty.

## Report Shape

Report findings per task:

```text
Task: <name>
Status: ready | needs cleanup | needs prompt/rubric review | needs redesign

Blockers:
- <finding> — why it matters — skill to use

Should fix:
- <finding> — why it matters — skill to use

Polish:
- <finding> — why it matters — skill to use

Submission narratives:
- Difficulty Explanation: ready | weak | missing
- Solution Explanation: ready | too detailed | missing
- Verification Explanation: ready | incomplete | missing
```

If no blockers are found, still mention any residual risk such as skipped
Harbor/Docker validation or unreviewed platform rubrics.
