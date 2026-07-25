# Terminus task-authoring skills — project purpose & pipeline map

**Purpose.** This repo produces Terminus-2nd-Edition **Regular tasks** for the Snorkel
platform, aligned to the live task gallery (`/portal/tasks`): self-contained, offline,
deterministic problems with a Python-pytest verifier, targeting **Hard or Medium by
MODEL PASS RATE** (Easy is blocked; Python tasks must be Hard). The default lane is
the fresh-only mining doctrine (100% NEW tasks; ports only on explicit request), with
the bd-mgmt seam and interaction/scale shapes as priority lanes — upstream bugfix PRs
are a minority lane. `debugging` and `software-engineering` categories are BLOCKED
(rejected by an automated eval check as of 2026-06-29), `data-processing` is ALSO
BLOCKED (enforced since 2026-07-10/11), and new milestone tasks are also blocked
— see the mirrored callouts in task-miner + task-clone (lift both together).

## Pipeline → skill map

`task-batch` is the autonomous end-to-end orchestrator entry point — it runs the full
gate pipeline below (fresh-only mining → collapse-law screen → skeleton probe → build →
validate → package) without further prompting. Tooling: `scripts/new-task.sh <slug>
<lang> <category>` stamps a hygiene-pre-wired skeleton; `scripts/preflight.sh <task-dir>`
machine-checks the mechanical gates before every zip.

| Stage | Skill(s) |
|---|---|
| 1. Mine candidates (metadata only) | `task-miner` (+ `find-task-prs` for the PR lane); rules-first category gate via `task-miner/category_rules.md` before any build |
| 2. Build the task | `task-clone` (+ `upstream-repo-sanitizer` for repo staging; `issue-to-regression-test`, `terminus-hard-python-verifier` for verifiers; `terminus-regular-task-authoring`, `terminus-rust-task-authoring` for layout/prompt rules) |
| 3. Probe difficulty cheaply | `task-local-solve-probe` (before any Harbor LLM spend) |
| 4. Validate | `task-harbor-runner` (oracle / nop / `stb harbor check` / real-agent runs) |
| 5. Review & package | `task-client-feedback-review`, `task-llm-style-audit` (LLM-tell audit + re-author of all prose surfaces, last step before zip), `task-zip-validator`, `task-zip-submit` |
| 6. Remediate a platform return | `task-revise-flag-remediation` ("Some tests not passed by any agent run" / 0/N coverage flag), `terminus-regular-task-authoring` Prompt Rules (instruction_check + disclosure ladder) |
| 7. Port an existing task to new languages | `task-language-port` (feasibility screen, mandatory narrative reskin, faithful placeholder+solution translation, re-validation) |
| 8. Maintenance | `sync-doc-and-skill` (portal-doc drift), `task-miner/refresh_gallery_taxonomy.py` (taxonomy, ~weekly), `anti-llm` (editorial pass) |

Handoff between stages is the **mined-candidate artifact** (`mined-candidates/<slug>.json`
+ a claim line in `index.jsonl`) — clone consumes it and must not re-mine.

## Sources of truth (read BEFORE mining or building)

- `mined-candidates/index.jsonl` — team claim/dedupe registry (incl. the
  `conformance_suite + spec + language` key for the L1 lane).
- `mined-candidates/gallery_tasks_snapshot.md` — novelty gate against the live gallery.
- `mined-candidates/gallery_taxonomy.md` — category/subtype menu; refresh if the
  snapshot date is older than ~7 days.
- `.agent/skills/task-miner/lever_patterns.md` — lever catalog **L1–L4** (conformance
  suite, synthetic interval-invariant ledger, differential-vs-authority, multi-vector
  security), claimed-resource ledger, and the complete L1 build runbook ("learn the
  pattern, not the resource"). Note the default lane is now the fresh-only doctrine
  (task-miner, "Fresh-only exploration doctrine"); the historical bd-mgmt seam is
  currently blocked for net-new submissions, so mine only the three open categories.
  interaction/scale shapes as priority lanes — not gallery-style spec-driven L1.
- `.agent/skills/task-miner/category_rules.md` — rules-first category gate
  (deterministic BLOCK/ALLOW rules calibrated on real-CI verdicts; run before
  trusting any blind category probe).
- `.agent/skills/task-miner/interaction_shape_recipe.md` — interaction/scale shape
  recipe (≥3 coupled causes + discovery breadth; escapes the master collapse law).

## Non-negotiable invariants

Offline (`allow_internet = false`) is the default, but retain `allow_internet = true` when network access is the task's point; hard-pin each live source by exact version and immutable digest/hash, then grade stable invariants rather than mutable responses. Keep 2 CPU / 4 GB, `environment/` ≤ 100 MiB, verifier =
`python3` pytest writing `/logs/verifier/reward.txt` within 450s, oracle passes /
nop fails for the intended reason, no tests/solution/answer keys reachable from
`environment/`, and difficulty is claimed only from blind-probe or platform agent
evidence — never from build time, repo size, or timeouts.

## Editing rules for this directory

Skills live ONLY here; `.claude/skills`, `.codex/skills`, `.gemini/skills` are symlinks
to `.agent/skills` — never fork a copy. Battle-tested lessons get codified into the
relevant SKILL.md (dated, with the incident), not left in personal memory; when a rule
must exist in two files (e.g. the category hold), each copy names its mirror.
