---
name: task-batch
description: "Use when the user sends `task-batch N` or `/task-batch N`, where N is a positive integer, to autonomously create exactly N brand-new Terminus 3 tasks ready for platform iteration. Run task-miner, task-clone, separate-verifier Oracle/NOP validation, task-zip-submit, task-client-feedback-review, adaptive task-local-solve-probe runs, and task-llm-style-audit. Do not use for ports, returned-task remediation, or ordinary single-task work."
---

# Task Batch

Create a fresh autonomous batch of submit-ready Terminus Regular tasks.

## Invocation

Accept either form:

```text
task-batch N
/task-batch N
```

Treat `N` as the required delivery quota. It must be a positive integer.

When invoked:

- Do not ask the user to choose repositories, languages, categories, candidates, or fixes.
- Make all normal task-building decisions autonomously.
- Deliver exactly `N` accepted tasks.
- Use any suitable implementation language, including Python when it fits.
- Build a useful Terminus 3 difficulty mix. Preserve valid Base/Core candidates;
  do not force every task toward Frontier.
- Keep mining replacements until the quota is met.
- Treat every invocation as a fresh batch. Do not port, reskin, or reuse an existing task unless the user explicitly requests that separately.

## Required Skills

Read each relevant `SKILL.md` completely before using that stage:

1. `task-miner`
2. `task-clone`
3. `task-harbor-runner`
4. `task-zip-submit`
5. `task-client-feedback-review`
6. `task-local-solve-probe`
7. `task-llm-style-audit`

Use `terminus-regular-task-authoring` and any language-specific authoring skill when required by the selected task.

This file controls the batch policy when it is more specific than a dependent skill. In particular, use the actual fresh subagent model available in the current environment; do not require or claim an unavailable pinned model.

## Truthfulness Rules

- Never claim that a command, validation, review, or probe ran without its real output and exit status.
- Never invent a subagent, model name, transcript, run ID, score, diff, or test result.
- Record the actual model reported by each probe environment when available.
- Treat setup, Docker, tool, dependency, timeout, and compilation failures as infrastructure failures, not evidence of task difficulty.
- Do not mark a task submit-ready while a required local check is blocked.
- Harbor API-key-dependent LLM-agent runs are not required. Local Docker build, Oracle, NOP, and non-API Harbor checks are required.
- If external infrastructure is unavailable, continue every safe independent step, preserve the artifacts, and report the exact blocker. Never fabricate completion to satisfy the quota.

## Preflight

Before mining:

1. Confirm the workspace and output directories.
2. Confirm Docker is reachable.
3. Confirm the local Terminus/Harbor tooling needed for Oracle and NOP runs is available.
4. Confirm repository mining access is available.
5. Inspect existing workspace and submission slugs so the batch cannot overwrite or duplicate them.

Stop early only for a real external blocker that prevents all useful progress. Otherwise continue autonomously.

## Batch Loop

Maintain an accepted-task counter. Repeat the following workflow until the counter equals `N`.

### 1. Mine a Fresh Candidate

Use `task-miner`.

The candidate must:

- use a domain-appropriate implementation language;
- be brand-new and gallery-novel;
- fit one exact Terminus 3 category/subcategory pair;
- have a fair, visible, offline-solvable contract;
- have enough independent behavioral depth to plausibly resist a strong agent;
- avoid saturated task families, known collapse patterns, hidden graded rules, and unreachable authorities;
- record its source repository, base commit, task contract, category, language, and novelty evidence.

Reject weak candidates before building. Do not fill quota with ports or cosmetic variants.

### 2. Clone and Build the Task

Use `task-clone` to create the task under `workspace/tbrain-<slug>/`.

Build the complete task:

- `instruction.md`
- `task.toml`
- `environment/`
- `solution/`
- `tests/`
- any required local references or fixtures

Keep the task's domain aligned with its exact category/subcategory pair. Python
used only by the verifier is not an implementation language.

Before difficulty probing, verify instruction sufficiency:

- Every graded behavior is stated in the instruction, demonstrated by an agent-visible example, supported by visible training data, or derivable from an offline-reachable authority.
- No hidden test depends on an unstated rule, convention, tie-break, constant, or output format.
- Every important instruction requirement has a matching verifier check.
- Every verifier behavior has a visible contractual basis.
- Reasonable alternative interpretations are unambiguously rejected by visible evidence.
- The Oracle agrees with the visible contract.

Create and validate the repository's instruction-sufficiency manifest when the authoring workflow requires it. Fix insufficiency before any solve probe.

Run and pass:

1. Whole-task Ruff validation with `--extend-select PLW1510`; every
   `subprocess.run(...)` must include explicit `check=True` or `check=False`.
2. Docker image build.
3. Oracle validation with reward `1.0`.
4. NOP validation with reward `0.0`.
5. Applicable local Harbor/Terminus checks that do not require an API key.

Use `task-harbor-runner` for Harbor execution and triage. Fix task defects and rerun the affected checks. Drop the candidate if the contract, authority, or environment cannot be made fair and reliable without collapsing the task.

### 3. Package the Task

Use `task-zip-submit`.

- Zip the task contents, not the parent directory.
- Exclude caches, local reports, solve copies, secrets, VCS metadata, and macOS resource forks.
- Write the archive to `submissions/<slug>.zip`.
- Inspect the archive listing after creation.

### 4. Review the ZIP and Fix It

Use `task-client-feedback-review` on the packaged ZIP.

The user has explicitly authorized fixes for this batch. Apply all blockers and relevant should-fix findings, with special attention to:

- instruction insufficiency or instruction/test asymmetry;
- offline authority reachability;
- prompt, rubric, solution, expected-output, or fixture leakage;
- Docker and dependency placement;
- canonical base image and metadata accuracy;
- verifier robustness and behavioral coverage;
- archive layout and submission hygiene.

After any task change:

1. Rerun Docker build.
2. Rerun Oracle and NOP.
3. Rerun applicable local Harbor checks.
4. Recreate the ZIP.
5. Review the new ZIP again.

Do not advance while a review blocker remains.

### 5. Run the Local Solve Probe

Use `task-local-solve-probe` with fresh subagents and isolated solve copies. Do not expose the solution, verifier tests, rubrics, reports, expected outputs, or hidden fixtures.

Use the actual subagent model available in the current environment. Preserve the real diff, verifier result, and failure classification for each attempt.

Run two fresh attempts initially. Add a third only after a split, a shared blind
spot, or incomplete per-case union.

- A semantic failure is valid difficulty evidence only when it matches the
  documented crux and the contract is instruction-sufficient.
- Setup, compilation, dependency, refusal, and timeout failures do not count.
- If all local attempts solve the task, fairly strengthen it once or replace it;
  do not spend platform iteration quota on a locally 100% candidate.
- If at least one attempt fails semantically, retain the candidate and record a
  provisional tier signal from the observed local pass rate. Do not present that
  signal as the final platform tier.
- For a zero-solve Frontier signal, require 100% per-case union, zero common
  misses, and de-correlated failures. Otherwise audit the oracle and visible
  authority before proceeding.
- A split result is a valid Core/Advanced signal when both the passing and
  failing runs are trustworthy. Python follows the same rule as every language.

The platform iteration stage uses two runs per current reference model and
requires at least one failure across all four. Final difficulty is measured over
eight runs, so local evidence remains provisional.

If hardening changes instructions, tests, fixtures, solution, environment, or metadata, rerun every affected gate and replace the ZIP before continuing.

### 6. Audit LLM Writing Style

Use `task-llm-style-audit` after the task has passed the technical and difficulty gates.

Audit every reviewer-visible prose surface, including:

- `instruction.md`;
- environment documentation and code comments;
- rubric text;
- submission explanations;
- metadata descriptions.

Rewrite flagged prose in clear, natural English without changing technical meaning, adding unsupported claims, or breaking instruction/test symmetry.

If the audit changes task contents, rerun the affected validation, recreate the ZIP, and confirm the final archive. If it changes only the external submission file, re-audit that file.

## Submission File

Create one file per accepted task:

```text
submissions/SUBMISSION-<slug>.md
```

Use this exact structure:

```markdown
# Difficulty Explanation

Describe in original language why the task is challenging for humans and coding agents. Base the explanation on the actual task design and observed probe failures. Do not claim unsupported platform difficulty.

# Solution Explanation

Describe the high-level solution approach and the key implementation insights. Do not copy the full Oracle or expose hidden fixture values.

# Verification Explanation

Explain how the tests verify correctness, including the major behavior clusters, preservation checks, edge cases, and anti-shortcut coverage.

# Metadata

- Does this task use an approved canonical base image? Yes — `<exact image reference>` / No — `<reason>`
- Did you use a Task Inspiration from the Task Gallery for this submission? Yes / No
- Task Inspiration ID: `<ID or N/A>`

# Rubrics

Agent completes `<observable behavior>`, +5
Agent completes `<observable behavior>`, +5
Agent preserves `<observable behavior>`, +3
Agent breaks `<observable behavior>`, -3
```

Rubrics must:

- grade observable behavior, not implementation style;
- use one physical line per rubric item;
- start with `Agent`;
- end with an allowed signed score;
- avoid hidden fixture values, test names, solution details, and private failure evidence;
- cover the task's main independent behavior clusters;
- remain consistent with the instruction and verifier.

Run the style audit on the completed submission file.

## Acceptance Gate

Count a task toward `N` only when all of the following are true:

- The task is fresh and uses a domain-appropriate language.
- The task folder is complete.
- The visible contract is instruction-sufficient.
- Whole-task Ruff validation, including `PLW1510`, is clean.
- Docker builds successfully.
- Oracle reward is `1.0`.
- NOP reward is `0.0`.
- Applicable local Harbor checks pass without requiring an API key.
- The final ZIP passes client-feedback review with no blocker.
- Two valid fresh attempts exist, with an adaptive third when required, and at
  least one trustworthy semantic failure provides a local difficulty signal.
- The LLM-style audit is clean.
- `submissions/<slug>.zip` exists and matches the final task state.
- `submissions/SUBMISSION-<slug>.md` exists and is accurate.

Do not count rejected, infrastructure-failed, ambiguous, locally all-pass, or
merely packaged candidates. A trustworthy split is valid Terminus 3 evidence.

## Final Response

Report one row per accepted task with:

- slug;
- language;
- category;
- Docker result;
- Oracle reward;
- NOP reward;
- Harbor result;
- ZIP review result;
- probe run results and any adaptive third run;
- provisional local tier signal;
- ZIP path;
- submission file path.

Also list any discarded candidates and their concise rejection reasons. Distinguish verified results from unavailable external checks.
