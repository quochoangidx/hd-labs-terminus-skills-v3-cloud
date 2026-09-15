---
name: find-task-prs
description: Scan a GitHub repository's recently merged PRs and return the top ~10 candidates suitable for building tb-quality TerminalBench tasks. Score diffs with the active Claude or Codex runtime, or OpenAI API only when explicitly selected. Use when the user gives a repo URL (or `owner/repo`) and wants to mine it for benchmark-worthy PRs.
---

# Find Task-Worthy PRs

> ⛔ **Minority-lane gate (2026-07-19).** Under the fresh-only mining doctrine
> (AGENTS.md §2) this upstream-PR lane runs only on explicit user request. Its
> typical output shape — reproduce-a-fix / repair — often collapses when the fix
> is mechanical regardless of file spread. Every candidate must pass the
> collapse-law screen and the Terminus 3 domain/subcategory screen before build.

Given a GitHub repo, surface ~10 merged PRs that would make good tb-quality tasks.

## Inputs

- **Repo**: `owner/repo` or full GitHub URL (required)
- Optional: `--limit N` (how many merged PRs to fetch; default 50)
- Optional: `--pick K` (how many to return; default 10)
- Optional `--scorer runtime|openai` (default `runtime`)
- `openai` scoring reads `OPENAI_API_KEY` + `LLM_MODEL` from `.env`

## Steps

### 1. List merged PRs

```bash
gh pr list --repo <owner/repo> --state merged --limit <N> \
  --json number,title,author,mergedAt,additions,deletions,changedFiles,url,labels
```

Filter out obvious non-candidates before scoring (cheap, saves LLM calls):
- `additions + deletions < 20` → too trivial
- `additions + deletions > 5000` → too huge for an LLM to tackle
- Title matches `^(docs|chore|ci|style|typo|bump|release|version)[:\s(]`
- `changedFiles > 50` → sprawling refactor, hard to isolate
- Labels include `documentation`, `dependencies`, `chore`, `release`
- **Already built** → `pr_url` appears in `reports/built-prs.json` (skip silently).
  The file is a JSON array of `{pr_url, task_slug, built_at}` records; treat a
  missing file as an empty list.

Keep candidates (cap at `2 * K`, e.g. 20, to bound scoring work).

### 2. Score each candidate

For each remaining PR, fetch a truncated diff:

```bash
gh pr diff <PR_NUMBER> --repo <owner/repo> | head -500
```

With the default `runtime` scorer, apply this rubric directly in the active
Claude or Codex session and preserve one structured assessment per PR. Do not
claim a separate model call or provider receipt.

Only when the user selects `--scorer openai`, call the OpenAI Responses API
(single request **per PR**, `LLM_MODEL` from `.env`) with this rubric:

```
Rate this merged PR as a candidate for a TerminalBench-style coding task (an
autonomous LLM agent must reproduce the change from a stripped-down state and
pass the original test suite).

Return ONLY JSON, no markdown:
{
  "score": 0-100,
  "difficulty": "easy" | "medium" | "hard" | "expert",
  "has_tests": true | false,
  "self_contained": true | false,
  "scope_summary": "one sentence",
  "why_good": "...",
  "why_bad": "..."
}

High-score PRs (**REQUIRED for a good task**):
- **difficulty must be medium / hard / expert** — `easy` PRs are rejected by the upstream criteria
- include meaningful test changes the agent can be evaluated against
- are self-contained (fixes/features in one subsystem)
- require real reasoning — ideally something where a current frontier LLM would fail or struggle (target pass@5 < 80%)
- are sized medium/hard (medium ~ 50-200 LOC, hard ~ 200-500 LOC, expert > 500 LOC)
- involve non-obvious invariants: concurrency, async bookkeeping, algorithm correctness, cross-module integration, tricky edge cases

Low-score PRs (filter out):
- `easy` difficulty — mechanical tweaks, single-file renames, straightforward one-liners
- docs-only, config bumps, pure dependency updates
- no test coverage for the change
- tightly coupled to external infra that can't run in Docker
- giant refactors or generated-code churn
- anything a current coding LLM would trivially solve in one shot
```

**Hard filter after scoring**: drop any PR with `difficulty == "easy"` before returning the top list — the project's goal is benchmarking challenging tasks only.

Run batched using asyncio or a simple for-loop; show progress (`Scoring 1/20…`) so the user sees it's alive.

For runtime scoring, emit the schema directly. If the optional OpenAI scorer
returns non-JSON, log and skip that PR rather than crashing.

### 3. Rank and present

Sort by `score` descending. Take top `K` (default 10). Display a table:

```
| # | Score | Difficulty | PR                       | Title                          | Why good                     |
|---|-------|------------|--------------------------|--------------------------------|------------------------------|
| 1 |  87   | hard       | owner/repo#1234          | <short title>                  | <one-line why_good>          |
...
```

Include each PR's URL (markdown link).

### 4. Ask user what to do next

Ask the user concisely in the normal response. Use a runtime-native structured
question tool only when it is available in the current mode:

> "Which PR(s) should I turn into tb-quality tasks?"

Options:
- `Top 1` — invoke the `task-clone` skill for #1
- `Pick specific` — prompt for PR numbers
- `All 10 (sequential)` — loop `task-clone` over each
- `Just save the list` — write `reports/<repo-slug>/pr-candidates.md` and stop

### 5. Saving the list (option 4)

When saving, create `reports/<owner>-<repo>/pr-candidates.md` with the table + full rationale per PR. Include the date scanned and the command used so it's reproducible.

## Implementation tips

- Respect GitHub rate limits. `gh pr diff` is one API call each; batching to ~20 is fine on an authenticated `gh` CLI.
- Truncate diffs to `head -500` before scoring — enough signal, bounded tokens.
- If `--scorer openai` was explicitly selected and `.env` has no
  `OPENAI_API_KEY`, abort early with the hint to add it. The default runtime
  scorer never requires that key.
- If the repo is huge and rate limits hit, report partial results instead of failing — tell the user how many PRs were actually scored.
- Do NOT create task folders in this skill; that's what `task-clone` is for. Keep this skill read-only (plus the optional summary file).
