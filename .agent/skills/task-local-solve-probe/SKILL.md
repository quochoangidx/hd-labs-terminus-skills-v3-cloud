---
name: task-local-solve-probe
description: Use when probing a Terminus 3 task's fairness and provisional difficulty before platform iteration. Prepares two isolated solve copies that exclude solution, tests, rubrics, and reports; scores stored diffs per case; and accepts a CORE+ signal when zero or one of the two valid solvers succeeds.
---

# Task Local Solve Probe

Use this skill after a task folder exists and before platform submission,
especially when estimating how a task may behave under GPT-5.6 and Claude
Opus 5 before platform iteration.

This skill has two modes. An exploratory probe is a cheap prefilter and cannot
qualify a tier. A counted probe can qualify a provisional local difficulty band
only after the complete verifier and semantic coverage evidence are frozen.
Strict direct-Docker preflight must already prove basic Oracle/NOP/noexec and
image validity. Harbor remains the later full integration and
submission-readiness gate; it is not required merely to decide whether a valid
candidate belongs on a Core/Advanced/Frontier shortlist.

## Core Rules

- Never solve in a chat that has already seen the task's solution, verifier,
  rubric, platform analysis, or intended patch.
- Refuse a counted difficulty probe unless
  `workspace/reports/<slug>/instruction-sufficiency.json` uses
  `schema_version: 3` and passes
  `sufficiency_manifest_check.py --require-v3`, and
  `semantic-coverage.json` passes `semantic_coverage_check.py`. The
  `core_advanced_frontier` profile additionally requires
  `semantic_coverage_check.py --advanced-plus`.
  The latter binds the frozen verifier, public surfaces, mechanisms,
  interactions, executable mutants, and independent review. A skeleton probe
  uses `--exploratory`; it may reject an idea but never qualify a tier.
- Before counted preparation, require `preprobe_check.py` to pass. It validates
  the current task snapshot against strict Docker Oracle/NOP evidence,
  pre-freeze client/manual review, and the task-visible style audit. Packaging
  and submission prose remain post-probe.
- Do not change the source task while probing.
- Solve copies must exclude `solution/`, `tests/`, `reports/`, `rubric*`,
  `*_rubric*`, prior run logs, and generated submission zips.
- Verification copies may include the full task; create them with
  `probe.py materialize` so they contain only the exact solver delta on top of
  the current full task before running verifier commands.
- Launch 2 fresh-context solver attempts concurrently on separate solve copies.
  After both finish, materialize, execute the verifier, collect CTRF, and record
  the runs sequentially so Docker and verifier resources never contend. Never
  add a third valid result. If an attempt is invalid because of setup, provider,
  timeout, dependency, refusal, or runtime failure, preserve the invalid probe
  directory, prepare a fresh pair, and rerun; invalid attempts do not count
  toward the required pair. The final counted probe directory always contains
  exactly two comparable valid results.
  Use 1 run only for an explicitly exploratory smoke probe.
- Difficulty is language-independent. Python follows the same probe and tier
  rules as every other implementation language.
- The solver pair is the safe parallel unit. Do not parallelize their verifier
  executions, Docker builds, or mutation work.
- In `task-batch`, the two valid solver sessions must be distinct from the
  builder, fairness reviewer, consolidated auditor, and each other. The role
  topology is one persistent builder, one persistent reviewer, one persistent
  auditor, and two valid solver results; failed attempts and corrective
  follow-ups have no quota.
- Select the default blind solver from the active runtime — and PIN it
  mechanically, do not rely on inheritance:
  - Codex: use `gpt-5.6-sol` with `reasoning_effort: medium` for every subagent:
    builder, fairness reviewer, both blind solvers, and auditor.
  - Claude Code: use Claude Opus 5 with medium reasoning. Pass `model: opus`
    and the medium reasoning setting EXPLICITLY on every subagent call —
    subagents inherit the session model by default, so a session running a
    stronger tier that omits the parameter probes with a solver outside the
    current platform pool (Opus 5 + GPT-5.6), distorting the tier estimate.
  Do not silently substitute a cheaper OR stronger model across runtimes. Use a
  different model or higher reasoning effort only when the user explicitly asks
  for it.
- If the runtime cannot create a fresh subagent on the required profile, stop
  the difficulty gate as `unverified`. Never replace the run with `stb`, a
  Harbor LLM agent, a manager-authored surrogate implementation, or a
  handwritten result. The solver must edit its own isolated `solve/` copy.
- **`task-batch` profile:** keep the same runtime-specific model pin for every
  subagent. Under `core_advanced_frontier`, `0/2` or `1/2` solved qualifies for
  handover after all quality gates pass. `2/2` triggers one fair strengthening
  cycle and one fresh two-run re-probe, then rejection if it remains all-pass.
  Union coverage, common misses, and semantic geometry are diagnostic only.
- Record `probe_model` in every run log and every verdict written to
  `index.jsonl`. Outside the `task-batch` override, verdict validity under model
  mismatch is ASYMMETRIC: a FAIL
  from a stronger-than-pool solver is still valid hold evidence (the pool model
  would also fail), but a PASS from a stronger-than-pool solver is invalid as
  a tier estimate — re-run that pass with the platform-matched model before
  dropping the candidate. Any historical `2/2 pass` verdict whose `probe_model`
  is missing or stronger than the pool is eligible for an opus re-probe on
  request.
- Default mode is `difficulty_probe`: each run is a one-shot solve attempt, like
  a Harbor/platform agent run. After the solver finalizes, verify the diff and
  record pass/fail. Do not send verifier logs, hidden cases, or expected
  failures back to the same solver for a second try.
- Use `debug_task` only when the goal is to repair the task/verifier/solution,
  not to measure difficulty. Debug retries do not count toward probe pass rate.
- Use a default soft solve budget of 600 seconds per run. Raise to 1800 seconds
  only for shortlist candidates or when the user explicitly asks for a
  Harbor-like long solve budget. The manager may wait in shorter chunks, but
  should not let a local solve probe run indefinitely.
- Provider authentication, capacity, or regional failures are infrastructure and
  leave the run unverified. Retry with a fresh replacement on the required
  profile until two valid results exist or external infrastructure remains
  genuinely unavailable. When current `stb` model runs are available and the
  user approves the cost, they may supplement local probes; never fabricate a
  substitute result.
- For post-build handover, follow
  [references/evidence-schema.md](references/evidence-schema.md). Use
  `probe.py prepare`, `diff`, `materialize`, and `record` to create the probe
  state and run results. `batch-handover.py` derives the verdict from those
  artifacts; prose in `probe-verdict.json` cannot substitute for them.
- **Lower-tier lane:** Terminus 3 accepts Base and Core tasks. When at least one
  valid run fails semantically and the task is fair, keep the observed lower-tier
  signal instead of pruning cases to manufacture a higher tier. An all-pass
  local sample still needs redesign or replacement before platform iteration.
- **CORE+ lane:** `core_advanced_frontier` accepts a mutation-backed `0/2` or
  `1/2` result after all quality gates pass. Preserve geometry diagnostics but
  do not use them as acceptance conditions. Reject a second consecutive `2/2`.

## Workflow

1. Prepare 2 active run folders under
   `workspace/local-solve-probes/<task-slug>/`. Counted preparation first runs the
   shared pre-probe ordering gate; exploratory preparation does not.
2. For each run, give the solver only `solve/`, which contains the sanitized
   task environment and `instruction.md`.
3. The solver edits only that run's `solve/` copy and returns one final
   candidate patch.
4. Capture the diff against the immutable sanitized `baseline/` copy.
5. Run `probe.py materialize run_N`. It rebuilds `verify/` from the current full
   task plus exactly the `baseline/`→`solve/` delta and rejects edits outside
   `environment/`.
6. Run the same local verifier command you would normally trust for the task.
7. Export the raw agent transcript, verifier log, and raw CTRF report, then
   use `probe.py record` with the runtime-generated fresh-agent session ID,
   actual model, and launch provenance. `record` derives `case-matrix.json`
   from CTRF; do not hand-author it. Compile/setup/timeout/unknown failures are
   recorded for diagnosis but can never qualify as difficulty. Archive that
   invalid probe bundle and prepare a fresh pair until the active bundle has two
   valid results.
8. For fair semantic failures, record the missed invariant, compatibility path,
   state transition, or project layer without exposing verifier fixture names.
9. Summarize the observed pass rate and whether the task is worth submitting
   and whether platform iteration is warranted.

Use the helper script when possible:

```bash
python3 .agent/skills/task-local-solve-probe/scripts/probe.py prepare \
  workspace/tasks/tbrain-example --profile general
python3 .agent/skills/task-local-solve-probe/scripts/probe.py diff workspace/local-solve-probes/tbrain-example/run_1
python3 .agent/skills/task-local-solve-probe/scripts/probe.py materialize workspace/local-solve-probes/tbrain-example/run_1
python3 .agent/skills/task-local-solve-probe/scripts/probe.py record \
  workspace/local-solve-probes/tbrain-example/run_1 \
  --result fail --type semantic \
  --notes "missed target-specific manifest section" \
  --runner codex-subagent --runtime codex --model gpt-5.6-sol \
  --reasoning-effort medium --agent-session-id '<runtime agent id>' \
  --launch-command '<runtime generated launch provenance>' \
  --agent-transcript /path/to/raw-agent-transcript.md \
  --verifier-log /path/to/verifier.log \
  --verification-ctrf /path/to/verification-ctrf.json \
  --verification-command '<offline verifier command>' \
  --verification-exit-code 1 --reward 0
python3 .agent/skills/task-local-solve-probe/scripts/probe.py summarize workspace/local-solve-probes/tbrain-example
```

For the current CORE+ campaign, summarize with the profile used at preparation:

```bash
python3 .agent/skills/task-local-solve-probe/scripts/probe.py prepare \
  workspace/tasks/tbrain-example --profile core_advanced_frontier
python3 .agent/skills/task-local-solve-probe/scripts/probe.py summarize \
  workspace/local-solve-probes/tbrain-example \
  --profile core_advanced_frontier
```

The summarizer retains failure nodes, common misses, union coverage, and
de-correlation as diagnostics. None can demote or promote a valid CORE+ result.

`summarize` is diagnostic only. It returns `needs_handover_validation` for a
  promising fully evidenced band; it never emits `candidate_ready`. Only
`batch-handover.py` may do that after checking the verifier matrix, hashes,
fairness, tier signal, and the complete quality evidence. As the final
trust boundary, handover reruns the fixed local NOP verifier against every
`verify/` tree and compares its raw CTRF/result/reward with the recorded run.
Docker/Harbor failure is `unverified`; caller-supplied output never substitutes.

Do NOT use `probe.py apply` or copy files into `verify/` by hand. Use
`probe.py materialize`; the handover gate later recomputes the diff and proves
that `verify/` is the current full task plus that exact solver delta.

## Exploratory skeleton mode

Use `probe.py prepare --exploratory` when a cheap early screen is worthwhile.
This is optional cost control, not a difficulty gate. Never report its pass
fraction as Core/Advanced/Frontier and never reuse its runs after the full verifier
or contract changes.

- **Minimum input:** a buildable `environment/` + `instruction.md` + the stub.
  No polished oracle, no hidden suite, no Dockerfile hardening, no packaging.
- **Scoring:** use a ROUGH check — a thrown-together differential against the
  intended authority, or about 30–60 hand-verified evaluation units spanning
  6–8 independent behavior clusters. Accept noise; the goal is to kill
  all-pass and single-lever candidates early, not to measure the exact
  difficulty band.
- **Exploratory disposition (2 runs):**
  - 2/2 pass → redesign or replace before full
    investment; this sample provides no local signal.
  - 0/2 or 1/2 with valid semantic failures → proceed to the full build.
  - Setup/instruction/skeleton failures → fix the skeleton and re-probe; these
    runs measure nothing about difficulty.
- **Limits:** every outcome remains `exploratory_only`. A skeleton 0/2 is only a
  "worth completing the verifier" signal.

## Interpretation

Default probe (exactly 2 runs):

- `0/2 pass` is a preliminary Frontier signal after quality validation.
- `1/2 pass` is a preliminary Core signal under the current two-run mapping.
- `2/2 pass` provides no local signal; rework or replace before using platform
  iteration.
- Any band where failures are setup, missing dependency, unclear instruction,
  or verifier construction: fix the task, not the difficulty label.

Map failures to the mechanism/interaction nodes in `semantic-coverage.json`
for diagnosis, not acceptance. Common misses or concentrated geometry should
be reported, but they do not block a valid `0/2` or `1/2` result.

For larger comparable samples, map the pooled accuracy to the current tiers:
Frontier <20%, Advanced 20–<50%, Core 50–<80%, Base 80–<100%.

Compile-only failures are weak difficulty evidence. Strong signals are partial
fixes that compile but miss legitimate contexts, preservation behavior, edge
invariants, or the correct project layer.

These semantic failure patterns may support the later Difficulty Explanation.
Setup failures, instruction ambiguity, verifier defects, dependency failures,
compile-only mistakes, and timeouts must not be presented as intrinsic task
difficulty.

Early-stop rules (k=2 default):

- If both runs pass: fairly strengthen once, regenerate every invalidated
  quality receipt, and run a fresh pair. Reject after a second `2/2`.
- If the runs split 1–1: keep the task as a provisional Core candidate.
- If both runs fail for setup, unclear instruction, or verifier construction
  reasons, stop and fix the task before probing again.
- If both runs fail semantically, retain the per-case matrix and geometry for
  diagnosis and proceed to handover validation; do not add another solver.

## Historical calibration from Opus 4.8 probes (2026-06-21)

Hard empirical finding (7 from-scratch spec tasks built in one session, only 2
reached the old MEDIUM band): **Opus 4.8 solved almost any well-specified spec task 3/3.** It
knows standard algorithms/specs cold AND it differential-tests its output against
any reachable reference. Use this as shape evidence, not as current tier metadata.

What does NOT make Opus fail (all came back 3/3): a clean "implement standard X"
task, even with the formula withheld, the reference library absent from the image,
a niche language, or a genuinely tricky CENTRAL behavior (push-then-move-optimal
Sokoban, GNU `chmod` symbolic modes, NumPy quantile methods, RFC 5952 IPv6, DST
gap/fold). Making the hard thing the HEADLINE backfires: the solver focuses on it,
fuzzes it, and nails it.

What DID work (the only 2 wins, both the same lever): a **secondary sub-rule blind
spot inside a LARGE multi-rule spec**, in an input category the solver under-fuzzes
even with the reference in hand. Both wins were gitignore-family path matching
where the discriminating fixture was `<dir>/**` + a query of the directory itself
(trailing-slash / `type=dir`) — random fuzzers under-generate directory-typed
queries at a `/**` parent, so ~1/3 of solvers miss it. Recipe: large spec, bury
the discriminator in a non-headline rule, state its observable contract without
a worked example or implementation hint, and put fixtures in the under-fuzzed
shape. Never omit the rule itself.

## This probe is OVER-GENEROUS — make it fair, and know its limit

The blind solver may have host tools and network access that differ from the
task environment. Match `[agent].network_mode` and expose only the declared
environment tools; otherwise a probe pass may be falsely easy because the
solver reached an authority unavailable in the real task.

- Prefer a **fair probe**: give the solver a build command that runs inside the
  task image. Use `--network none` when `[agent].network_mode = "no-network"`
  (`docker run --rm -i --network none -v <repo>:/w:ro -w /w <task base image> bash -lc '<build && run>'`)
  and state "the environment is fully offline; this command is the only way to
  build/run; do not install or fetch anything." This denies references not in the
  image — but it does NOT stop a determined solver from running host `python3`
  against a stdlib reference, so **design reference-reachability away at mining
  time** (don't pick a behavior whose ground truth is a host stdlib).
- Materialize the solver's delta with `probe.py materialize`, then run the
  supported local NOP verification surface against `run_N/verify` (reward 1.0
  = solved). Do NOT use `probe.py apply`; its `diff -ruN` treats the
  sanitized-away `solution/`,`tests/` as deletions and corrupts `verify/`.
- **Probe copies go STALE the moment the source task is edited** (spec fix,
  corpus prune, test change after probe prep). Score solver diffs against the
  SOURCE task's `tests/` + oracle, never against a `run_N/verify` copy prepared
  earlier — a stale copy can flip the whole verdict. Tells: a "MISSING TEST FN"
  pytest error, or the copy's expected outputs disagreeing with the current
  contract/oracle. Sanity-gate before trusting any score: the SOURCE oracle must
  PASS and the stock/starting state must FAIL under the same command.

## Candidate-readiness verdict

The local probe produces preliminary evidence, not the final Terminus 3 tier.
The platform iteration stage runs two trials per model and requires at least one
failure across the four; final difficulty uses four trials per model.

Use these local outcomes:

- **All runs pass:** `rework_or_replace`. The local sample provides no signal.
- **At least one trustworthy semantic failure:** `needs_handover_validation`.
  Map the pass fraction to a provisional tier and preserve the real geometry.
- **Zero solves:** keep a provisional Frontier signal after all quality gates
  pass. Report union/common-miss/geometry diagnostics without blocking it.
- **Setup, verifier, dependency, refusal, or timeout failures:**
  `fix_task_first`; they never count toward difficulty.
- **Shared misses:** report them as risk diagnostics. The earlier independent
  fairness, Oracle/NOP, mutation, and auditor gates—not geometry—decide validity.

Do not prune passing cases or hide contract facts to change the tier. Base and
Core are valid Terminus 3 outcomes.

For `core_advanced_frontier`, replace the general verdict mapping above with:

- **`0/2` or `1/2`:** `core_plus_shortlist` after all quality evidence passes.
- **`2/2`:** `rework_or_replace`; strengthen fairly once and run a fresh pair,
  then reject if the second pair is also all-pass.

`core_plus_shortlist` is a probe-selection status, not the hash-bound
`candidate_ready` status and not a platform-confirmed tier.

## Solver prompt shape

Use a short prompt for each fresh solver:

```text
You are solving a Terminus 3 task locally. Work only inside this copied task
folder. Do not search for solution, tests, rubrics, reports, or platform
feedback. Read instruction.md and the codebase, make the change, and run the
checks available inside the copied environment. Stop when you have a candidate
artifact. This is a one-shot attempt; you will not receive verifier feedback.
```

Match the task's `[agent].network_mode`. Do not include prior analysis, expected
failure modes, oracle hints, or verifier case names.

## Reporting

Return:

- task slug and run count
- actual runtime, model, reasoning effort, and unique session IDs
- pass count and provisional tier signal
- semantic versus non-semantic failure distribution
- per-run case matrix, union coverage, common misses, and semantic-node failures
- automatic failure de-correlation as non-blocking diagnostic information
- compact crux evidence suitable for
  `[metadata].difficulty_explanation`, without model names or hidden fixtures
- one status:
  - `incomplete_evidence`
  - `fix_task_first`
  - `rework_or_replace`
  - `needs_handover_validation`
  - `unsupported_campaign_sample`
  - `exploratory_only`
  - `core_plus_shortlist`
  - `candidate_ready`

Only `batch-handover.py` may emit `candidate_ready` after verifying hashes,
the isolated solve deltas, CTRF evidence, V3 evidence inferability, and trusted
verifier reruns.
