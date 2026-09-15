# Terminus task-authoring skills — project purpose & pipeline map

**Purpose.** This repo produces Terminus 3 tasks for the Snorkel platform:
self-contained, deterministic, multi-step domain work with a Python-pytest
verifier running in a separate container. All seven Terminus 3 categories are
open. Tasks use one exact category/subcategory pair and the empirical tiers
Frontier, Advanced, Core, or Base; difficulty is language-independent.

## Pipeline → skill map

`task-batch` is the autonomous end-to-end orchestrator entry point — it runs the full
gate pipeline below (fresh-only mining → optional exploratory screen → full build → V3 evidence +
mutation-backed semantic coverage → exact-Docker Oracle/NOP + pre-freeze review/style → frozen
counted probe → full validation + submission audit → package) without further prompting. Tooling: `scripts/new-task.sh <slug>
<lang> <category> <subcategory>` stamps a hygiene-pre-wired skeleton; `scripts/preflight.sh <task-dir>`
machine-checks the mechanical gates before every zip.

Run repository Python helpers through `scripts/python3`; it selects Python
>=3.11 consistently for Claude Code, Codex, and direct shell use. Set
`TERMINUS_PYTHON` only when an explicit interpreter override is needed.

| Stage | Skill(s) |
|---|---|
| 1. Mine candidates (metadata only) | `task-miner` (+ `find-task-prs` for the PR lane); rules-first category gate via `task-miner/category_rules.md` before any build |
| 2. Build and prove semantic coverage | `task-clone` (+ `upstream-repo-sanitizer` for repo staging; `issue-to-regression-test`, `terminus-hard-python-verifier` for verifiers; `terminus-regular-task-authoring` for V3 inferability, semantic coverage, layout, and prompt rules; `terminus-rust-task-authoring` for Rust) |
| 3. Prove pre-freeze validity | Strict exact-Docker Oracle/NOP/noexec preflight, folder-level `task-client-feedback-review`, task-tree phase of `task-llm-style-audit`, then the shared pre-probe receipt gate |
| 4. Freeze and probe | Hash-bind the completed Step 2/3 receipts, then run counted `task-local-solve-probe`; exploratory runs never qualify a tier |
| 5. Harden, audit, and package | `task-harbor-runner` for full integration checks; `terminus-rubric-authoring` for contract-witness coverage and a hash-bound rubric receipt; submission-only `task-llm-style-audit`; exact-ZIP `task-client-feedback-review`, `task-zip-validator`, and `task-zip-submit` |
| 6. Remediate a platform return | `task-revise-flag-remediation` (all six trial-analysis flags, reviewer feedback, and 0/N solvability), `terminus-regular-task-authoring` V3 evidence-inferability gate |
| 7. Migrate an existing task to another runtime | `task-language-port` (explicit request only; internal/replacement use, never a separate reskinned submission) |
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
  pattern, not the resource"). The default lane is the fresh-only doctrine;
  language ports and narrative reskins are not novel Terminus 3 tasks.
- `.agent/skills/task-miner/category_rules.md` — domain-first Terminus 3
  category/subcategory screen and evidence schema.
- `.agent/skills/task-miner/interaction_shape_recipe.md` — interaction/scale shape
  recipe (open Terminus 3 candidate shape; old canonical restoration/migration
  results are negative priors, not a blanket closure).

## Non-negotiable invariants

Top-level `artifacts`, `[verifier].environment_mode = "separate"`, a digest-pinned
`tests/Dockerfile` with all verifier dependencies and artifact landing directories,
`[environment].network_mode = "public"` plus explicit `[agent]` and `[verifier]`
network modes, agent timeout 1800–18000 seconds, no GPU,
roughly 2 CPU / 8 GB / 10 GB, oracle passes and nop fails for the intended reason,
no tests/solution/answer keys reachable from `environment/`, and difficulty is
claimed only from model-run evidence — never from ambiguity, build time, repo size,
or timeouts.

Fairness means a clear goal and enough visible evidence to infer the graded
domain model. Keep paths, public schema/interface, safety constraints, and
arbitrary exact conventions explicit. Hidden instances and combinations are
valid; oracle-only policies and unobtainable facts are not. New/revised tasks
use `schema_version: 3` in the compatibility-named
`workspace/reports/<slug>/instruction-sufficiency.json` report.

Counted probes also require a frozen `semantic-coverage.json`: every promised
public surface is tested; Advanced+ targets have at least three independent
mechanisms and two interactions; each node has a killed executable partial-fix
mutant. Fixture multiplication does not add semantic rank, and a `1/3` result
from one replicated lever is not Advanced.

## Editing rules for this directory

Skills live ONLY here; `.claude/skills`, `.codex/skills`, `.gemini/skills`, and
`.cline/skills` are symlinks to `.agent/skills` — never fork a copy. Claude-only
agent launch profiles may live in `.claude/agents/` when Claude's Agent API
cannot express a required control per call; policy still remains in the shared
skill. Battle-tested lessons get codified into the
relevant SKILL.md (dated, with the incident), not left in personal memory; when a rule
must exist in two files (for example category availability), each copy names its mirror.
