---
name: task-batch
description: "Use when the user sends `task-batch N` or `/task-batch N`, where N is a positive integer, to autonomously create exactly N brand-new Terminus 3 tasks ready for platform iteration. Run task-miner, task-clone, separate-verifier Oracle/NOP validation, task-zip-submit, task-client-feedback-review, adaptive task-local-solve-probe runs, and task-llm-style-audit. Do not use for ports, returned-task remediation, or ordinary single-task work."
---

# Task Batch

Create a fresh autonomous batch of submit-ready Terminus Regular tasks.

## Invocation

Accept either form:

```text
task-batch N
/task-batch N
```

Treat `N` as the required delivery quota. It must be a positive integer.

## Advanced+ Campaign Profile

When the user asks for only Advanced/Frontier tasks, activate
`advanced_frontier_only`. The current repository campaign has this profile
active by user decision (2026-08-13).

This profile adds a stricter selection stage to the general submit-ready path:

- `N` still counts only final `candidate_ready` tasks whose ZIP, preflight,
  review, and handover gates pass. `advanced_plus_shortlist` is an intermediate
  state and never increments the delivery quota.
- Use a **counted frozen-snapshot** blind probe as the selection gate. Before
  preparing it, finish the verifier/oracle, public-surface audit, V3 evidence
  audit, mutation-backed semantic coverage receipt, and exact-Docker
  Oracle/NOP/noexec pre-probe receipt. Full Harbor checks, final ZIP review, and
  submission hardening remain after shortlist selection. An exploratory skeleton probe can
  reject an idea cheaply but can never qualify it or increment `N`.
- Start with two fresh runs. A `1/2` split is unresolved and MUST receive the
  adaptive third run. Keep `1/3` as provisional Advanced only when both failing
  runs cross at least two semantic nodes and their failed-node sets differ; a
  repeated single lever multiplied across fixtures is rejected. Keep `0/2` or `0/3`
  as provisional Frontier only when semantic failures are de-correlated,
  per-case union is 100%, common misses are empty, and the V3
  evidence-inferability audit passes. Here, 100% union mirrors the platform's solvability rule. The
  de-correlation/common-miss checks are conservative local confidence checks
  for a zero-solve Frontier claim, not platform tier criteria and not a rule
  that failures must be distributed across clusters.
- Reject `2/3` (Core), `2/2` (all-pass/no local signal), Base, and Core results
  from this campaign and mine replacements. Preserve the truthful evidence;
  never prune passing cases or hide contract facts to move a task upward.
- Report these as `advanced_plus_shortlist` candidates with a provisional local
  tier. Never call them `candidate_ready`, submit-ready, or platform-confirmed
  until the deferred full validation path has actually passed.

Under this profile, use `task-miner`, `task-clone`,
`terminus-regular-task-authoring`, and `task-local-solve-probe` for the
selection loop, then use the remaining validation and packaging skills for
every shortlisted candidate before it can count toward `N`.

When invoked:

- Do not ask the user to choose repositories, languages, categories, candidates, or fixes.
- Make all normal task-building decisions autonomously.
- Deliver exactly `N` accepted tasks.
- Use any suitable implementation language, including Python when it fits.
- Build a useful Terminus 3 difficulty mix. Preserve valid Base/Core candidates;
  do not force every task toward Frontier.
- Under `advanced_frontier_only`, this general mix rule is superseded: preserve
  lower-tier evidence, but do not count Base/Core candidates toward `N`.
- Keep mining replacements until the quota is met.
- Treat every invocation as a fresh batch. Do not port, reskin, or reuse an existing task unless the user explicitly requests that separately.

## Adaptive Candidate Design Portfolio

Design each candidate from its domain-native failure mode, work surface, and
deliverable before consulting the pattern catalog. Extract the causal graph and
failure geometry, then classify the completed design:

- `established` applies one dominant `P*` topology, with at most one orthogonal
  secondary topology and one P4/P6 amplifier or envelope.
- `derived` creates an `X-*` topology by transforming or composing established
  parents across at least two structural axes. Domain, language, repository,
  narrative, or file-format changes alone remain reskins.

Do not preassign immutable task slots. Record every mining-plan-qualified
attempt, including later rejections, against the explicit user candidate
budget. Use roughly 20–30% derived attempts as a non-blocking exploration band
when the budget permits. A rejection may be followed by either track, and the
first task that clears every gate may be accepted regardless of track.

Guide future mining with the rolling five accepted tasks: aim for one or two
derived tasks, no dominant topology above three of five, and no exact role stack
three times consecutively. Portfolio drift changes priority; it never blocks
handover or justifies relabelling a candidate.

Save a schema-v3
`workspace/reports/batches/<batch-id>-pattern-mix.json`. Validate it with
`--allow-partial` before scaffolding and without that flag at final handover:

```bash
python3 .agent/skills/task-batch/scripts/design_pattern_mix_check.py \
  workspace/reports/batches/<batch-id>-pattern-mix.json --allow-partial
```

Manifest shape:

```json
{
  "schema_version": 3,
  "batch_id": "<batch-id>",
  "expected_count": 1,
  "candidate_budget": 6,
  "portfolio_history": [],
  "accepted_task_slugs": [],
  "candidates": [
    {
      "task_slug": "tbrain-example",
      "classification_timing": "post_crux",
      "disposition": "active",
      "track": "established",
      "pattern_ids": ["P1", "P4"],
      "domain_crux": {
        "failure_mode": "<natural domain failure>",
        "native_work_surface": "<real work surface>",
        "native_artifact_or_behavior": "<graded native outcome>",
        "difficulty_without_incidental_conventions": "<remaining intrinsic challenge>"
      },
      "convention_audit": {
        "status": "pass",
        "assertion_to_source_complete": true,
        "arbitrary_conventions": []
      },
      "source_smoke": {
        "status": "pass",
        "receipt": "<receipt path>",
        "runtime_entrypoint": "<minimal verifier entrypoint smoke>",
        "verifier_dependencies": ["<runtime>", "pytest"],
        "unprivileged_candidate_execution": true
      },
      "structural_signature": {
        "causal_topology": "<topology>",
        "work_surface": "<surface>",
        "verifier_architecture": "<architecture>",
        "failure_geometry": "<geometry>",
        "difficulty_source": "<source>",
        "artifact_type": "<artifact>"
      },
      "pattern_fit_evidence": {},
      "frontier_stability": {
        "dominant_topology_id": "P1",
        "secondary_topology_id": null,
        "amplifier_or_envelope_id": "P4",
        "planned_mechanism_ids": ["planner-rule", "stats-refresh", "preservation"],
        "planned_interaction_ids": ["plan-stats", "refresh-preservation"],
        "retrieval_audit": {
          "search_queries": ["issue wording", "failure symbol", "release version diff"],
          "public_artifacts_checked": ["<URLs/commits checked>"],
          "exact_solution_found": false,
          "satisfied_mechanism_ids": [],
          "satisfied_interaction_ids": [],
          "disposition": "pass"
        },
        "orthogonal_traps": [
          {"id": "trap-a", "semantic_node": "planner-rule", "repair_surface": "planner.rule", "natural_implementation": "<reasonable local fix>", "why_wrong": "<semantic counterexample>", "witness_ids": ["interaction-a"]},
          {"id": "trap-b", "semantic_node": "stats-refresh", "repair_surface": "stats.refresh", "natural_implementation": "<different reasonable fix>", "why_wrong": "<different counterexample>", "witness_ids": ["interaction-b"]}
        ],
        "shared_fix_rationale": "<why one helper or mapping cannot repair both>"
      },
      "causal_graph": {"nodes": ["planner", "statistics"], "edges": ["planner->statistics"]},
      "non_equivalence_rationale": "<why this is not a prior instance>",
      "closest_portfolio_pattern_instance": "<slug or none>"
    }
  ]
}
```

A derived entry uses the same domain-first evidence and `frontier_stability`
object, sets
`dominant_topology_id` to its own `X-*` ID, and may use an applied parent `P*`
as the secondary or `P4`/`P6` amplifier slot.

Only a candidate that passed taxonomy, novelty, anti-retrieval, domain crux,
convention symmetry, canonical source/runtime smoke, topology, and verifier-plan
gates counts toward the candidate budget. Raw ideas and early taxonomy failures
do not count. Pattern membership never substitutes for semantic rank, fairness,
mutation coverage, or empirical difficulty evidence.

## Required Skills

Read each relevant `SKILL.md` completely before using that stage:

1. `task-miner`
2. `task-clone`
3. `terminus-regular-task-authoring` and any required language-specific skill
4. `task-client-feedback-review`
5. `task-llm-style-audit`
6. `task-local-solve-probe`
7. `task-harbor-runner`
8. `task-zip-submit`

This file controls the batch policy when it is more specific than a dependent
skill. Read
[`references/quota-efficient-workflow.md`](references/quota-efficient-workflow.md)
before launching any role. Pin candidate design and builder work to
`gpt-5.6-sol` medium, fairness reviewers to `gpt-5.6-luna` high, the
consolidated auditor to `gpt-5.6-luna` max, and counted blind solvers to
`gpt-5.6-sol` medium.
Run the Luna roles as independent Codex tasks by following
[`references/luna-thread-orchestration.md`](references/luna-thread-orchestration.md);
do not request Luna through the collaboration-subagent runtime. A
`task-batch N` invocation authorizes these visible reviewer/auditor tasks.
Record the actual model and fail closed when a requested profile is unavailable;
never silently substitute Terra or claim an unavailable pin.
Before launching a builder, also follow
[`references/builder-quota-hooks.md`](references/builder-quota-hooks.md).
Validate both repository-local agent hook configurations, create the
stage-specific hash-bound context packet, and open the lease for the exact
builder subagent type. Stage A ends after mining plus canonical-image source
smoke. Transition to scaffolding only before a new counted follow-up. Poll the
lease during waits and interrupt at its deadline; hooks cannot interrupt an
in-flight model request by themselves.
Before creating Luna fairness/auditor tasks, follow
[`references/review-role-quota-hooks.md`](references/review-role-quota-hooks.md).
Create a hash-bound role packet, open exactly two reviewer leases or one
auditor lease, then create only that cohort until every session is claimed.
Poll role deadlines during waits. Reviewer/auditor tasks are read-only; one
re-review/re-audit cycle is the maximum, and the same auditor task must be
transitioned to `post_probe`. Bind the three final lease receipts into the
quota ledger before pre-solver and handover validation.

## Truthfulness Rules

- Never claim that a command, validation, review, or probe ran without its real output and exit status.
- Never invent a subagent, model name, transcript, run ID, score, diff, or test result.
- Record the actual model reported by each probe environment when available.
- Treat setup, Docker, tool, dependency, timeout, and compilation failures as infrastructure failures, not evidence of task difficulty.
- Do not mark a task submit-ready while a required local check is blocked.
- Harbor API-key-dependent LLM-agent runs are not required. Local Docker build, Oracle, NOP, and non-API Harbor checks are required.
- If external infrastructure is unavailable, continue every safe independent step, preserve the artifacts, and report the exact blocker. Never fabricate completion to satisfy the quota.
- Treat `scripts/batch-handover.py` as the only authority allowed to emit
  `candidate_ready`. A prose checklist, a successful ZIP command, or copied
  terminal output cannot increment the accepted-task counter.
- Evidence is immutable and snapshot-bound. Preserve raw logs, CTRF, diffs,
  agent/reviewer transcripts, runtime/model/session provenance, and SHA-256
  digests. Any task or submission change invalidates dependent receipts.

## Fixed Agent Budget, Turn Budget, and Role Separation

An accepted task uses exactly **6–7 role sessions**, but the quota guard counts
every model turn, including follow-ups, failures, interruptions, usage-limit
stops, and reuses of an existing role identity. The per-candidate cap is 12
external model turns. A role-session count alone is not quota evidence.

| Role | Sessions | Scope |
|---|---:|---|
| Builder | 1 | deep mining, authoring, Oracle, verifier, semantic-manifest draft, and all pre-freeze fixes |
| Fairness reviewers | 2 | independent V3 task-visible review only |
| Consolidated auditor | 1 | semantic realism, client/manual folder review, and task-tree style audit; reused post-probe |
| Blind solvers | 2–3 | two initial fresh solves plus one adaptive solve only when triggered |

The builder never performs fairness review or a blind solve. The builder and
blind solvers use Sol collaboration subagents. The two fairness reviewers use
separate Luna-high Codex tasks and receive only `instruction.md` and the
agent-visible environment and evidence; run them concurrently in distinct
fresh tasks. One independent Luna-max Codex task performs the three pre-freeze
auditor judgments. Keep three separate receipts, but give their
semantic `review`, folder `manual_review`, and task-style `auditor` records the
same real runtime/model/session/transcript provenance.

The design/build agent is not fresh-context. Keep one persistent informed
Sol-medium builder session. Before choosing a candidate, make it read the
durable campaign memory, current batch portfolio, and relevant rejection/probe
reports, then record and hash-bind the pattern-blind domain-crux card. Only
after that may it read the frontier pattern catalog to classify the design or
derive a structural transformation. Send fairness/auditor findings back to
that same builder. Require a finding-by-finding critique receipt (`accept`,
`challenge`, or `partial`, with evidence and action) before remediation. Never
leak this builder context into the fresh fairness reviewers or blind solvers.

Run deterministic prompt/scanner/isolation/anti-cheat/artifact-independence
gates before launching the fairness pair. Allow at most one fairness
remediation cycle and one auditor remediation cycle; reject the candidate if
the same gate still fails. Before blind solvers, run `quota_guard.py --phase
pre-solver` to verify role routing, completed review gates, lease provenance,
and remediation caps. There is no fixed per-candidate model-turn cap or
pre-solver turn reserve; honor only explicit user batch-wide budgets and the
role-specific deadline/tool limits.

Launch the first two blind solvers concurrently on separate solve copies. Wait
for both to finish, then materialize, execute the verifier, collect CTRF, and
record each run sequentially. Add solver 3 only for `1/2`, a shared blind spot,
or incomplete union. Reuse the consolidated auditor thread in a new post-probe turn
for submission prose, exact final ZIP review, and metadata/handover surfaces;
the final transcript must bind the final artifacts, while runtime/model/session
identity stays the same.

Do not create separate specialist agents for static scanning, prose inventory,
mutation execution, packaging, or handover. The orchestrator runs deterministic
tools and the fixed roles supply the required judgments. A candidate rejected
at mining or the smoke gate should consume zero or one builder session, never a
full review/solve cohort. Excluding the builder, an accepted task therefore
uses exactly 5–6 external sessions; a two-task accepted batch uses 12–14 role
sessions.

Safe concurrency: different-domain idea cards/builders in separate worktrees,
each fairness pair, each initial solver pair, and static scanning alongside
prose inventory. Different Luna cohorts require separate worktrees and lease
directories; do not let unclaimed review leases compete for `SessionStart`. Run
Docker builds for one task, Oracle/NOP/noexec, shared-image mutation runs,
solver verifier executions, final packaging, and handover sequentially.

Only one builder lease may be active in a shared worktree. Parallel builders
must use separate worktrees and separate lease paths; otherwise their task
trees, Docker state, and hook ownership are not safely isolated.

## Preflight

Before mining:

1. Confirm the workspace and output directories.
2. Confirm Docker is reachable.
3. Confirm the local Terminus/Harbor tooling needed for Oracle and NOP runs is available.
4. Confirm repository mining access is available.
5. Inspect existing workspace and submission slugs so the batch cannot overwrite or duplicate them.
6. Confirm the Codex task tools and Luna-high/Luna-max profiles required by
   `references/luna-thread-orchestration.md`; resolve the current project ID.

Stop early only for a real external blocker that prevents all useful progress. Otherwise continue autonomously.

## Batch Loop

Maintain an accepted-task counter. Repeat the following workflow until the counter equals `N`.

Both profiles execute `1 → 2 → 3 → 4 → 5 → 6 → 7`. The Advanced+ profile
uses Step 5 as a selection gate, but the technical validity checks in Step 3
always happen first. Only the final handover in Step 7 increments the counter.
Handover each finished task immediately using the incremental batch index. A
later task is screened against every earlier accepted task; on a diversity
collision, reject the new task. When the index reaches `N`, seal the complete
batch index and adaptive candidate ledger mechanically. Do not rerun fairness reviews or
blind solves for unchanged task snapshots merely because a peer was added.

### 1. Mine a Fresh Candidate

Use `task-miner`.

The candidate must:

- use a domain-appropriate implementation language;
- be brand-new and gallery-novel;
- fit one exact Terminus 3 category/subcategory pair;
- have a fair goal and enough evidence under its declared `network_mode` to
  infer the graded model; the verifier itself remains deterministic and
  self-contained;
- have enough independent behavioral depth to plausibly resist a strong agent;
- avoid saturated task families, lane-matched collapse patterns, oracle-only
  policies, unobtainable facts, and unreachable authorities; discoverable
  hidden requirements and held-out combinations are allowed;
- declare a verifier architecture profile and budget: 50–1000 visible units
  across at least six clusters for `cheap_deterministic`, or 20–80 scenarios
  across at least four clusters for `expensive_stateful`, with at least two
  cross-cluster scenarios and coverage of every promised public surface;
- record its source repository, base commit, task contract, category, language, and novelty evidence;
- define the pattern-blind domain crux and pass the convention/assertion audit
  before assigning its `established` or `derived` classification;
- pass the schema-v3 frontier-stability gate: one dominant topology, a recorded
  anti-retrieval search, and at least two orthogonal natural-but-wrong traps
  with distinct semantic nodes/repair surfaces and disjoint witnesses. Reject
  when one public artifact covers two planned mechanisms or any interaction;
  use an upstream fix only as substrate for a materially new topology;
- pass the canonical-image source/runtime/entrypoint smoke before it is added
  to the candidate ledger and before Stage B begins.

Save the mined artifact and pass
`verifier_architecture_check.py plan <candidate.json>` before scaffolding.
Reject weak or thin candidates before building. Do not fill quota with ports or cosmetic variants.

Maintain `workspace/reports/<slug>/design-signature.json` for one batch ID. It
must include a unique `domain_key`, a unique `architecture_family`, and all six
structural axes. Compare every qualified attempt against accepted, shortlisted,
and rejected qualified attempts in this invocation. Consecutive attempts must
differ on at least two axes; reject duplicate domain keys/families, a pair
matching more than four axes, a third consecutive dominant topology, or a third
consecutive exact role stack. Surface category/language changes do not clear
this gate.

Maintain one shared `workspace/reports/batches/<batch-id>.json`:

```json
{
  "schema_version": 2,
  "status": "building",
  "batch_id": "<batch-id>",
  "expected_count": 2,
  "task_slugs": ["tbrain-one", "tbrain-two"]
}
```

Set `expected_count` to the requested `N`, not always 10. While building, append
each individually ready task and keep `status: "building"`; `task_slugs` may
contain 1..N accepted tasks. Each listed task's `compared_against` must equal
the current list minus itself. At N, set `status: "complete"`. The batch gate
recomputes domain-key/family uniqueness and every pair's six-axis distance.

Maintain the schema-v3 sibling candidate ledger independently of the accepted
prefix. Append every mining-plan-qualified attempt and preserve its final
`active`, `rejected`, or `accepted` disposition. Use
`design_pattern_mix_check.py --allow-partial` before scaffolding and while the
batch is building; at N, list exactly the accepted slugs and run the strict
default. The strict gate validates evidence and the accepted subset, not an
exact track allocation. A replacement may use either track. Schemas v1–2 remain
readable only for historical evidence; never create a new legacy manifest.

Record every design input and SHA-256 under the builder's `report_inputs` in
`quota-ledger.json`. Initial design/build requires durable-memory,
pattern-catalog, and batch-portfolio inputs; add relevant prior-rejection
reports when available.

### 2. Clone and Build the Task

Use `task-clone` to create the task under `workspace/tasks/tbrain-<slug>/`.

Scaffold the task and build the agent-visible contract plus verifier skeleton:

- `instruction.md`
- `task.toml`
- `environment/`
- `tests/`
- any required local references or fixtures

Keep the task's domain aligned with its exact category/subcategory pair. Python
used only by the verifier is not an implementation language.

Before expanding to the full verifier breadth, implement 6–10 discriminating
witnesses that cover the proposed mechanisms, interactions, and arbitrary
conventions. Run the assertion-to-source audit against those witnesses. Reject
or narrow the candidate now if the contract, Oracle model, and observable
assertions cannot be made symmetric; do not multiply an unresolved convention
into dozens of fixtures.

Build the verifier skeleton before the Oracle. Collect the exact
platform-visible IDs and create `workspace/reports/<slug>/verifier-matrix.json`,
then run:

```bash
python3 .agent/skills/terminus-regular-task-authoring/scripts/verifier_architecture_check.py \
  matrix workspace/reports/<slug>/verifier-matrix.json \
  --task-slug <slug> --allow-missing-ctrf
```

If this fails, redesign the verifier or drop the candidate immediately. Do not
write the Oracle, build Docker images, run Oracle/NOP, or spend a solve probe on
it. Unit multiplication cannot repair missing mechanisms or interactions.

After the breadth gate passes, the same builder finishes `solution/` and runs a
cheap Oracle/NOP smoke cycle before any fairness review, mutation campaign, or
consolidated audit. Reject broken/thin candidates here. Add the raw
Oracle CTRF path and SHA-256 to `verifier-matrix.json`, then rerun the same
command without `--allow-missing-ctrf`. The CTRF IDs must exactly equal the
declared behavior plus non-behavior IDs.

Before launching fairness reviewers, run the five mechanical gates in
`references/quota-efficient-workflow.md`: instruction preflight, client
scanner without manual attestation, strict isolated-verifier preflight,
artifact-independence evidence, and the anti-cheat threat-model check. Record
their evidence hashes in `workspace/reports/<slug>/quota-ledger.json` and pass
`quota_guard.py --phase pre-review`. Mechanical failures return to the builder
and consume no reviewer turn.

Before a full difficulty probe, verify Terminus 3 goal/evidence/inferability:

- The goal, artifact paths, public interface/schema, and arbitrary exact
  conventions are explicit.
- Each semantic test maps to an inference family supported by one or more
  agent-visible sources; the final inferred rule need not be stated as prose.
- Hidden tests vary instances, combinations, layouts, or state sequences under
  the same inferable model and introduce no oracle-only policy.
- Every important instruction requirement has a matching verifier check, and
  the verifier accepts semantic equivalents when representation is not part of
  the goal.
- Two fresh task-visible Luna Codex tasks, launched in parallel and isolated
  from the builder, find the goal clear, the graded inference
  supportable, and no required fact unobtainable. They need not reproduce the
  oracle implementation.

Create `workspace/reports/<slug>/instruction-sufficiency.json` with
`schema_version: 3` and pass `sufficiency_manifest_check.py --require-v3`.

Then complete the semantic coverage gate in
`terminus-regular-task-authoring/references/semantic-coverage-gate.md`:

- freeze the complete task/verifier snapshot;
- require the finalized verifier architecture gate to pass; the semantic
  checker calls the same validator used by mining, authoring, and handover;
- map every public surface to platform-visible test IDs;
- record at least three independent mechanisms and two interactions;
- kill one plausible partial-fix mutant per mechanism and interaction;
- retain at least one deliberately wrong/incomplete implementation as the
  portal-required proof that the verifier rejects a wrong solution; the
  per-node mutant campaign remains the stronger batch requirement;
- the builder drafts the manifest and executes its mutants; the consolidated
  auditor independently reviews semantic realism after the draft is complete;
- save `semantic-coverage.json`, cleanly applicable patches, materialized
  mutant hashes, verifier logs/commands/CTRF, and an independent review
  transcript;
- pass `semantic_coverage_check.py --advanced-plus`.

Skeleton probes are exploratory only. They need a lightweight goal/evidence
audit and must be prepared with `--exploratory`; their results cannot qualify a
task or be reused after the full verifier is built.

### 3. Run the Pre-Probe Validity Gates

Reuse the strict preflight already completed before fairness, without emitting
a submission ZIP. This proves the exact
Docker verifier completes within its 900-second hard timeout, Oracle earns
`1.0`, NOP earns `0.0`, and the Oracle still passes under noexec `/tmp`:

```bash
scripts/preflight.sh workspace/tasks/<slug> --strict \
  --report-json workspace/reports/<slug>/probe-preflight.json \
  --evidence-dir workspace/reports/<slug>/probe-preflight-logs
```

Use one Luna-max consolidated-auditor task transcript for the semantic review, client/manual
folder review, and task-tree style audit. Run the client scanner and independent
manual review on the task folder before
freezing it. Clear blockers and should-fix findings now, before spending blind
solve sessions:

```bash
python3 .agent/skills/task-client-feedback-review/scripts/review_task.py \
  workspace/tasks/<slug> --json --manual-review-pass \
  --review-transcript workspace/reports/<slug>/consolidated-pre-freeze-audit.md \
  --review-runtime <actual-runtime> --review-model <actual-model> \
  --review-session-id <actual-session-id> \
  --evidence-output workspace/reports/<slug>/pre-freeze-review.json
```

Audit every task-visible prose surface, apply any rewrite, then create the
pre-freeze style receipt:

```bash
python3 .agent/skills/task-batch/scripts/evidence.py task-style-receipt \
  workspace/tasks/<slug> \
  --transcript workspace/reports/<slug>/consolidated-pre-freeze-audit.md \
  --runtime <actual-runtime> --model <actual-model> \
  --session-id <actual-session-id> \
  --output workspace/reports/<slug>/task-style-preflight.json
```

Create the fixed-role receipt from those three audit surfaces and the two
fairness reviews:

```bash
python3 .agent/skills/task-batch/scripts/session_budget.py create \
  workspace/tasks/<slug> workspace/reports/<slug> \
  --builder-runtime <actual-runtime> --builder-model <actual-model> \
  --builder-session-id <actual-builder-session-id>
```

Append every builder, reviewer, auditor, failed, interrupted, and follow-up
turn to `quota-ledger.json`, then require the solver reserve:

```bash
python3 .agent/skills/task-batch/scripts/quota_guard.py \
  workspace/reports/<slug>/quota-ledger.json --phase pre-solver
```

Finally run the shared ordering gate:

```bash
python3 .agent/skills/task-local-solve-probe/scripts/preprobe_check.py \
  workspace/tasks/<slug> workspace/reports/<slug>
```

Any fix invalidates the affected sufficiency, semantic, preflight, review,
style, or session-budget receipt. Regenerate them before continuing.
For a fairness/auditor remediation, send the report to the existing builder
session and save its finding dispositions before applying edits. A new
fresh-context builder is not an allowed remediation path.

### 4. Freeze the Counted Snapshot

Prepare counted solve copies only after Step 3 passes. `probe.py prepare`
revalidates and hash-binds the pre-probe technical, client-review, task-style,
V3 sufficiency, semantic-coverage, and verifier receipts:

```bash
python3 .agent/skills/task-local-solve-probe/scripts/probe.py prepare \
  workspace/tasks/<slug> --profile advanced_frontier_only
```

Do not create an intermediate ZIP. Packaging before the difficulty gate adds
no evidence and produces an archive that later style/submission work replaces.

### 5. Run the Local Solve Probe

Use `task-local-solve-probe` in counted mode with fresh subagents and isolated
solve copies. Counted preparation must validate and hash-bind both the V3
evidence-inferability receipt and the frozen semantic coverage/verifier
receipts. Do not expose the solution, verifier tests, rubrics, reports,
expected outputs, or hidden fixtures.

Use the actual subagent model available in the current environment. Preserve the real diff, verifier result, and failure classification for each attempt.

Run two fresh attempts concurrently. After both agents return, run their
materialization and verifier evidence pipeline sequentially. Add a third only
after a `1/2` split, a shared blind spot, or incomplete per-case union.

- A semantic failure is valid difficulty evidence only when it matches the
  documented crux and the contract is instruction-sufficient.
- Setup, compilation, dependency, refusal, and timeout failures do not count.
- If all local attempts solve the task, fairly strengthen it once or replace it;
  do not spend platform iteration quota on a locally 100% candidate.
- If at least one attempt fails semantically, retain the candidate and record a
  provisional tier signal from the observed local pass rate. Do not present that
  signal as the final platform tier.
- For a zero-solve Frontier signal, require 100% per-case union, zero common
  misses, and de-correlated failures. Otherwise audit the oracle and visible
  authority before proceeding.
- A split result is a valid Core/Advanced signal when both the passing and
  failing runs are trustworthy. Python follows the same rule as every language.
- In `advanced_frontier_only`, `1/3` additionally requires two distinct
  multi-node failure sets derived automatically from the semantic coverage
  manifest. Never use raw failed-row count or a manual de-correlation flag.

The platform iteration stage uses two runs per current reference model and
requires at least one failure across all four. Final difficulty is measured over
eight runs, so local evidence remains provisional.

If hardening changes instructions, tests, fixtures, solution, environment, or
metadata, return to Step 3 and prepare fresh counted runs.

For a provably mechanical task-visible edit only (whitespace, Unicode,
punctuation, or an allowlisted lexical substitution with unchanged V3 mapping),
follow the editorial-rebind rule in the quota workflow reference: rerun
deterministic checks and hashes, but do not recall the fairness pair. Any
requirement/evidence/interface change is semantic and invalidates the affected
review.

### 6. Harden the Shortlist and Audit Submission Prose

Only shortlisted candidates enter this step. Run applicable full local
Harbor/Terminus checks that do not require an API key, then create the final
submission file described below from the frozen task and observed probe
evidence.

The task-visible prose was already audited before the counted snapshot. Reuse
the same consolidated auditor Codex task with `send_message_to_thread` in a
new turn and use
`task-llm-style-audit` now only on external post-probe surfaces:

- rubric text;
- submission explanations;
- copy/paste metadata answers.

Rewrite flagged prose in clear, natural English without changing technical meaning, adding unsupported claims, or breaking instruction/test symmetry.

If this stage discovers a necessary task-content change, return to Step 3 and
rerun the counted probes. Do not silently edit the frozen task. Preserve the
submission-only audit transcript at
`workspace/reports/<slug>/style-audit-transcript.md`, then create the hash-bound
receipt with:

```bash
python3 .agent/skills/task-batch/scripts/evidence.py style-receipt \
  workspace/tasks/<slug> \
  --submission workspace/submissions/SUBMISSION-<slug>.md \
  --transcript workspace/reports/<slug>/style-audit-transcript.md \
  --runtime <actual-runtime> --model <actual-model> \
  --session-id <actual-session-id> \
  --output workspace/reports/<slug>/style-audit.json
```

The receipt reuses `task-style-preflight.json` by hash and covers only the
external submission surface. Do not create it unless the named auditor actually
reviewed that final submission.

### 7. Seal the Final Snapshot

After all task, submission, probe, and style changes are complete, create the
final mechanical evidence and ZIP in one strict run:

```bash
scripts/preflight.sh workspace/tasks/<slug> --strict \
  --report-json workspace/reports/<slug>/preflight.json \
  --evidence-dir workspace/reports/<slug>/preflight-logs \
  --emit-zip workspace/submissions/<slug>.zip
```

The receipt must include successful policy, agent/verifier image builds,
Oracle=1, NOP=0, Oracle under noexec `/tmp`, and hashes for the raw build,
solve, verifier, CTRF, and reward artifacts. A summary without those raw files
is not auditable evidence.

Run the client scanner on that exact final ZIP and save its receipt:

```bash
python3 .agent/skills/task-client-feedback-review/scripts/review_task.py \
  workspace/submissions/<slug>.zip --json \
  --manual-review-pass \
  --review-transcript workspace/reports/<slug>/client-review-transcript.md \
  --review-runtime <actual-runtime> --review-model <actual-model> \
  --review-session-id <actual-session-id> \
  --evidence-output workspace/reports/<slug>/client-review.json
```

Use the same consolidated-auditor runtime/model/session identity for this final
ZIP review and for `style-audit.json`. The post-probe transcripts are new and
must cover the exact final submission and ZIP; do not reuse the old transcript
hash as a substitute for reviewing changed surfaces.

Complete the manual portions required by `task-client-feedback-review`; the
scanner is a fail-closed mechanical subset, not a substitute for semantic
review. Preserve that manual review as the named non-empty transcript before
running this command. Then run the final handover gate:

```bash
python3 scripts/batch-handover.py workspace/tasks/<slug> \
  --report-dir workspace/reports/<slug> \
  --probe-dir workspace/local-solve-probes/<slug> \
  --zip workspace/submissions/<slug>.zip \
  --submission workspace/submissions/SUBMISSION-<slug>.md \
  --profile advanced_frontier_only \
  --batch-index workspace/reports/batches/<batch-id>.json \
  --expected-batch-size <N> \
  --incremental-batch \
  --output workspace/reports/<slug>/handover.json
```

Run `quota_guard.py --phase handover` first. Count the task only when this
command exits `0`, prints `CANDIDATE_READY`, and
the saved handover has `status: candidate_ready`. It independently recomputes
the task/ZIP file map, receipt hashes, V3 evidence sources and fairness transcripts,
probe diffs/CTRF, style surfaces, submission hash, and trusted probe verifier
results. Never hand-edit receipts to clear a failure; rerun the originating
stage.

## Submission File

Create one file per accepted task:

```text
workspace/submissions/SUBMISSION-<slug>.md
```

Use this exact structure:

```markdown
# Difficulty Explanation

Describe in original language why the task is challenging for humans and coding agents. Base the explanation on the actual task design and observed probe failures. Name the professional role that would perform this work and why it is relevant. State where any corpus, fixtures, captures, traces, or dataset came from and why they are realistic; if the task uses no external data, say that explicitly. Do not claim unsupported platform difficulty.

# Solution Explanation

Describe the high-level solution approach and the key implementation insights. Do not copy the full Oracle or expose hidden fixture values.

# Verification Explanation

Explain how the tests verify correctness, including the major behavior clusters, preservation checks, edge cases, and anti-shortcut coverage.

# Relevant Experience

State the concrete domain, toolchain, or repository experience that supports the task design. Keep it factual and do not invent personal credentials.

# Metadata

- Does this task use an approved canonical base image? Yes — `<exact image reference>` / No — `<reason>`
- Did you use a Task Inspiration from the Task Gallery for this submission? Yes / No
- Task Inspiration ID: `<ID or N/A>`

# Rubrics

Agent completes `<observable behavior>`, +5
Agent completes `<observable behavior>`, +5
Agent preserves `<observable behavior>`, +3
Agent breaks `<observable behavior>`, -3
```

Rubrics must:

- grade observable behavior, not implementation style;
- use one physical line per rubric item;
- start with `Agent`;
- end with an allowed signed score;
- avoid hidden fixture values, test names, solution details, and private failure evidence;
- cover the task's main independent behavior clusters;
- remain consistent with the instruction and verifier.

Run the style audit on the completed submission file.

## Acceptance Gate

Count a task toward `N` only when all of the following are true:

- The task is fresh and uses a domain-appropriate language.
- The incremental batch index contains the task and every accepted predecessor;
  the final sealed index contains exactly `N` tasks. Every listed pair has
  unique domain keys and architecture families and was compared on all axes.
- The schema-v3 candidate ledger contains every qualified attempt, stays within
  the explicit candidate budget, preserves rejected dispositions, and lists
  the same `N` accepted tasks as the final batch index. It passes domain-crux,
  convention-symmetry, source-smoke, structural-diversity, anti-retrieval, and
  orthogonal-trap validation without enforcing an exact track allocation. Each
  derived entry still proves a non-reskin transformation.
- The task folder is complete.
- The goal is clear and the graded domain model is inferable from visible evidence under schema version 3.
- The frozen semantic coverage receipt passes, covers every public surface,
  and contains executable dedicated mutants for every mechanism and interaction.
- The mining architecture plan passed before scaffolding, and the finalized
  verifier matrix passed before Oracle/NOP with the correct 50–1000 or 20–80
  platform-visible breadth, cluster count, cross-cluster units, and shapes.
- `probe-preflight.json`, `pre-freeze-review.json`,
  `task-style-preflight.json`, and `agent-session-budget.json` all pass against
  the exact counted task snapshot,
  and `preprobe_check.py` accepts them before any counted solve starts.
- Whole-task Ruff validation, including `PLW1510`, is clean.
- Docker builds successfully.
- Oracle reward is `1.0`.
- NOP reward is `0.0`.
- Applicable local Harbor checks pass without requiring an API key.
- The final ZIP passes client-feedback review with no blocker.
- Two valid fresh attempts exist, with an adaptive third when required, and at
  least one trustworthy semantic failure provides a local difficulty signal.
- The role receipt and final probe evidence prove exactly one builder, two
  fairness reviewers, one reusable consolidated auditor, and two or three
  blind solvers: 6–7 total sessions and 5–6 external sessions per accepted task.
- The quota ledger counts every actual model turn, enforces Sol-medium for
  design/building, Luna-high Codex tasks for fairness review, a Luna-max Codex
  task for consolidated audit, and Sol-medium subagents for blind solving,
  stays within 12
  turns, respects both one-cycle remediation caps, and passed the pre-solver
  reserve and handover checks.
- Any provisional Advanced `1/3` has distinct multi-node failure geometry; any
  replicated single-lever split is rejected.
- The pre-freeze task-tree style audit and post-probe submission-only style
  audit are both clean and hash-bound to their exact surfaces.
- `workspace/submissions/<slug>.zip` exists and matches the final task state.
- `workspace/submissions/SUBMISSION-<slug>.md` exists and is accurate.
- The final `workspace/reports/<slug>/handover.json` is schema version 2,
  hash-binds every required evidence file, and says `candidate_ready` after a
  successful `scripts/batch-handover.py` run.

Do not count rejected, infrastructure-failed, ambiguous, locally all-pass, or
merely packaged candidates. A trustworthy split is valid Terminus 3 evidence.

## Final Response

Report one row per accepted task with:

- slug;
- language;
- category;
- Docker result;
- Oracle reward;
- NOP reward;
- Harbor result;
- ZIP review result;
- probe run results and any adaptive third run;
- provisional local tier signal;
- ZIP path;
- submission file path;
- final ZIP SHA-256 and handover receipt path.

Also list every qualified discarded candidate and its concise rejection reason;
distinguish verified results from unavailable external checks. Report the
candidate-budget usage, established/derived attempt counts, accepted tracks,
pattern IDs, and any non-blocking rolling-portfolio advisories. For every
derived attempt, include its `X-*` ID and one-sentence non-equivalence rationale.
