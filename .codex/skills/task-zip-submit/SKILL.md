---
name: task-zip-submit
description: Use when packaging a Terminus task for Snorkel upload or checking ZIP structure. Ensures task contents, not the parent folder, are zipped; strips macOS resource forks and caches; verifies archive contents before submission.
---

# Task Zip Submit

Use this skill when creating or validating a submission ZIP.

## Zip Rule

Zip the contents of the task folder, not the folder itself.

Task folders usually live under `workspace/`. Zip from inside the task folder, not from the repository root. Put submission ZIPs under `workspace/submissions/` so generated artifacts stay ignored.

The ZIP must contain only the files/folders required by the Platform Submission Guide. Use an allowlist. Do not include `reports/`, `submissions/`, `jobs/`, local notes, caches, downloaded source archives, root `.ruff_cache`, or the outer `workspace/` folder.

For a Regular task, the ZIP root should contain:

```text
instruction.md
task.toml
pyproject.toml
environment/
solution/
tests/
```

For a milestone task, the ZIP root should contain:

```text
task.toml
environment/
steps/
```

Milestone ZIPs must not include root-level `instruction.md`, `solution/`, or `tests/`.

## Clean First

From the task root:

```bash
find . \( -name '.DS_Store' -o -name '._*' -o -name '__MACOSX' -o -name '__pycache__' -o -name 'target' -o -name '.git' -o -name '.env' \) -print
find . -name '*.pyc' -print
find . \( -name '.ruff_cache' -o -name '.pytest_cache' -o -name '.mypy_cache' \) -print
find environment -type f \( -name 'CLAUDE.md' -o -name 'skills.md' -o -name 'AGENTS.md' \) -print 2>/dev/null || true
```

Delete junk before packaging:

```bash
find . \( -name '.DS_Store' -o -name '._*' -o -name '__pycache__' -o -name 'target' -o -name '.git' -o -name '.ruff_cache' -o -name '.pytest_cache' -o -name '.mypy_cache' \) -exec rm -rf {} +
```

Do not use macOS Finder "Compress" when possible; it can add `__MACOSX` and `._*` files that fail CI.

## Regular ZIP

From inside the task folder:

```bash
TASK_NAME="$(basename "$PWD")"
mkdir -p ../submissions
zip -rX "../submissions/${TASK_NAME}.zip" instruction.md task.toml pyproject.toml environment solution tests \
    -x '*.DS_Store' -x '__MACOSX/*' -x '*/__pycache__/*' -x '*/target/*' -x '*/.git/*' -x '*/.env' -x '*/.ruff_cache/*' -x '*/.pytest_cache/*' -x '*.pyc' -x 'reports/*' -x 'submissions/*' -x 'jobs/*'
```

## Milestone ZIP

From inside the task folder:

```bash
TASK_NAME="$(basename "$PWD")"
mkdir -p ../submissions
zip -rX "../submissions/${TASK_NAME}.zip" task.toml environment steps \
    -x '*.DS_Store' -x '__MACOSX/*' -x '*/__pycache__/*' -x '*/target/*' -x '*/.git/*' -x '*/.env' -x '*/.ruff_cache/*' -x '*/.pytest_cache/*' -x '*.pyc' -x 'reports/*' -x 'submissions/*' -x 'jobs/*'
```

## Verify

```bash
TASK_NAME="$(basename "$PWD")"
unzip -l "../submissions/${TASK_NAME}.zip" | head -40
unzip -l "../submissions/${TASK_NAME}.zip" | grep -E '__MACOSX|\.DS_Store|/\._|__pycache__|\.pyc|/target/|/\.git/|/\.env|\.ruff_cache|\.pytest_cache|CLAUDE\.md|skills\.md|AGENTS\.md|reports/|submissions/|jobs/|workspace/' || true
```

The first listing must not show an extra top-level parent folder.

Bad:

```text
tbrain-example/instruction.md
tbrain-example/task.toml
```

Good:

```text
instruction.md
task.toml
environment/Dockerfile
```

Also good: every path in the ZIP starts with one of the allowlisted roots (`instruction.md`, `task.toml`, `pyproject.toml`, `environment/`, `solution/`, `tests/`) for Regular tasks.

Before upload, inspect environment README/spec/config/comment-heavy files for
hidden solution walkthroughs or prompt-bypass instructions. Supporting docs
must read like realistic engineering artifacts and all task goals must remain
in `instruction.md`.

## Submission Reminder

On first upload:

- upload ZIP to Snorkel Expert Platform -> Terminus-2nd-Edition
- check "Generate Rubric(s)" while "Send to Reviewer" is unchecked
- keep "Send to Reviewer" unchecked
- inspect CI and generated rubric before final reviewer submission
- edit the generated rubric for accuracy and completeness
- verify rubric lines start with `Agent`, end with `, +/-N`, use only values 1,
  2, 3, or 5, never use 4, and focus on trace-evidenced behavior rather than
  final pytest results
- ensure regular-task rubrics have at least three negative criteria and a 10-40
  positive-point total; milestone rubrics need at least one negative criterion
  and 10-40 positive points per milestone
- before final reviewer submission, uncheck "Generate Rubric(s)" so the edited
  rubric is not overwritten, then check "Send to Reviewer"
- after final submission, expect peer review in 1-7 business days; total review
  cycles can take 7-14 business days
