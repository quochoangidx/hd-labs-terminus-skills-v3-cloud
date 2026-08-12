---
name: task-local-solve-probe
description: Use when cheaply probing a Terminus 3 task's fairness and provisional difficulty signal before platform iteration. Prepares isolated solve copies that exclude solution, tests, rubrics, and reports; starts with 2 fresh runs and adds a 3rd only for a split, shared blind spot, or incomplete union; scores stored diffs per case; and reports tier and coverage risk without language-specific rules.
---

# Task Local Solve Probe

Use this skill after a task folder exists and before platform submission,
especially when estimating how a task may behave under GPT-5.6 and Claude
Opus 5 before spending platform iteration quota.

This is a cheap prefilter, not a replacement for Harbor. Harbor remains the
source of truth for oracle/NOP/static checks, Docker behavior, and platform
confidence.

## Core Rules

- Never solve in a chat that has already seen the task's solution, verifier,
  rubric, platform analysis, or intended patch.
- Refuse a full difficulty probe unless
  `workspace/reports/<slug>/instruction-sufficiency.json` passes
  `terminus-regular-task-authoring/scripts/sufficiency_manifest_check.py`.
  Skeleton probes require the same contract-source and two-reviewer audit in
  draft form. A solver guessing a hidden rule correctly is not sufficiency
  evidence, and no probe result may override a failed gate.
- Do not change the source task while probing.
- Solve copies must exclude `solution/`, `tests/`, `reports/`, `rubric*`,
  `*_rubric*`, prior run logs, and generated submission zips.
- Verification copies may include the full task; create them with
  `probe.py materialize` so they contain only the exact solver delta on top of
  the current full task before running verifier commands.
- Default to 2 sequential fresh-context runs. Add a 3rd ONLY on a 1–1 split,
  when both failures share a case/feature cluster, or when their per-case union
  is incomplete. Use 1 run for a quick smoke probe. Pooling
  to N≥5 is an escalation option for same-engine families where per-engine
  numbers would otherwise be variance (AGENTS.md §7), never the default.
- Difficulty is language-independent. Python follows the same probe and tier
  rules as every other implementation language.
- Use parallel agents only when the user explicitly wants that and the
  orchestration is stable.
- Select the default blind solver from the active runtime — and PIN it
  mechanically, do not rely on inheritance:
  - Codex: use `gpt-5.6` with `reasoning_effort: medium`, even if the manager
    chat is using a higher effort.
  - Claude Code: use Claude Opus 5 with medium reasoning. Pass `model: opus`
    and the medium reasoning setting EXPLICITLY on every probe Agent call —
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
- **`task-batch` profile:** keep the same current-model pins. A locally all-pass
  task is poor use of iteration quota, but a split is a valid Core/Advanced
  signal and must not be discarded merely because one solver succeeded.
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
- Provider authentication, quota, or regional failures are infrastructure and
  leave the run unverified. When current `stb` model runs are available and the
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

## Workflow

1. Prepare 2 run folders by default under
   `workspace/local-solve-probes/<task-slug>/`; add `run_3` only for a 1–1
   split, shared blind spot, or incomplete union. Override with `--runs 1..5`
   when needed (N≥5 = same-engine pooling).
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
   recorded for diagnosis but can never qualify as difficulty.
8. For fair semantic failures, record the missed invariant, compatibility path,
   state transition, or project layer without exposing verifier fixture names.
9. Summarize the observed pass rate and whether the task is worth submitting
   and whether platform iteration is worth the quota.

Use the helper script when possible:

```bash
python3 .agent/skills/task-local-solve-probe/scripts/probe.py prepare workspace/tbrain-example
python3 .agent/skills/task-local-solve-probe/scripts/probe.py diff workspace/local-solve-probes/tbrain-example/run_1
python3 .agent/skills/task-local-solve-probe/scripts/probe.py materialize workspace/local-solve-probes/tbrain-example/run_1
python3 .agent/skills/task-local-solve-probe/scripts/probe.py record \
  workspace/local-solve-probes/tbrain-example/run_1 \
  --result fail --type semantic \
  --notes "missed target-specific manifest section" \
  --runner codex-subagent --runtime codex --model gpt-5.6 \
  --reasoning-effort medium --agent-session-id '<runtime agent id>' \
  --launch-command '<runtime generated launch provenance>' \
  --agent-transcript /path/to/raw-agent-transcript.md \
  --verifier-log /path/to/verifier.log \
  --verification-ctrf /path/to/verification-ctrf.json \
  --verification-command '<offline verifier command>' \
  --verification-exit-code 1 --reward 0
python3 .agent/skills/task-local-solve-probe/scripts/probe.py summarize workspace/local-solve-probes/tbrain-example
```

`summarize` is diagnostic only. It returns `needs_handover_validation` for a
  promising fully evidenced band; it never emits `candidate_ready`. Only
`batch-handover.py` may do that after checking the verifier matrix, hashes,
fairness, tier signal, and any required union/de-correlation evidence. As the final
trust boundary, handover reruns the fixed local NOP verifier against every
`verify/` tree and compares its raw CTRF/result/reward with the recorded run.
Docker/Harbor failure is `unverified`; caller-supplied output never substitutes.

Do NOT use `probe.py apply` or copy files into `verify/` by hand. Use
`probe.py materialize`; the handover gate later recomputes the diff and proves
that `verify/` is the current full task plus that exact solver delta.

## Skeleton mode — probe BEFORE the full build (mandatory gate in task-clone)

Run a difficulty probe as soon as a candidate has the minimum probeable
surface, BEFORE any oracle/verifier/packaging investment. This is the
mandatory gate in `task-clone` Workflow step 10 and `lever_patterns.md` L1
step 5; it exists because the old ordering (full build first, probe last)
burned the whole build cost on candidates with no local difficulty signal.

- **Minimum input:** a buildable `environment/` + `instruction.md` + the stub.
  No polished oracle, no hidden suite, no Dockerfile hardening, no packaging.
- **Scoring:** use a ROUGH check — a thrown-together differential against the
  intended authority, or about 30–60 hand-verified evaluation units spanning
  6–8 independent behavior clusters. Accept noise; the goal is to kill
  all-pass and single-lever candidates early, not to measure the exact
  difficulty band.
- **Verdict mapping (2 runs, adaptive 3rd):**
  - 2/2 pass (or 3/3 after an adaptive run) → redesign or replace before full
    investment; this sample provides no local signal.
  - 0/2 with de-correlated semantic failures and 100% per-case union → proceed
    to the full build without a 3rd run.
  - 1/2, shared failure cluster, or incomplete union → run the 3rd. A repeated
    common miss after that is an oracle/fairness/single-lever audit, not hold
    evidence.
  - Setup/instruction/skeleton failures → fix the skeleton and re-probe; these
    runs measure nothing about difficulty.
- **Limits:** skeleton mode never replaces the post-build probe or the
  candidate-readiness verdict below — the rough check command is too noisy to
  ground a submit decision, and the pass-table pre-audit needs the real
  corpus. A skeleton 0/2 is a "worth building" signal, not a Frontier label.

## Interpretation

Default probe (2 runs, adaptive 3rd):

- `0/2 pass` with de-correlated semantic failures and 100% union is a strong
  preliminary Frontier signal.
- A split triggers the adaptive third run. Map the observed pass fraction to a
  provisional Terminus 3 tier, regardless of implementation language.
- `2/2 pass` provides no local signal; rework or replace before using platform
  iteration quota.
- Any band where failures are setup, missing dependency, unclear instruction,
  or verifier construction: fix the task, not the difficulty label.

Cluster failures by behavior/invariant, not by pytest function name. Green
geometry spans ≥2 independent clusters (prefer ≥3); use a dominant cluster
above roughly 50% of all semantic misses as a warning that the apparent breadth
may still be one lever, not as an automatic pruning rule.

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

- If both runs pass: stop — the sample has no local signal. Do not run a 3rd
  hoping for a different answer.
- If the runs split 1–1: run the 3rd and record the resulting provisional tier.
- If both runs fail for setup, unclear instruction, or verifier construction
  reasons, stop and fix the task before probing again.
- If both runs fail semantically, score their per-case matrix before stopping.
  Stop at `0/2` only when union coverage is 100% and the failures are
  de-correlated. If both failures share a case/cluster, or union coverage is
  incomplete, spend ONE disambiguation run. A repeated common miss after run 3
  triggers oracle-authority audit and single-lever DROP/redesign; a different
  failure place or a pass returns to normal geometry scoring.

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
task environment. Match the task's `network_mode` and expose only the declared
environment tools; otherwise a probe pass may be falsely easy because the
solver reached an authority unavailable in the real task.

- Prefer a **fair probe**: give the solver a build command that runs inside the
  task image. Use `--network none` only for `network_mode = "no-network"`
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
- **Zero solves:** require 100% per-case union, zero common misses, and
  de-correlated failures before calling it a Frontier signal. Otherwise audit
  the oracle, authority, and instruction sufficiency.
- **Setup, verifier, dependency, refusal, or timeout failures:**
  `fix_task_first`; they never count toward difficulty.
- **Shared misses:** authority-audit first. Use
  `task-revise-flag-remediation` only when disclosure, test splitting, or
  reference data fixes fairness without manufacturing a higher tier.

Do not prune passing cases or hide contract facts to change the tier. Base and
Core are valid Terminus 3 outcomes.

## Solver prompt shape

Use a short prompt for each fresh solver:

```text
You are solving a Terminus 3 task locally. Work only inside this copied task
folder. Do not search for solution, tests, rubrics, reports, or platform
feedback. Read instruction.md and the codebase, make the change, and run the
checks available inside the copied environment. Stop when you have a candidate
artifact. This is a one-shot attempt; you will not receive verifier feedback.
```

Match the task's `network_mode`. Do not include prior analysis, expected
failure modes, oracle hints, or verifier case names.

## Reporting

Return:

- task slug and run count
- actual runtime, model, reasoning effort, and unique session IDs
- pass count and provisional tier signal
- semantic versus non-semantic failure distribution
- per-run case matrix, union coverage, common misses, and failure clusters
- whether zero-solve failures are de-correlated
- compact crux evidence suitable for
  `[metadata].difficulty_explanation`, without model names or hidden fixtures
- one status:
  - `incomplete_evidence`
  - `fix_task_first`
  - `rework_or_replace`
  - `needs_handover_validation`
  - `candidate_ready`

Only `batch-handover.py` may emit `candidate_ready` after verifying hashes,
the isolated solve deltas, CTRF evidence, instruction sufficiency, and trusted
verifier reruns.
