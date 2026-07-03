# Terminus task-authoring skills — project purpose & pipeline map

**Purpose.** This repo produces Terminus-2nd-Edition **Regular tasks** for the Snorkel
platform, aligned to the live task gallery (`/portal/tasks`): self-contained, offline,
deterministic problems with a Python-pytest verifier, targeting **Hard or Medium by
MODEL PASS RATE** (Easy is blocked; Python tasks must be Hard). The default lane is
gallery-style spec-driven work (Lane A); upstream bugfix PRs are a minority lane.
`debugging` and `software-engineering` categories are ON HOLD (see the mirrored
callouts in task-miner + task-clone — lift both together).

## Pipeline → skill map

| Stage | Skill(s) |
|---|---|
| 1. Mine candidates (metadata only) | `task-miner` (+ `find-task-prs` for the PR lane) |
| 2. Build the task | `task-clone` (+ `upstream-repo-sanitizer` for repo staging; `issue-to-regression-test`, `terminus-hard-python-verifier` for verifiers; `terminus-regular-task-authoring`, `terminus-rust-task-authoring` for layout/prompt rules) |
| 3. Probe difficulty cheaply | `task-local-solve-probe` (before any Harbor LLM spend) |
| 4. Validate | `task-harbor-runner` (oracle / nop / `stb harbor check` / real-agent runs) |
| 5. Review & package | `task-client-feedback-review`, `task-zip-validator`, `task-zip-submit` |
| 6. Remediate a platform return | `task-revise-flag-remediation` ("Some tests not passed by any agent run" / 0/N coverage flag), `terminus-regular-task-authoring` Prompt Rules (instruction_check + disclosure ladder) |
| 7. Maintenance | `sync-doc-and-skill` (portal-doc drift), `task-miner/refresh_gallery_taxonomy.py` (taxonomy, ~weekly), `anti-llm` (editorial pass) |

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
  pattern, not the resource").

## Non-negotiable invariants

Offline (`allow_internet = false`), 2 CPU / 4 GB, `environment/` ≤ 100 MiB, verifier =
`python3` pytest writing `/logs/verifier/reward.txt` within 450s, oracle passes /
nop fails for the intended reason, no tests/solution/answer keys reachable from
`environment/`, and difficulty is claimed only from blind-probe or platform agent
evidence — never from build time, repo size, or timeouts.

## Editing rules for this directory

Skills live ONLY here; `.claude/skills`, `.codex/skills`, `.gemini/skills` are symlinks
to `.agent/skills` — never fork a copy. Battle-tested lessons get codified into the
relevant SKILL.md (dated, with the incident), not left in personal memory; when a rule
must exist in two files (e.g. the category hold), each copy names its mirror.
