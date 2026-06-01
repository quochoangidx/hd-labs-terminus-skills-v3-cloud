---
name: task-zip-submit
description: Use when packaging a Terminus task for Snorkel upload or checking ZIP structure. Ensures task contents, not the parent folder, are zipped; strips macOS resource forks and caches; verifies archive contents before submission.
---

# Task Zip Submit

Use this skill when creating or validating a submission ZIP.

## Zip Rule

Zip the contents of the task folder, not the folder itself.

Task folders usually live under `workspace/`. Zip from inside the task folder, not from the repository root. Put submission ZIPs under `workspace/submissions/` so generated artifacts stay ignored.

The ZIP must contain only the files/folders required by the Platform Submission Guide. Use an allowlist. Do not include `reports/`, `submissions/`, local notes, caches, downloaded source archives, root `.ruff_cache`, or the outer `workspace/` folder.

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
find . \( -name '.DS_Store' -o -name '._*' -o -name '__MACOSX' -o -name '__pycache__' -o -name 'target' -o -name '.git' \) -print
find . -name '*.pyc' -print
find . \( -name '.ruff_cache' -o -name '.pytest_cache' -o -name '.mypy_cache' \) -print
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
    -x '*.DS_Store' -x '__MACOSX/*' -x '*/__pycache__/*' -x '*/target/*' -x '*/.git/*' -x '*/.ruff_cache/*' -x '*/.pytest_cache/*' -x '*.pyc'
```

## Milestone ZIP

From inside the task folder:

```bash
TASK_NAME="$(basename "$PWD")"
mkdir -p ../submissions
zip -rX "../submissions/${TASK_NAME}.zip" task.toml environment steps \
    -x '*.DS_Store' -x '__MACOSX/*' -x '*/__pycache__/*' -x '*/target/*' -x '*/.git/*' -x '*/.ruff_cache/*' -x '*/.pytest_cache/*' -x '*.pyc'
```

## Verify

```bash
TASK_NAME="$(basename "$PWD")"
unzip -l "../submissions/${TASK_NAME}.zip" | head -40
unzip -l "../submissions/${TASK_NAME}.zip" | grep -E '__MACOSX|\.DS_Store|/\._|__pycache__|\.pyc|/target/|/\.git/|\.ruff_cache|\.pytest_cache|reports/|submissions/|workspace/' || true
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

## Submission Reminder

On first upload:

- upload ZIP to Snorkel Expert Platform -> Terminus-2nd-Edition
- check rubric generation
- keep "Send to Reviewer" unchecked
- inspect CI and generated rubric before final reviewer submission
