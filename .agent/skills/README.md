# Terminus task-authoring skills — project purpose & pipeline map

**Purpose.** This repo produces Terminus 3 tasks for the Snorkel platform:
self-contained, deterministic, multi-step domain work with a Python-pytest
verifier running in a separate container. All seven Terminus 3 categories are
open. Tasks use one exact category/subcategory pair and the empirical tiers
Frontier, Advanced, Core, or Base; difficulty is language-independent.

## Pipeline → skill map

| Stage | Skill(s) |
|---|---|
| 1. Mine candidates (metadata only) | `task-miner` (+ `find-task-prs` for the PR lane) |
| 2. Build the task | `task-clone` (+ `upstream-repo-sanitizer` for repo staging; `issue-to-regression-test`, `terminus-hard-python-verifier` for verifiers; `terminus-regular-task-authoring`, `terminus-rust-task-authoring` for layout/prompt rules) |
| 3. Probe difficulty cheaply | `task-local-solve-probe` (before any Harbor LLM spend) |
| 4. Validate | `task-harbor-runner` (oracle / nop / `stb harbor check` / real-agent runs) |
| 5. Review & package | `task-client-feedback-review`, `task-llm-style-audit` (LLM-tell audit + re-author of all prose surfaces, last step before zip), `task-zip-validator`, `task-zip-submit` |
| 6. Remediate a platform return | `task-revise-flag-remediation` ("Some tests not passed by any agent run" / 0/N coverage flag), `terminus-regular-task-authoring` Prompt Rules (instruction_check + disclosure ladder) |
| 7. Port an existing task to new languages | `task-language-port` (feasibility screen, mandatory narrative reskin, faithful placeholder+solution translation, re-validation) |
| 8. Maintenance | `sync-doc-and-skill` (portal-doc drift), `anti-llm` (editorial pass) |

Handoff between stages is the **mined-candidate artifact** (`mined-candidates/<slug>.json`
+ a claim line in `index.jsonl`) — clone consumes it and must not re-mine.

## Sources of truth (read BEFORE mining or building)

- `mined-candidates/index.jsonl` — team claim/dedupe registry (incl. the
  `conformance_suite + spec + language` key for the L1 lane).
- `mined-candidates/gallery_tasks_snapshot.md` — novelty gate against the live gallery.
- `docs/understanding-tasks/task-taxonomy.md` — authoritative Terminus 3
  category/subcategory menu.
- `.agent/skills/task-miner/lever_patterns.md` — lever catalog **L1–L4** (conformance
  suite, synthetic interval-invariant ledger, differential-vs-authority, multi-vector
  security), claimed-resource ledger, and the complete L1 build runbook ("learn the
  pattern, not the resource").

## Non-negotiable invariants

Top-level `artifacts`, `[verifier].environment_mode = "separate"`, a digest-pinned
`tests/Dockerfile` with all verifier dependencies and artifact landing directories,
`network_mode = "public"` by default, agent timeout 1800–18000 seconds, no GPU,
roughly 2 CPU / 8 GB / 10 GB, oracle passes and nop fails for the intended reason,
no tests/solution/answer keys reachable from `environment/`, and difficulty is
claimed only from model-run evidence — never from ambiguity, build time, repo size,
or timeouts.

## Editing rules for this directory

Skills live ONLY here; `.claude/skills`, `.codex/skills`, `.gemini/skills` are symlinks
to `.agent/skills` — never fork a copy. Battle-tested lessons get codified into the
relevant SKILL.md (dated, with the incident), not left in personal memory; when a rule
must exist in two files (for example category availability), each copy names its mirror.
