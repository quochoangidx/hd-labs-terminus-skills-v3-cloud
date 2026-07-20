---
name: task-local-solve-probe
description: Use when cheaply probing whether a Terminus Regular task is too easy before submission. Prepares isolated solve copies that exclude solution, tests, rubrics, and reports; records fresh-agent solve attempts, defaulting to 2 runs (a 3rd only on a 1-1 split); scores diffs against verifier copies; and summarizes pass-rate risk without modifying the source task.
---

# Task Local Solve Probe

Use this skill after a task folder exists and before platform submission,
especially when deciding whether a task is likely Medium/Hard for GPT-5.5 or
Claude Opus 4.8.

This is a cheap prefilter, not a replacement for Harbor. Harbor remains the
source of truth for oracle/NOP/static checks, Docker behavior, and platform
confidence.

## Core Rules

- Never solve in a chat that has already seen the task's solution, verifier,
  rubric, platform analysis, or intended patch.
- Do not change the source task while probing.
- Solve copies must exclude `solution/`, `tests/`, `reports/`, `rubric*`,
  `*_rubric*`, prior run logs, and generated submission zips.
- Verification copies may include the full task; apply only the solve diff into
  them before running verifier commands.
- Default to 2 sequential fresh-context runs, adding a 3rd ONLY on a 1–1 split
  (user probe default, 2026-07-19). Use 1 run for a quick smoke probe. Pooling
  to N≥5 is an escalation option for same-engine families where per-engine
  numbers would otherwise be variance (AGENTS.md §7), never the default.
- Use parallel agents only when the user explicitly wants that and the
  orchestration is stable.
- Select the default blind solver from the active runtime — and PIN it
  mechanically, do not rely on inheritance:
  - Codex: use `gpt-5.5` with `reasoning_effort: medium`, even if the manager
    chat is using a higher effort.
  - Claude Code: use Claude Opus 4.8 with its normal/default reasoning
    configuration. Pass `model: opus` EXPLICITLY on every probe Agent call —
    subagents inherit the session model by default, so a session running a
    stronger tier (Fable/Mythos) that omits the parameter probes with a
    stronger solver than the platform grading pool (Opus 4.8 + GPT-5) and
    systematically inflates false-EASY verdicts.
  Do not silently substitute a cheaper OR stronger model across runtimes. Use a
  different model or higher reasoning effort only when the user explicitly asks
  for it.
- Record `probe_model` in every run log and every verdict written to
  `index.jsonl`. Verdict validity under model mismatch is ASYMMETRIC: a FAIL
  from a stronger-than-pool solver is still valid hold evidence (the pool model
  would also fail), but a PASS from a stronger-than-pool solver is INVALID as
  EASY evidence — re-run that pass with the platform-matched model before
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
- Harbor LLM calls and stb agent runs are PERMANENTLY geoblocked from this
  environment (AGENTS.md §7) — never plan a Harbor GPT/Claude follow-up run.
  Local fresh-subagent probes plus platform submission results are the only
  difficulty signals.

## Workflow

1. Prepare 2 run folders by default under
   `workspace/local-solve-probes/<task-slug>/`; add a `run_3` only on a 1–1
   split. Override with `--runs 1..5` when needed (N≥5 = same-engine pooling).
2. For each run, give the solver only `solve/`, which contains the sanitized
   task environment and `instruction.md`.
3. The solver edits only that run's `solve/` copy and returns one final
   candidate patch.
4. Capture the diff from the solve copy.
5. Apply the diff into the matching `verify/` copy, which contains the full
   task including verifier files.
6. Run the same local verifier command you would normally trust for the task.
7. Record pass/fail plus failure type: `semantic`, `compile`, `setup`,
   `timeout`, or `unknown`.
8. For fair semantic failures, record the missed invariant, compatibility path,
   state transition, or project layer without exposing verifier fixture names.
9. Summarize the observed pass rate and whether the task is worth submitting
   (Harbor LLM runs are geoblocked — the platform's own agent runs after
   submission are the only downstream difficulty check).

Use the helper script when possible:

```bash
python3 .agent/skills/task-local-solve-probe/scripts/probe.py prepare workspace/tbrain-example
python3 .agent/skills/task-local-solve-probe/scripts/probe.py diff workspace/local-solve-probes/tbrain-example/run_1
python3 .agent/skills/task-local-solve-probe/scripts/probe.py record workspace/local-solve-probes/tbrain-example/run_1 --result fail --type semantic --notes "missed target-specific manifest section"
python3 .agent/skills/task-local-solve-probe/scripts/probe.py summarize workspace/local-solve-probes/tbrain-example
```

Do NOT use `probe.py apply` on sanitized solve copies — its `diff -ruN` records
the sanitized-away `solution/`/`tests/` as deletions and corrupts `verify/`.
Instead, copy the solver's changed source file(s) into the `verify/` copy by
hand (see the fair-probe section below).

## Skeleton mode — probe BEFORE the full build (mandatory gate in task-clone)

Run a difficulty probe as soon as a candidate has the minimum probeable
surface, BEFORE any oracle/verifier/packaging investment. This is the
mandatory gate in `task-clone` Workflow step 10 and `lever_patterns.md` L1
step 5; it exists because the old ordering (full build first, probe last)
burned the whole build cost on candidates that then probed all-pass EASY.

- **Minimum input:** a buildable `environment/` + `instruction.md` + the stub.
  No polished oracle, no hidden suite, no Dockerfile hardening, no packaging.
- **Scoring:** use a ROUGH check — a thrown-together differential against the
  intended authority, or a dozen hand-verified input→output cases. Accept
  noise; the goal is to kill all-pass-EASY candidates early, not to measure
  the exact difficulty band.
- **Verdict mapping (2 runs, 3rd only on a 1–1 split):**
  - 2/2 pass (or 2/3 after the tie-break run) → DROP or redesign the lever
    before building anything more. Apply the master collapse law (AGENTS.md
    §1): if no undisclosed in-image library-quirk differential and no
    undisclosed counter-intuitive rule survives, there is nothing to redesign
    around — drop.
  - 0/2, or 0–1/3 after a tie-break, with semantic failures → proceed to the
    full build, then run the normal post-build probe.
  - Setup/instruction/skeleton failures → fix the skeleton and re-probe; these
    runs measure nothing about difficulty.
- **Limits:** skeleton mode never replaces the post-build probe or the
  submit-readiness verdict below — the rough check command is too noisy to
  ground a submit decision, and the pass-table pre-audit needs the real
  corpus. A skeleton 0/2 is a "worth building" signal, not a HARD label.

## Interpretation

Default probe (2 runs, 3rd only on a 1–1 split):

- `0/2 pass` with semantic/fair failures: strongest hold signal; promising
  task.
- `1/1 split`: run the 3rd. `1/3` with semantic failures still holds (gray
  zone — likely Medium unless failures show robust semantic blind spots);
  `2/3` = collapse, rework or replace.
- `2/2 pass`: too easy for a top batch; rework or replace.
- Any band where failures are setup, missing dependency, unclear instruction,
  or verifier construction: fix the task, not the difficulty label.

Escalated pooling (N≥5 across same-engine variants): grade the pooled rate —
~0–25% pass with semantic failures is a HARD-signal, ~40–67% pools to Medium,
≥80% is easy (AGENTS.md §7).

Compile-only failures are weak difficulty evidence. Strong signals are partial
fixes that compile but miss legitimate contexts, preservation behavior, edge
invariants, or the correct project layer.

These semantic failure patterns may support the later Difficulty Explanation.
Setup failures, instruction ambiguity, verifier defects, dependency failures,
compile-only mistakes, and timeouts must not be presented as intrinsic task
difficulty.

Early-stop rules (k=2 default):

- If both runs pass: stop — `2/2` is EASY, drop or rework. Do not run a 3rd
  hoping for a different answer.
- If the runs split 1–1: run the 3rd (the only case that earns one). `2/3` =
  collapse; `1/3` with semantic failures = hold.
- If both runs fail for setup, unclear instruction, or verifier construction
  reasons, stop and fix the task before probing again.
- If both runs fail semantically in fair ways, stop — `0/2` is the strongest
  hold signal; no tie-break run is needed. EXCEPTION: if both failures land on
  the SAME single case/convention (the single-lever fair⊥hard fingerprint),
  n=2 convergence can be coincidence on a task with several hard clusters —
  spend ONE disambiguation run before concluding. Same place again → confirmed
  single-lever, DROP; a different failure place or a pass → score by the normal
  geometry rules instead.

## Beating Opus 4.8 is a ~1/5 lottery — calibrate expectations (2026-06-21)

Hard empirical finding (7 from-scratch spec tasks built in one session, only 2
reached MEDIUM): **Opus 4.8 solves almost any well-specified spec task 3/3.** It
knows standard algorithms/specs cold AND it differential-tests its output against
any reachable reference. Do NOT promise a pipeline of MEDIUM+ tasks; treat each
as a gamble and tell the user so up front.

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
the discriminator in a non-headline rule, do NOT spell out its subtle implication,
and put fixtures in the under-fuzzed shape.

## This probe is OVER-GENEROUS — make it fair, and know its limit

The blind solver runs on the host with full Docker + network, so it can
differential-test against ANY reference the platform agent could NOT: tools baked
in the task image (`git`, `chmod`, `openssl`) and — crucially — host-stdlib
references (`python3 -c "import ipaddress/csv/datetime/...; ..."`). The platform
agent is sandboxed (no internet, task-image only). So an all-pass (2/2) here is
a decisive "too easy", but a probe pass can be falsely easy for tasks whose
reference is reachable.

- Prefer a **fair probe** for compiled/non-Python tasks: give the solver a build
  command that runs INSIDE the task's own image with `--network none`
  (`docker run --rm -i --network none -v <repo>:/w:ro -w /w <task base image> bash -lc '<build && run>'`)
  and state "the environment is fully offline; this command is the only way to
  build/run; do not install or fetch anything." This denies references not in the
  image — but it does NOT stop a determined solver from running host `python3`
  against a stdlib reference, so **design reference-reachability away at mining
  time** (don't pick a behavior whose ground truth is a host stdlib).
- Apply the solver's diff by **copying the changed source file(s)** into the
  `verify/` copy and running `harbor --force-build -a nop -p run_N/verify`
  (reward 1.0 = solved). Do NOT use `probe.py apply` — its `diff -ruN` treats the
  sanitized-away `solution/`,`tests/` as deletions and corrupts `verify/`.
- **Probe copies go STALE the moment the source task is edited** (spec fix,
  corpus prune, test change after probe prep). Score solver diffs against the
  SOURCE task's `tests/` + oracle, never against a `run_N/verify` copy prepared
  earlier — a stale copy can flip the whole verdict. Tells: a "MISSING TEST FN"
  pytest error, or the copy's expected outputs disagreeing with the current
  contract/oracle. Sanity-gate before trusting any score: the SOURCE oracle must
  PASS and the stock/starting state must FAIL under the same command.

## Submit-readiness verdict (no extra runs — re-score the diffs you already have)

The probe must end with a SUBMIT verdict, not just a pass rate. It combines the
difficulty band with union coverage (the platform's blocking flag "Some tests
not passed by any agent run" fires on any case ALL agents miss), using only the
diffs already produced — never spend additional solver runs on this:

- **1/3 pass (after the tie-break run)** → union coverage is AUTOMATICALLY
  satisfied (the passing run covers every case). Verdict: **submit-ready** —
  the sweet spot (hard + every test reachable).
- **2/2 pass, or 2/3 after the tie-break** → **collapse**: default too easy,
  rework or replace — an all-but-one pass on this over-generous probe rarely
  survives even as Medium on the platform. Keep only with a concrete reason
  (e.g. the passes leaned on a host reference the fair in-image probe denies —
  then re-probe fairly).
- **0/2 pass** (strongest hold signal; same handling for a 0/3) → score each
  stored solver diff PER-CASE against the SOURCE corpus, combine the results,
  and pick the action by the failure GEOMETRY:
  1. **Union covers ALL cases** → **submit-ready** (each run failed a different
     slice = de-correlated hardness, exactly the target shape).
  2. **Killer cases sit inside group/aggregate tests but ≥1 run passed them
     individually** → **SPLIT**: parametrize the corpus per-case (changes the
     unit of coverage, not the win condition).
  3. **A few 0-probe cases on an irreducible obscure feature or undisclosed
     convention** → **PRUNE** them, or disclose / ship the non-derivable
     reference data in-env, per
     `.agent/skills/task-revise-flag-remediation/SKILL.md` — then RE-SCORE the
     same stored diffs (free) to confirm the union now covers everything.
  4. **Runs are NEAR-PERFECT, failing only one (or a couple of) case(s)** — the
     single-blind-spot fingerprint: the entire difficulty is one insight or
     ambiguity, with no fair middle (kept hidden = unfair 0/N; disclosed = the
     task collapses to EASY). → **REDESIGN around an independent lever, or DROP
     the task.** Do NOT prune your way out here — removing that case flips the
     near-perfect runs to 100% and leaves an EASY task.

Caveats: a 2–3-run local union is a noisier sample than the platform's ~10 runs
(a case at exactly 1/2 here can still land 0/N there), and this probe is
over-generous (see below) — a solver that pivoted to a host reference passes
cases a sandboxed platform agent cannot, hiding blind spots. Score diffs built
inside the task image with `--network none` when the verdict matters. The
platform run remains the source of truth.

## Solver Prompt Shape

Use a short prompt for each fresh solver:

```text
You are solving a Terminus Regular task locally. Work only inside this copied
task folder. Do not search for solution, tests, rubrics, reports, or platform
feedback. Read instruction.md and the codebase, make the fix, and run whatever
local checks are available inside the copied environment. Stop when you have a
candidate patch. This is a one-shot attempt: after your final answer, you will
not receive verifier feedback for another try.
```

Do not include prior analysis, expected failure modes, oracle hints, or verifier
case names.

## Reporting

Return:

- task slug
- run count
- pass count
- `probe_model` (the pinned solver model; a pass recorded under a
  stronger-than-pool model is flagged invalid-EASY, see Core Rules)
- failure type distribution
- whether failures are semantic/fair or setup/instruction noise
- compact semantic failure patterns suitable as factual input to the Difficulty
  Explanation, with no solver/model names and no hidden fixture details
- for 0/2 (or 0/3) conformance-corpus tasks: the per-case union verdict (all
  cases covered by ≥1 run, or the list of 0-probe correlated-blind-spot cases)
- recommendation, from this shared vocabulary (`probe.py summarize` emits the
  first four automatically; the last two require the manual per-case scoring
  above):
  - `submit_ready` — 0/2, or 0–1/3 after a tie-break, with fair semantic
    failures AND union covers every case
  - `gray_zone_review` — a 1–1 split awaiting its tie-break run, or a
    borderline pooled rate
  - `rework_or_replace` — 2/2 pass, or 2/3+ after the tie-break (collapse)
  - `fix_task_first` — failures dominated by setup/instruction/verifier noise
  - `fix_coverage_then_rescore` — 0/N with fixable 0-probe cases: split /
    prune / disclose
  - `redesign_or_drop` — 0/N with the near-perfect single-blind-spot
    fingerprint
