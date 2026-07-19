---
name: task-zip-submit
description: Use when packaging a Terminus task for Snorkel upload or checking ZIP structure. Ensures task contents, not the parent folder, are zipped; strips macOS resource forks and caches; verifies archive contents before submission.
---

# Task Zip Submit

Use this skill when creating or validating a submission ZIP.

## Zip Rule

Zip the contents of the task folder, not the folder itself.

Task folders usually live under `workspace/`. Zip from inside the task folder, not from the repository root. Put submission ZIPs under `workspace/submissions/` so generated artifacts stay ignored.

The ZIP must contain only the files/folders required by the Platform Submission Guide. Use an allowlist (`instruction.md task.toml environment solution tests`) rather than zipping `.` — a `.` glob silently pulls in files reviewers reject. Do not include `rubric.md` or `SUBMISSION.md` (rubrics are entered in the platform UI only; `SUBMISSION.md` is a local meta-doc — reviewers return the task if either ships in the ZIP), nor `reports/`, `submissions/`, `jobs/`, local notes, caches, downloaded source archives, root `.ruff_cache`, or the outer `workspace/` folder.

**Make shell scripts executable before zipping.** Reviewers reject a ZIP whose `tests/test.sh` or `solution/solve.sh` is non-executable. Run `chmod +x tests/test.sh solution/solve.sh` first, then verify the stored Unix mode with `unzip -Z <zip> tests/test.sh solution/solve.sh` (expect `-rwxr-xr-x`). `zip -X` preserves the Unix permission mode — it only strips uid/gid and timestamps — so the allowlist command below keeps the exec bit intact.

The platform's `Difficulty Explanation`, `Solution Explanation`, and
`Verification Explanation` fields are entered separately in the UI. They are
not ZIP contents.

For a Regular task, the ZIP root should contain:

```text
instruction.md
task.toml
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

## Metadata Update

Before packaging, update the task's `task.toml` `[metadata]` author fields to:

```toml
author_name = "anonymous"
author_email = "anonymous"
```

Replace existing `author_name` and `author_email` values instead of adding
duplicate keys.

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
zip -rX "../submissions/${TASK_NAME}.zip" instruction.md task.toml environment solution tests \
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
unzip -l "../submissions/${TASK_NAME}.zip" | grep -E '__MACOSX|\.DS_Store|/\._|__pycache__|\.pyc|/target/|/\.git/|/\.env|\.ruff_cache|\.pytest_cache|CLAUDE\.md|skills\.md|AGENTS\.md|rubric\.md|SUBMISSION\.md|reports/|submissions/|jobs/|workspace/' || true
```

Any hit from that grep is a blocker — re-zip with the allowlist. In particular `rubric.md` and `SUBMISSION.md` must not appear.

**Verifier self-containment:** files that ship in `tests/` must not reference paths that are absent at verify time. The verifier container mounts only `/app` and `tests/`; `reports/`, `solution/`, and root docs are NOT present. Grep the verifier for stray references before zipping — a docstring or comment pointing at `reports/...` (or `solution/...`) is a review blocker even though it is "just a comment":

```bash
grep -nE 'reports/|solution/|\.\./' tests/*.py || true   # expect no matches
```
Fix by removing the reference (make the docstring self-contained) rather than shipping the extra file.

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

Also good: every path in the ZIP starts with one of the allowlisted roots (`instruction.md`, `task.toml`, `environment/`, `solution/`, `tests/`) for Regular tasks.

## Client Feedback Blockers

Before upload, fail the package if any of these are present:

- root-level `pyproject.toml`
- any string beginning with `CANARY-`
- `.whl` files under `tests/`
- license files in small or minimal codebases
- `environment/data` used as an oversized prompt/spec extension
- `instruction.md` references `tests/`, `verifier`, `test.sh`,
  `test_outputs.py`, hidden tests, rubrics, CI, or reward files
- rubrics reference tests, verifier logic, `test.sh`, `test_outputs.py`,
  `/tests/`, hidden tests, CI, reward files, or pytest results
- `tests/test.sh` writes `/logs/verifier` only after an early exit guard

Verifier dependencies must be installed by `environment/Dockerfile`; `tests/`
should contain verifier scripts and fixtures, not dependency wheels.

Before upload, inspect environment README/spec/config/comment-heavy files for
hidden solution walkthroughs or prompt-bypass instructions. Supporting docs
must read like realistic engineering artifacts and all task goals must remain
in `instruction.md`.

## Submission Explanation Preflight

Before sending the task to a reviewer, locate:

```text
workspace/reports/<task-slug>/submission-explanations-source.md   (factual source notes)
submissions/SUBMISSION-<task-slug>.md                             (UI-ready platform packet)
```

The UI-ready packet must contain (alongside Metadata and Rubrics — see
`task-clone`/`task-batch` for the full packet format) exactly these three
explanation sections:

```text
Difficulty Explanation
Solution Explanation
Verification Explanation
```

Check that:

- the final text preserves the facts, thresholds, paths, APIs, and validation
  results from the source draft
- Difficulty describes intrinsic engineering difficulty, not slow builds,
  repository size, test count, or timeout behavior
- Solution matches the oracle at a high level without pasting code or a patch
- Verification explains behavioral discrimination and does not merely say that
  tests pass
- no field mentions LLMs, AI, models, agents, anti-LLM mechanisms, detection
  avoidance, guidelines, reviewer criteria, or policy dates
- neither explanation file is present in the task root or generated ZIP

Missing explanations should stop reviewer submission until they are written,
but they do not change the ZIP allowlist.

## Submission Reminder

On first upload:

- upload ZIP to Snorkel Expert Platform -> Terminus-2nd-Edition
- copy the three explanation sections (plus rubric and metadata answers)
  from the UI-ready `submissions/SUBMISSION-<slug>.md` packet into their
  matching platform fields; do not copy headings, rewrite diagnostics, or the
  factual source draft
- check "Generate Rubric(s)" while "Send to Reviewer" is unchecked
- keep "Send to Reviewer" unchecked
- inspect CI and generated rubric before final reviewer submission
- edit the generated rubric for accuracy and completeness
- verify rubric lines start with `Agent`, end with `, +/-N`, use only values 1,
  2, 3, or 5, never use 4, carry an explicit leading `+` on every positive
  score (write `+3`, not `3` — unsigned positives are sent back for revision),
  and focus on trace-evidenced behavior rather than final pytest results
- for non-milestone tasks, use a flat `Agent ...` list; a single `# Rubric 1`
  header is tolerated but not required, and `# Rubric 2+` is reserved for
  milestone tasks
- for milestone tasks, use `# Rubric 1`, `# Rubric 2`, etc. blocks matching the
  milestones
- ensure rubrics have at least three negative criteria overall; milestone
  rubrics also need at least one negative criterion and 10-40 positive points
  per milestone
- before final reviewer submission, uncheck "Generate Rubric(s)" so the edited
  rubric is not overwritten, then check "Send to Reviewer"
- after final submission, expect peer review in 1-7 business days; total review
  cycles can take 7-14 business days
