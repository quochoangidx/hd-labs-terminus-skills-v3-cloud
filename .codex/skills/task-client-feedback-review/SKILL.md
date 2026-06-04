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
python .codex/skills/task-client-feedback-review/scripts/review_task.py <task-or-zip> [...]
```

For global skill use:

```bash
python /Users/thuongthai/.codex/skills/task-client-feedback-review/scripts/review_task.py <task-or-zip> [...]
```

Use `--json` when another script will consume the result.

2. Read `instruction.md` and any provided/generated rubric manually for prompt
   realism:
   - Would a real developer who did not already know the solution include each
     sentence?
   - Does the prompt state desired behavior, or does it reveal root cause,
     implementation path, or exact patch shape?
   - Niche behavioral detail is acceptable when it makes tests fair.
     Implementation/root-cause detail is not.
   - Non-milestone rubrics should be flat `Agent ...` criteria; a single
     `# Rubric 1` header is tolerated but not required. `# Rubric 2+` is only
     for milestone tasks.
   - Milestone rubrics must use one block per milestone with `# Rubric 1`,
     `# Rubric 2`, etc.
   - Rubrics need at least three negative criteria overall; milestone rubrics
     also need at least one negative criterion per milestone.

3. Classify findings:
   - `blocker`: likely reject or high-severity client feedback issue.
   - `should_fix`: not always fatal, but fix before a new submission.
   - `polish`: useful prompt/rubric quality improvement.

## Current Client Blockers

- root-level `pyproject.toml`
- dependency wheels under `tests/`
- dependency installation or downloads in `tests/test.sh`
- instructions or rubrics referencing tests, verifier logic, `test.sh`,
  `test_outputs.py`, `/tests/`, hidden tests, CI, reward files, pytest, or final
  test results
- canary strings (`CANARY-*`)
- `/logs/verifier` not prepared before early exits in `tests/test.sh`
- license files in small or minimal codebases
- `environment/data` used as an oversized prompt/spec extension
- hidden solution walkthroughs or bug hints in environment docs/comments

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
```

If no blockers are found, still mention any residual risk such as skipped
Harbor/Docker validation or unreviewed platform rubrics.
