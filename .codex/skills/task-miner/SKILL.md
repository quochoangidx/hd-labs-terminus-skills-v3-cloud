---
name: task-miner
description: Use when mining a user-provided GitHub repo source, issue list, or pull-request list into hard Terminus Regular task candidates. Accepts repo source parameters such as owner/repo, a GitHub repository URL, or URLs ending in /issues or /pulls; helps find real closed bugs or merged PRs suitable for task-clone.
---

# Task Miner

Use this skill to source hard Terminus Regular task ideas from a repo source provided by the user.

Repo source examples:

- `https://github.com/dagster-io/dagster/pulls`
- `https://github.com/dagster-io/dagster/issues`
- `https://github.com/dagster-io/dagster`
- `dagster-io/dagster`

## Normalize The Source

Convert the user-provided repo source into `owner/repo`.

- For GitHub URLs, parse the first two path segments after `github.com`.
- Treat `/pulls`, `/issues`, `/pull/<number>`, and `/issues/<number>` as source hints, not as part of the repo name.
- If a specific issue or PR URL is provided, inspect that item first.
- If only a list URL or repo is provided, mine several candidates before choosing.

Use `gh` or browsing to verify repository state, issue/PR state, merge status, and fixing commits. Do not rely on memory for GitHub status.

## Candidate Selection

Prefer closed bugs or merged PRs with:

- a real user-visible bug, not a docs-only or maintenance change
- upstream tests added or changed to cover the behavior
- a deterministic local reproduction
- no live credentials, external services, paid APIs, or network needed at runtime
- a fix that touches 2+ interacting subsystems, or a smaller subtle fix with non-obvious behavior
- a parent commit before the fix that builds in Docker without excessive setup
- task scope small enough for one focused debugging task

Reject candidates that are:

- documentation-only, typo-only, dependency bump, CI-only, release metadata, or typing-only
- single-line option validation or obvious error-message changes
- broad migrations or architectural rewrites
- flaky, timing-sensitive, or dependent on unavailable OS services
- only reproducible with a large database, cloud account, broker, cluster, browser farm, or external plugin
- likely solvable by copying a test name, issue title, or one expected string

For Python Hard tasks, the final task should realistically target `difficulty = "hard"`.

## Mining Strategy

Start broad, then narrow:

```bash
gh search prs --repo owner/repo --state closed --merged "bug fix test" --limit 20 --json number,title,url,closedAt
gh search issues --repo owner/repo --state closed "bug regression" --limit 20 --json number,title,url,closedAt,labels
```

For promising PRs:

```bash
gh pr view <number> --repo owner/repo --json number,title,state,mergedAt,mergeCommit,baseRefOid,headRefOid,files,additions,deletions,body
gh pr diff <number> --repo owner/repo
```

For promising issues:

```bash
gh issue view <number> --repo owner/repo --json number,title,state,closedAt,labels,body,comments
```

Prefer PRs where changed files reveal both implementation and upstream regression tests. If starting from an issue, identify the fixing PR or commit before designing the task.

## Hardness Filter

A strong hard candidate usually requires understanding at least two subsystems in the target project. Examples:

- scheduler or orchestration state plus event/log reporting
- config parsing plus runtime execution behavior
- resource lifecycle plus error propagation
- serialization/deserialization plus user-facing CLI/API output
- cache/state persistence plus selection/filtering behavior
- plugin/hook lifecycle plus result reporting

Do not accept a candidate as hard only because the repo is large. The bug itself must force real reasoning.

## Transformation Pattern

1. Identify the closed issue or merged PR and the fixing commit.
2. Choose a parent commit before the fix for `environment/repo`.
3. Clone or stage the repo under `environment/repo`; do not fetch the repo at runtime.
4. Remove upstream tests, changelog entries, issue references, generated metadata, and breadcrumbs that reveal the fix.
5. Write `instruction.md` as user-visible behavior only. Do not mention issue URLs, PR numbers, commit hashes, test names, `solution/`, verifier files, or implementation steps.
6. Put reproducer projects, fixtures, input files, or CLI invocations inside verifier tests, not in the prompt.
7. Write `solution/fix.patch` from the generalized upstream fix, adjusted only as needed for the staged parent.
8. Write `solution/solve.sh` that applies the patch and runs a focused behavioral smoke test.
9. Write behavioral verifier tests that fail on the staged parent and pass after the oracle patch.
10. Run oracle, nop, static checks, and ZIP validation.

Use `task-clone`, `terminus-hard-python-verifier`, `upstream-repo-sanitizer`, `task-harbor-runner`, and `task-zip-submit` as companion skills when the work reaches those phases.

## Prompt Shape

Keep `instruction.md` concise, concrete, and implementation-neutral:

```md
The package in `/app` mishandles <observable scenario>. A user who <normal workflow> currently sees <bad behavior>.

Fix it so `<public command or API>` <required observable result>. The run should still <preserve important behavior>, and <edge case contract>.
```

Only assert exact strings in the prompt if the verifier requires those strings.

## Verifier Guidance

Verifier tests should exercise the target from the outside:

- run the public CLI, API, or Python entry point with `subprocess.run`
- create temporary projects or input files inside the test
- parse structured output with real parsers for JSON, XML, CSV, YAML, or SQLite
- assert return code category, user-facing output, files/state produced, and absence of internal crashes
- include normal-behavior preservation and at least one boundary or anti-shortcut case

Every verifier test function needs a docstring, and every asserted behavior must be stated in `instruction.md`.

## Output When Mining

When presenting candidates, include:

- source repo and issue/PR URL
- merged/closed date and fixing commit if known
- parent commit to stage
- changed implementation files and changed test files
- why it is hard
- offline reproduction plan
- verifier plan
- reject reasons for candidates you considered but skipped

Then pick one candidate and continue into `task-clone` if the user asked to create the task.
