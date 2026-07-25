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

For a task that was already in the platform revision queue or awaiting review
before its category closed, pass `--revision-exception`. Never use this flag for
a net-new task; category availability remains a blocker by default.

Also run `scripts/preflight.sh <task-dir>` (repo root) for the mechanical
subset review_task.py doesn't itself check (.dockerignore contents,
`# syntax=` line, CRLF/arcnames, rubric closed-set).

For a workspace task, require and validate
`workspace/reports/<slug>/instruction-sufficiency.json` with
`terminus-regular-task-authoring/scripts/sufficiency_manifest_check.py`. Missing
or failing evidence is a blocker. For a standalone ZIP, the report is correctly
absent from the archive; recreate the contract-source matrix manually from the
ZIP and apply the blind-review procedure in
`terminus-regular-task-authoring/references/instruction-sufficiency-gate.md`.
The automated scanner cannot certify semantic sufficiency.

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
     - **Not vaguer than the tests (else Task Instruction Sufficiency FAIL).**
       If a test asserts a specific numeric threshold or exact value, the
       instruction MUST state that number. "reject a too-large exponent" while
       the test requires `> 24 bits` made 8/9 agents guess 31/33/64 and fail.
       Flag any tested cutoff/value that the instruction leaves implicit
       (`should_fix`). Naming the spec value the test checks is required
       sufficiency, not over-spec; optionally cite an in-repo precedent.
       Treat a reasonable implementation that passes every visible statement
       but fails a test as a blocker even when another solver guessed the hidden
       rule or every test has at least one passer.
       The "spec value" here means VALUES (numbers, output keys, data schema,
       exact-match constants) — docs want these explicit
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
       Sufficiency-FAIL when names were omitted, then the design-doc WARN when
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
   - Non-milestone rubrics should be flat `Agent ...` criteria; a single
     `# Rubric 1` header is tolerated but not required. `# Rubric 2+` is only
     for milestone tasks.
   - Milestone rubrics must use one block per milestone with `# Rubric 1`,
     `# Rubric 2`, etc.
   - Rubrics need at least three negative criteria overall; milestone rubrics
     also need at least one negative criterion per milestone.

3. Review reviewer-facing submission explanations when available. Look first
   for these external files:

```text
workspace/reports/<task-slug>/submission-explanations-source.md   (factual source notes)
submissions/SUBMISSION-<task-slug>.md                             (UI-ready platform packet)
```

   These files must remain outside the submitted task and ZIP (the review
   script also flags any `submission-*.md` found inside the ZIP).

   Review each field separately:

   - **Difficulty Explanation:** names intrinsic technical interactions and a
     plausible partial-fix trap; does not use repository size, test count,
     timeout rate, cold builds, instruction ambiguity, or verifier defects as
     evidence of difficulty.
   - **Solution Explanation:** matches the oracle and root cause at a high
     level; does not paste the patch, invent extra work, or leak back into
     `instruction.md`, environment docs, or rubrics.
   - **Verification Explanation:** maps behavioral cases to requirements,
     explains what catches partial fixes, and reports oracle/nop outcomes only
     when validation logs support them.

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
- `/logs/verifier` not prepared before early exits in `tests/test.sh`
- license files in small or minimal codebases
- `environment/data` used as an oversized prompt/spec extension
- hidden solution walkthroughs or bug hints in environment docs/comments
- missing `tmux`/`asciinema` in the task image (agent runs fail with
  `Failed to start tmux session` / `verifier_did_not_run`)
- `tests/` or `solution/` copied into the Docker image
- `privileged: true`, `SYS_ADMIN`/`NET_ADMIN`/`SYS_MODULE` capabilities, or
  `/var/run/docker.sock` mounts in docker-compose
- AI-scaffolding filenames in the environment (`CLAUDE.md`, `AGENTS.md`,
  `skills.md`, `.cursor/`)
- `codebase_size` not matching the `environment/` file count (excluding
  `Dockerfile`/`docker-compose*`): 0-19 `minimal`, 20-199 `small`, 200+ `large`.
  CI (`run_static_checks.py`) enforces this mechanically and rejects a mismatch.
- `ruff` errors anywhere ruff scans the task dir — INCLUDING upstream `.py`
  under `environment/repo` (CI lints the whole tree, default E4/E7/E9/F). Common
  hits: `F401`/`E741` in `tests/test_outputs.py`, `E402`/`E701`/`E731` in
  upstream dev/codegen scripts. Fix per `upstream-repo-sanitizer`.
- `agent.timeout_sec` outside `[1, 1800]` — CI hard-caps it at 1800 (a heavy
  build does not justify raising it; the build runs under `build_timeout_sec`
  and the verifier under `verifier.timeout_sec`, both separate from the agent
  budget).
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
- `tests/test.sh` that does NOT write a default `echo 0 > /logs/verifier/reward.txt`
  immediately after `mkdir -p /logs/verifier` (before pytest / any risky work).
  Reviewers require reward to default to 0 so a crash/timeout before the final
  block leaves 0, not an absent reward (KDL + HOCON 2026-07). Fix per
  `terminus-regular-task-authoring` (test.sh shape).
- verifier that runs a compiled binary but never REBUILDS it from the agent's
  source (only asserts the prebuilt binary exists) — the tests then don't enforce
  the "implement it in the source" contract (a stale image-built binary passes).
  Fix: session-fixture `rm` + `go/cargo build` from `/app` before cases (see
  `terminus-regular-task-authoring`, Verifier Rules).
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
- `difficulty` in `task.toml` not matching the platform's difficulty artifact
  (e.g. artifact reports `medium`, toml says `hard`) — align the metadata (a
  non-blocking cleanup reviewers still call out).
- a config/format PARSER task (HCL2, Dockerfile, HOCON, nginx, …) whose deliverable
  is "parse document → canonical JSON" but `category = "build-and-dependency-management"`
  — reviewers reject it as software-engineering (BLOCKED): "the actual work is
  implementing a full X parser from a stub." ⛔ The old fix — retarget
  `category = "data-processing"` with a transformation-first reframe — is DEAD:
  since 2026-07-11 `data-processing` is itself a blocked predicted category
  (`Predicted category 'data-processing' (confidence 0.9) is blocked`), so that
  retarget just swaps one blocked slug for another. A flagged parser task must
  either honestly become `system-administration`, `games`, or
  `machine-learning`, or be shelved/dropped. Build/dependency, security, and
  scientific-computing tasks are also blocked for net-new submissions as of
  Jul 24; do not recommend them as a reframe. When one parser is flagged, AUDIT the whole
  batch and shelve same-profile parsers proactively.
- `allow_internet` not matching the task's genuine need (new High reviewer
  criterion, policy 2026-07-13): `true` without a real requirement is
  eval-checked and may be rejected; our offline tasks must stay `false`. A task
  that genuinely needs the network (e.g. HuggingFace model download) MAY set
  `true` — keep it internet-enabled when that dependency is the task's point.
  For every live source, require exact version and immutable digest/hash pins,
  and grade stable invariants rather than drifting live values, rotating keys,
  or mutable API shapes.
- ⚠️ NOT blockers — official FAQ citations for pushback (portal FAQ, 2026-07-17):
  (a) rigorous verifier logic in `tests/` is LEGITIMATE — running the agent's
  binary, parsing its output, golden fixtures/hashes, spec-derived invariants,
  and hardcoded expected RESULTS ("fine and often required") are all sanctioned;
  the only real defects are a callable in `tests/` that maps task inputs to the
  complete expected artifact (end-to-end solving belongs in `solution/`) or
  hardcoding values the instruction says the agent must read from a config file.
  (b) base images: tasks whose CI passed before 2026-06-15 are grandfathered —
  reviewers shouldn't flag their base image (digest pinning still required).
  Cite the FAQ instead of editing correct files.

## Existing Skills To Use For Fixes

- `terminus-regular-task-authoring`: prompt, metadata, verifier, rubric, and
  `tests/test.sh` shape.
- `upstream-repo-sanitizer`: environment size, license files, secret-shaped
  files, hidden hint leakage, and codebase_size honesty.
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
