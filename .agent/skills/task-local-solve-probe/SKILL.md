---
name: task-local-solve-probe
description: Use when cheaply probing whether a Terminus Regular task is too easy before spending Harbor LLM budget. Prepares isolated solve copies that exclude solution, tests, rubrics, and reports; records fresh-agent solve attempts, defaulting to 3 runs; applies diffs into verifier copies; and summarizes pass-rate risk without modifying the source task.
---

# Task Local Solve Probe

Use this skill after a task folder exists and before expensive Harbor LLM runs,
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
- Default to 3 sequential fresh-context runs. Use 1 run for a quick smoke probe
  and 5 runs only for shortlist candidates where the extra signal is worth the
  model budget.
- Use parallel agents only when the user explicitly wants that and the
  orchestration is stable.
- Select the default blind solver from the active runtime:
  - Codex: use `gpt-5.5` with `reasoning_effort: medium`, even if the manager
    chat is using a higher effort.
  - Claude Code: use Claude Opus 4.8 with its normal/default reasoning
    configuration.
  Do not silently substitute a cheaper model across runtimes. Use a different
  model or higher reasoning effort only when the user explicitly asks for it.
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
- If a Harbor GPT/Claude run is suggested after the probe, require both an AI
  API key and explicit user approval before running it.

## Workflow

1. Prepare 3 run folders by default under
   `workspace/local-solve-probes/<task-slug>/`; override with `--runs 1..5`
   when needed.
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
9. Summarize the observed pass rate and whether Harbor LLM spend is justified.

Use the helper script when possible:

```bash
python3 .agent/skills/task-local-solve-probe/scripts/probe.py prepare workspace/tbrain-example
python3 .agent/skills/task-local-solve-probe/scripts/probe.py diff workspace/local-solve-probes/tbrain-example/run_1
python3 .agent/skills/task-local-solve-probe/scripts/probe.py apply workspace/local-solve-probes/tbrain-example/run_1
python3 .agent/skills/task-local-solve-probe/scripts/probe.py record workspace/local-solve-probes/tbrain-example/run_1 --result fail --type semantic --notes "missed target-specific manifest section"
python3 .agent/skills/task-local-solve-probe/scripts/probe.py summarize workspace/local-solve-probes/tbrain-example
```

## Interpretation

- `0-2/5 pass` with semantic/fair failures: promising task; run Harbor GPT/Claude
  only if the user approves API usage.
- `0-2/5 pass` with setup, missing dependency, unclear instruction, or verifier
  construction failures: fix the task, not the difficulty label.
- `3/5 pass`: gray zone. Likely Medium unless failures show robust semantic
  blind spots across contexts.
- `4-5/5 pass`: likely too easy for a top batch; rework or replace.

Compile-only failures are weak difficulty evidence. Strong signals are partial
fixes that compile but miss legitimate contexts, preservation behavior, edge
invariants, or the correct project layer.

These semantic failure patterns may support the later Difficulty Explanation.
Setup failures, instruction ambiguity, verifier defects, dependency failures,
compile-only mistakes, and timeouts must not be presented as intrinsic task
difficulty.

Early-stop rules:

- If the first 2 runs pass quickly, stop and treat the task as likely too easy.
- If the first 2 runs fail for setup, unclear instruction, or verifier
  construction reasons, stop and fix the task before probing again.
- If the first 2 runs fail semantically in different fair ways, the task is
  already promising; a third run is optional when budget matters.

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
agent is sandboxed (no internet, task-image only). So a 3/3 here is a decisive
"too easy", but a probe pass can be falsely easy for tasks whose reference is
reachable.

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

## Coverage pre-audit for conformance corpora (pre-empt the 0/N flag)

For tasks graded per-case over a big corpus, the probe's solver diffs double as
a FREE correlated-blind-spot detector. The platform's blocking flag "Some tests
not passed by any agent run" fires exactly on cases ALL agents miss, and the
probe solvers predict those. After the runs:

- Score EACH solver's build per-case against the SOURCE corpus (not just the
  overall pass/fail) and compute the union: which cases did NO probe run pass?
- A case at 0/probes is a correlated-blind-spot candidate. Before submitting,
  disclose it (one instruction sentence or an in-env examples file), ship the
  missing non-derivable reference data in-env, or prune it — decision tree in
  `.agent/skills/task-revise-flag-remediation/SKILL.md`.
- Cases passed by only ~1 of 3 probes are fine (de-correlated hardness); the
  target shape is many independent quirk families each solver misses a
  DIFFERENT slice of.
- Solver diffs/binaries are reusable: after strengthening or pruning the
  corpus, RE-SCORE the stored diffs instead of re-running solvers.

This costs no extra solver budget and catches most coverage-flag returns one
platform cycle early.

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
- failure type distribution
- whether failures are semantic/fair or setup/instruction noise
- compact semantic failure patterns suitable as factual input to the Difficulty
  Explanation, with no solver/model names and no hidden fixture details
- recommendation: `rework`, `run_harbor_llm_with_approval`, `replace`, or
  `keep_without_llm_if_budget_limited`
