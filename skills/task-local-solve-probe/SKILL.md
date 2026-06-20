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
8. Summarize the observed pass rate and whether Harbor LLM spend is justified.

Use the helper script when possible:

```bash
python3 skills/task-local-solve-probe/scripts/probe.py prepare workspace/tbrain-example
python3 skills/task-local-solve-probe/scripts/probe.py diff workspace/local-solve-probes/tbrain-example/run_1
python3 skills/task-local-solve-probe/scripts/probe.py apply workspace/local-solve-probes/tbrain-example/run_1
python3 skills/task-local-solve-probe/scripts/probe.py record workspace/local-solve-probes/tbrain-example/run_1 --result fail --type semantic --notes "missed target-specific manifest section"
python3 skills/task-local-solve-probe/scripts/probe.py summarize workspace/local-solve-probes/tbrain-example
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

Early-stop rules:

- If the first 2 runs pass quickly, stop and treat the task as likely too easy.
- If the first 2 runs fail for setup, unclear instruction, or verifier
  construction reasons, stop and fix the task before probing again.
- If the first 2 runs fail semantically in different fair ways, the task is
  already promising; a third run is optional when budget matters.

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
- recommendation: `rework`, `run_harbor_llm_with_approval`, `replace`, or
  `keep_without_llm_if_budget_limited`
