# Task Batch

Create a fresh autonomous batch of submit-ready Terminus Regular tasks.

## Invocation

Accept either form:

```text
task-batch N
/task-batch N
```

Treat `N` as the required delivery count. It must be a positive integer. It
does not cap how many candidates, repairs, retries, or recorded model turns the
workflow may need.

Before Stage A, read and select exactly one profile from
[`execution-profiles.md`](execution-profiles.md). This file
applies only once `campaign_ready` has been selected explicitly; a bare
`task-batch N` selects `builder_certified` and never loads it. The selected profile
controls required roles, evidence, stop conditions and result labels throughout
the run; never execute the full workflow and mark omitted gates as expected
failures.

## CORE+ Campaign Profile (`campaign_ready` only)

The current repository campaign uses `core_advanced_frontier`: accept Core,
Advanced, or Frontier candidates and reject Base/all-pass candidates. Historical
`advanced_frontier_only` receipts remain readable but must not be created for a
new batch.

This profile adds a stricter selection stage to the general submit-ready path:

- `N` counts only final `candidate_ready` tasks whose ZIP, preflight,
  review, and handover gates pass. `core_plus_shortlist` is an intermediate
  state and never increments the delivered-task count.
- Use a hash-bound counted blind probe as the selection gate. Before launching
  it, finish the verifier/oracle, public-surface audit, V3 evidence audit,
  mutation-backed semantic coverage receipt, and exact-Docker
  Oracle/NOP/noexec pre-probe receipt. A separate counted-freeze stage is
  optional: `probe.py prepare` may run as the first mechanical action of the
  blind-solver stage. Full Harbor checks, final ZIP review, and submission
  hardening remain after shortlist selection. An exploratory skeleton probe can
  reject an idea cheaply but can never qualify it or increment `N`.
- Complete the task, verifier, Oracle/NOP/noexec proof, mutation evidence, and
  mechanical quality gates before `contract_review`. A review repair must
  regenerate every affected receipt. Harbor remains post-shortlist unless the
  user explicitly requires an earlier integration diagnosis.
- Run exactly two fresh blind solvers. `0/2` or `1/2` solved is sufficient local
  difficulty evidence for the CORE+ campaign after all fairness, verifier,
  Oracle, NOP, isolation, mutation, review, and packaging gates pass. Preserve
  union coverage, common misses, and failure geometry as diagnostics, but never
  use them to block or promote the task.
- A first `2/2` result triggers one fair hardening cycle and one fresh two-run
  probe. Reject only if that second valid pair is also `2/2`. Preserve truthful
  evidence; never prune passing cases or hide contract facts to move a task upward.
- Report qualifying candidates as `core_plus_shortlist` with a provisional local
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
- Under `core_advanced_frontier`, count valid Core, Advanced, and Frontier
  candidates; Base/all-pass candidates do not count toward `N`.
- Keep mining replacements until the requested delivery count is met. There is
  no candidate-attempt limit.
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
attempt, including later rejections. There is no candidate budget or maximum
attempt count. Use roughly 20–30% derived attempts as a non-blocking
exploration advisory. A rejection may be followed by either track, and the
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
  "execution_profile": "campaign_ready",
  "expected_count": 1,
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
      "scope_ledger": {
        "primary_outcome": "<one observable result>",
        "causal_core": "<inference chain>",
        "core_obligations": ["<obligation id>"],
        "support_obligations": ["<supplied parsing/schema boundary>"],
        "non_goals": ["<explicitly ungraded domain>"]
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
        "planned_mechanism_ids": ["planner-rule", "stats-refresh"],
        "planned_interaction_ids": ["plan-stats"],
        "retrieval_audit": {
          "search_queries": ["issue wording", "failure symbol", "release version diff"],
          "public_artifacts_checked": ["<URLs/commits checked>"],
          "exact_solution_found": false,
          "overlap_classification": "none",
          "callable_solution_available": false,
          "satisfied_mechanism_ids": [],
          "satisfied_interaction_ids": [],
          "non_collapse_rationale": "<required for substrate_primitives or partial_topology>",
          "disposition": "pass"
        },
        "orthogonal_traps": [
          {"id": "trap-a", "semantic_node": "planner-rule", "repair_surface": "planner.rule", "natural_implementation": "<reasonable local fix>", "why_wrong": "<semantic counterexample>", "witness_ids": ["interaction-a"]}
        ],
        "shared_fix_rationale": null
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

Record a candidate in the ledger after it passes taxonomy, novelty,
anti-retrieval, domain crux, convention symmetry, canonical source/runtime
smoke, topology, and verifier-plan gates. Raw ideas and early taxonomy failures
need not enter the ledger. This is provenance, not an attempt limit. Pattern
membership never substitutes for semantic rank, fairness, mutation coverage,
or empirical difficulty evidence.

## Required Skills

Read each relevant `SKILL.md` completely before using that stage:

1. `task-miner`
2. `task-clone`
3. `terminus-regular-task-authoring` and any required language-specific skill
4. `task-client-feedback-review`
5. `terminus-rubric-authoring`
6. `task-llm-style-audit`
7. `task-local-solve-probe`
8. `task-harbor-runner`
9. `task-zip-submit`

`campaign_ready` uses all applicable entries. `panel_ready` uses only
`task-miner`, `task-clone`, `terminus-regular-task-authoring`,
`task-quality-panel-judgement`, deterministic `task-client-feedback-review`,
`task-harbor-runner`, and `task-zip-submit`; do not load or execute omitted
fairness, auditor, rubric, style or solve-probe stages merely because they are
listed for the full campaign.

This file controls the batch policy when it is more specific than a dependent
skill. In `campaign_ready`, read
[`quota-efficient-workflow.md`](quota-efficient-workflow.md)
and
[`single-reviewer-workflow.md`](single-reviewer-workflow.md)
before launching campaign roles. In `panel_ready`, do not load those campaign
references; read `references/execution-profiles.md`, bounded task design and the
quality-panel precheck reference instead. Every subagent uses the active
runtime's fixed model:
`gpt-5.6-sol` medium in Codex, or Opus 5 medium in Claude Code. This applies to
the selected builder and quality-panel reviewers; `campaign_ready` additionally
applies it to its fairness reviewer, blind solvers and consolidated auditor.
Only `campaign_ready` reuses one fresh fairness-reviewer session for its
contract and final review turns. Record the actual runtime/model and fail
closed when that profile is unavailable; never silently substitute another
model.
In `campaign_ready`, before launching a builder, also follow
[`builder-quota-hooks.md`](builder-quota-hooks.md).
Validate both repository-local agent hook configurations, create the
stage-specific hash-bound context packet, and open the lease for the exact
builder subagent type. Stage A ends after mining plus canonical-image source
smoke. Transition to scaffolding only before a new counted follow-up. Poll the
lease during waits and interrupt at its deadline; hooks cannot interrupt an
in-flight model request by themselves.
The consolidated auditor is mandatory, independent, and read-only only in
`campaign_ready`. Bind its identity and transcript into that profile's quota
ledger and final receipts.

## Truthfulness Rules

- Never claim that a command, validation, review, or probe ran without its real output and exit status.
- Never invent a subagent, model name, transcript, run ID, score, diff, or test result.
- Record the actual model reported by each probe environment when available.
- Treat setup, Docker, tool, dependency, timeout, and compilation failures as infrastructure failures, not evidence of task difficulty.
- Do not mark a task submit-ready while a required local check is blocked.
- Harbor API-key-dependent LLM-agent runs are not required. Local Docker build, Oracle, NOP, and non-API Harbor checks are required.
- If external infrastructure is unavailable, continue every safe independent step, preserve the artifacts, and report the exact blocker. Never fabricate completion to satisfy the delivery count.
- Treat `scripts/batch-handover.py` as the only authority allowed to emit
  `candidate_ready`. A prose checklist, a successful ZIP command, or copied
  terminal output cannot increment the accepted-task counter.
- Evidence is immutable and snapshot-bound. Preserve raw logs, CTRF, diffs,
  agent/reviewer transcripts, runtime/model/session provenance, and SHA-256
  digests. Any task or submission change invalidates dependent receipts.

## Unbounded Attempts and Role Separation (`campaign_ready` only)

Each task uses one persistent builder identity, one persistent fairness-reviewer
identity, one persistent consolidated-auditor identity, and exactly two valid
blind-solver results. The reviewer covers `contract_review` and `final_review`
in the same fresh-context session. Record every model turn, including
follow-ups, failures, interruptions, usage-limit stops, and retries, but impose
no turn, session, remediation, or candidate-attempt quota. Failed solver
launches do not count toward the two valid results and may be replaced with
fresh attempts on the required profile.

| Role | Required successful identity/result | Scope |
|---|---:|---|
| Builder | 1 | deep mining, authoring, Oracle, verifier, semantic-manifest draft, and all pre-freeze fixes |
| Reviewer | 1 | fresh task-visible contract review, then final review in the same session |
| Consolidated auditor | 1 | independent semantic/folder/style and final packet audit |
| Blind solvers | 2 valid results | fresh one-shot solves; replace invalid infrastructure attempts |

The builder never performs independent review or a blind solve. The builder and
blind solvers use collaboration subagents. The default reviewer is one
Sol-medium Codex subagent or Opus-5-medium Claude subagent. It receives only
`instruction.md` plus the agent-visible environment/evidence and performs the
required `contract_review` and `final_review` phases in the same session. The
auditor is a distinct required session using the same runtime-specific model.

The design/build agent is not fresh-context. Keep one persistent informed
builder session on the runtime-specific fixed model. Before choosing a candidate, make it read the
durable campaign memory, current batch portfolio, and relevant rejection/probe
reports, then record and hash-bind the pattern-blind domain-crux card. Only
after that may it read the frontier pattern catalog to classify the design or
derive a structural transformation. Send every reviewer/auditor report back to
that same builder. Require a finding-by-finding critique receipt (`accept`,
`challenge`, or `partial`, with evidence and action), plus an independent
orchestrator adjudication, before remediation. Never leak this builder context
into the fresh reviewer or blind solvers.

Run the contract-stage prompt/scanner/source-smoke/assertion-symmetry gates
before launching the reviewer's contract pass. Full strict Docker, artifact-independence,
anti-cheat, mutation, and Harbor work belongs later, after the task-visible
contract is stable. In `campaign_ready`, review and audit failures return to the same
builder for correction and the affected gate is rerun until it passes or the
candidate is shown to require an unfair contract, unreachable authority, or
fundamental redesign. Repeated failure alone is not a quota-based rejection.
Before blind solvers, run `quota_guard.py --phase
pre-solver` to verify role routing, completed review gates, lease provenance,
and remediation history. There is no fixed per-candidate or batch-wide
model-turn, remediation, or candidate limit.

Launch the first two blind solvers concurrently on separate solve copies. Wait
for both to finish, then materialize, execute the verifier, collect CTRF, and
record each run sequentially. Never add a third solver. Use the reviewer's
second turn for the stable final task
review. Submission prose, exact final ZIP review, and metadata/handover are
mechanical/orchestrator work, with the mandatory auditor checking the stable
pre-probe and final submission surfaces.

Do not create separate specialist agents for static scanning, prose inventory,
mutation execution, packaging, or handover. The orchestrator runs deterministic
tools and the fixed roles supply the required judgments. A candidate rejected
at mining or the smoke gate should not launch a full review/solve cohort. An
accepted task proves the required role separation and two valid solver results;
failed launches and corrective follow-ups may increase the recorded
turn/session count without invalidating it.

Safe concurrency: different-domain idea cards/builders in separate worktrees,
each initial solver pair, and static scanning alongside prose inventory.
Different task cohorts require separate worktrees and lease directories. Run
Docker builds for one task, Oracle/NOP/noexec, shared-image mutation runs,
solver verifier executions, final packaging, and handover sequentially.

Only one builder lease may be active in a shared worktree. Parallel builders
must use separate worktrees and separate lease paths; otherwise their task
trees, Docker state, and hook ownership are not safely isolated.

## Preflight

Before mining:

1. In `campaign_ready`, bootstrap, trust, and validate both repository-local
   agent configurations. This is mandatory on a fresh clone for campaign roles
   and idempotent on an existing checkout:

   ```bash
   python3 .agent/skills/task-batch/scripts/setup_agent_hooks.py \
     --install --trust --self-test
   ```

   It installs the shared skill discovery links, enables the committed hooks,
   and records project trust for both Codex and Claude without replacing other
   user settings. A failure blocks campaign mining. `panel_ready` skips these
   quota/session hooks and checks only that its builder and fresh panel reviewer
   routing are available.
2. Confirm the workspace and output directories.
3. Confirm Docker is reachable.
4. Confirm the local Terminus/Harbor tooling needed for Oracle and NOP runs is available.
5. Confirm repository mining access is available.
6. Inspect existing workspace and submission slugs so the batch cannot overwrite or duplicate them.
7. Confirm collaboration-subagent routing for the roles selected by the active
   profile: builder plus eight panel reviewers for `panel_ready`; builder,
   fairness reviewer, auditor and solver pair for `campaign_ready`.

Stop early only for a real external blocker that prevents all useful progress. Otherwise continue autonomously.

## Batch Loop

Maintain a profile-specific accepted counter: `candidate_ready` for
`campaign_ready`, or `local_panel_cleared` for `panel_ready`. Repeat only until
that counter equals `N`.

Candidate retirement is a loop transition, not batch completion. Preserve its
evidence and disposition, leave the accepted count unchanged, then immediately
return to mining a structurally fresh replacement within the user's requested
category/subcategory and language. If taxonomy review moves a candidate outside
that requested pair, do not count it or silently broaden the batch scope.
A progress report, a Base ZIP, or a long unsuccessful build is not a stopping
condition. Stop short of N only for a user stop or a concrete external blocker
that prevents all useful in-scope progress; record the blocker and resume point.
This applies equally to Claude and Codex.

Treat prior batch reports as evidence, not new policy. In particular, a reported
2/2 on one snapshot does not establish the tier of a later unprobed snapshot,
nor prove an entire domain impossible. Do not replace V3 inferability with a
requirement that all ground truth be impossible to self-check. Carry forward
the specific failed design hypothesis, not a blanket domain ban.

The following fixed candidate lifecycle applies only to `campaign_ready`:

`mine candidate → build task → run complete quality/Oracle/NOP gates → contract_review → repair/recheck until pass → final_review → repair/recheck until pass → mandatory auditor → repair/recheck until pass → two valid blind-solver results → accept 0–1/2, or fairly strengthen once and re-probe after 2/2 → final ZIP/handover`.

Failures are routed by cause:

- setup, provider, timeout, dependency, Docker-daemon, or tool failures are
  infrastructure failures; preserve the evidence, repair/retry the same stage,
  and never count them as difficulty or as one of the two valid solver results;
- Oracle, NOP, isolation, mutation, packaging, or other mechanical-quality
  failures return to the builder, invalidate affected receipts, and rerun until
  green;
- contract-review, final-review, or audit findings return to the same builder,
  then the same reviewer/auditor identity rechecks the affected surface;
- quality-panel discovery findings receive one consolidated batch and one fresh
  clearance; a blocking clearance returns `rescope_required` and stops that
  obligation set rather than entering this generic repair loop;
- reject only when the candidate is intrinsically unfair, depends on an
  unreachable authority, needs a fundamental redesign better treated as a new
  candidate, cannot make progress after evidence-based fixes, or remains `2/2`
  after the single allowed fair difficulty-hardening cycle.

Every repair invalidates and regenerates the affected hash-bound evidence. The
second `2/2` result rejects the candidate; there is never a third solver run.

`campaign_ready` executes `1 → 2 → 3 → 4 → 5 → 6 → 7`.
`panel_ready` follows the shorter path in `execution-profiles.md`
and never calls campaign-only handover. In `campaign_ready` Step 2, preserve
the order `full task/verifier → complete Oracle/NOP/quality gates → contract review → repair → final review → repair → auditor`.
The CORE+ profile
uses Step 5 as a selection gate, but the technical validity checks in Step 3
always happen first. Only the final handover in Step 7 increments the
`campaign_ready` counter; five-axis non-blocking closure plus exact deterministic closure and
packaging increments the `panel_ready` counter.
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
- have a fair goal and enough evidence under its declared
  `[agent].network_mode` to
  infer the graded model; the verifier itself remains deterministic and
  self-contained;
- have enough causal and inferential depth to plausibly resist a strong agent,
  without accumulating independent behavior families;
- avoid saturated task families, lane-matched collapse patterns, oracle-only
  policies, unobtainable facts, and unreachable authorities; discoverable
  hidden requirements and held-out combinations are allowed;
- apply [bounded task design](../../terminus-regular-task-authoring/references/bounded-task-design.md):
  declare a runtime profile and obligation-driven verifier inventory, with
  discriminating coverage of every promised public surface and real interaction;
  do not impose unit/cluster/shape quotas or inflate scope to satisfy them;
- for `panel_ready`, create the obligation manifest and pass
  `terminus-regular-task-authoring/scripts/panel_precheck.py --design-only` before
  scaffolding; a disconnected core or serialization-only bundle is rejected;
- record its source repository, base commit, task contract, category, language, and novelty evidence;
- define the pattern-blind domain crux and pass the convention/assertion audit
  before assigning its `established` or `derived` classification;
- in `campaign_ready`, pass the schema-v3 frontier-stability gate: one dominant
  topology, a recorded anti-retrieval search, and natural-but-wrong coverage for
  the retained causal core. Multiple claimed traps need distinct semantic
  nodes/repair surfaces and distinguishable witnesses. Classify
  public overlap as `none`, `substrate_primitives`, `partial_topology`,
  `task_topology`, or `exact_solution`. Primitive count alone never rejects a
  candidate. Reject only `task_topology`, `exact_solution`, or a reachable
  callable solution/oracle; use an upstream fix only as substrate for a
  materially new topology;
- pass the canonical-image source/runtime/entrypoint smoke before it is added
  to the candidate ledger and before Stage B begins.

Save the mined artifact and pass
`verifier_architecture_check.py plan <candidate.json>` before scaffolding.
Reject weak or thin candidates before building. Do not fill the requested
delivery count with ports or cosmetic variants.

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
  "execution_profile": "campaign_ready",
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

For a Hardware / CAD candidate, apply
`docs/creating-tasks/cad-task-guidelines.md` at this checkpoint. The verifier
plan must measure every stated dimension and through/repeated/exact-count
feature on built geometry using an approach the selected engine supports.
Sampling grain must be finer than its tolerance. A parametric promise requires
changing a fresh driving value, recomputing without errors, and measuring the
changed solid; reading stored parameters does not qualify as a witness.

Begin with a compact set of discriminating witnesses derived from the scope
ledger, covering its core obligations, causal interaction, and arbitrary
conventions. Run the assertion-to-source audit against those witnesses. Reject
or narrow the candidate now if the contract, Oracle model, and observable
assertions cannot be made symmetric; do not multiply an unresolved convention
into dozens of fixtures.

Complete the verifier only for the retained scope before review. Do not add
mechanisms, malformed-input domains or compatibility behavior to imply
difficulty. Collect the exact
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

After the breadth gate passes, the builder finishes `solution/`, runs targeted
Oracle/NOP checks, stabilizes the mutation campaign, and then runs the complete
strict Oracle/NOP/noexec and quality gates. Reject broken/thin candidates here.
Add the raw
Oracle CTRF path and SHA-256 to `verifier-matrix.json`, then rerun the same
command without `--allow-missing-ctrf`. The CTRF IDs must exactly equal the
declared behavior plus non-behavior IDs.

Before `contract_review`, run the five full mechanical gates in
`references/quota-efficient-workflow.md`:
instruction preflight, client scanner without manual attestation, strict
isolated-verifier preflight, artifact-independence evidence, and the anti-cheat
threat-model check. Record their evidence hashes in
`workspace/reports/<slug>/quota-ledger.json`. Mechanical failures return to the
builder and consume no reviewer or solver turn.

In `campaign_ready`, now launch the single reviewer's `contract_review` turn on the hash-bound
task-visible packet. The builder and orchestrator adjudicate every finding,
repair it, and recheck the affected surface until it passes or meets an
explicit fundamental-rejection condition. Regenerate all affected
Oracle/NOP/quality evidence. Then reuse the reviewer for `final_review`, apply
the same unbounded repair/recheck rule, and run the mandatory auditor. Do not
launch blind solvers while any review, audit, Oracle, NOP, or quality failure
remains.

The strict preflight must include `check_modal_dockerfile_compat` for every
Dockerfile: digest-only external-image `COPY --from=` refs. Local Docker success
does not waive this cloud-builder gate. `COPY --chown=` may be named or numeric.
When the task ships a Compose file, also run `check_compose_networks`: no
`networks:` or per-service `network_mode:` in the Compose file, and all three
`task.toml` phases `"public"`.

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
- Every domain rule explicitly named by the contract has an isolating fixture
  whose expected result changes when that rule alone is inverted; held-out data
  is never the sole enforcement of a stated rule.
- One fresh task-visible reviewer session, isolated from the builder, finds the
  goal clear, the graded inference supportable, and no required fact
  unobtainable. It need not reproduce the oracle implementation. The same
  session later performs `final_review` against the stable snapshot.

Create `workspace/reports/<slug>/instruction-sufficiency.json` with
`schema_version: 3` and pass `sufficiency_manifest_check.py --require-v3`.

Run `task-quality-panel-judgement` when required by the selected profile.
`Minor` and `Major` block on `coherent_contract`,
`correct_reference_solution`, `sound_verifier`, and `deterministic_execution`;
only `Major` blocks on `protected_ground_truth`. Findings marked `Advisory` do
not block, and `Unsure` is not itself a confirmed defect, but an undecided axis
leaves the gate uncleared. Its discovery → one remediation batch
→ one clearance stop overrides generic retry language: a blocking clearance
returns `rescope_required`, not another witness-expansion loop. If tests execute agent code in
the verifier, require privilege demotion plus `--no-new-privs` or equivalent,
read isolation from goldens and `/logs/verifier`, and neutral input paths. Scan
Python verifier cleanup for the merged-`/usr` Bash-mode alias bug before probe.

Then complete the semantic coverage gate in
`terminus-regular-task-authoring/references/semantic-coverage-gate.md`:

- freeze the complete task/verifier snapshot;
- require the finalized verifier architecture gate to pass; the semantic
  checker calls the same validator used by mining, authoring, and handover;
- map every public surface to platform-visible test IDs;
- record the natural mechanisms and at least one genuine causal interaction;
  counts are descriptive and must never cause scope expansion;
- kill one plausible partial-fix mutant per mechanism and interaction;
- retain at least one deliberately wrong/incomplete implementation as the
  portal-required proof that the verifier rejects a wrong solution; the
  per-node mutant campaign remains the stronger batch requirement;
- the builder drafts the manifest and executes its mutants; the reviewer's
  `final_review` independently checks semantic realism after the draft is
  complete; the consolidated auditor then performs the required independent
  quality, Oracle, NOP, isolation, and artifact review;
- save `semantic-coverage.json`, cleanly applicable patches, materialized
  mutant hashes, verifier logs/commands/CTRF, and an independent review
  transcript;
- pass `semantic_coverage_check.py --advanced-plus`.

Build mutation evidence in two phases. First, run each candidate mutant only
against its small targeted witness set until the intended behavior is killed
and at least one unrelated witness survives. Do not launch strict preflight,
Harbor, or the complete matrix while any targeted witness is red. Once the
task, Oracle, and every mutant anchor are stable, run each accepted mutant and
the wrong/incomplete solution against the full verifier exactly once for that
snapshot. Preserve rejected/no-op/compile attempts as evidence, but do not
re-run the whole matrix merely to debug them.

Skeleton probes are exploratory only. They need a lightweight goal/evidence
audit and must be prepared with `--exploratory`; their results cannot qualify a
task or be reused after the full verifier is built.

### 3. Run the Pre-Probe Validity Gates

Revalidate strict preflight after all review/audit remediation is closed, the
complete Oracle is green, and all mutant anchors are stable. Do
not emit a submission ZIP. This proves the exact
Docker verifier completes within its 900-second hard timeout, Oracle earns
`1.0`, NOP earns `0.0`, and the Oracle still passes under noexec `/tmp`:

```bash
scripts/preflight.sh workspace/tasks/<slug> --strict \
  --report-json workspace/reports/<slug>/probe-preflight.json \
  --evidence-dir workspace/reports/<slug>/probe-preflight-logs
```

In `campaign_ready`, reuse the single reviewer session for its `final_review` turn covering semantic
realism, client/manual folder review, and task-tree style. The builder and
orchestrator adjudicate every finding. Then run the mandatory independent
auditor. A failed review/audit returns to the same builder and then to the same
reviewer/auditor identity for recheck; stop when the repair would require scope
inflation or fundamental redesign. Run the client
scanner and independent manual review on the task
folder before spending blind-solve sessions:

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

Create the role receipt from the builder, the single two-pass reviewer, and the
required auditor:

```bash
python3 .agent/skills/task-batch/scripts/session_budget.py create \
  workspace/tasks/<slug> workspace/reports/<slug> \
  --builder-runtime <actual-runtime> --builder-model <actual-model> \
  --builder-session-id <actual-builder-session-id>
```

Append every builder, reviewer, auditor, failed, interrupted, and follow-up
turn to `quota-ledger.json`; this is an audit ledger, not a quota. Then require
the pre-solver role and evidence gates:

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
For reviewer/auditor remediation, send the report to the existing builder
session, save its finding dispositions, and save the orchestrator adjudication
before applying edits. A new fresh-context builder is not an allowed
remediation path.

### 4. Optional Explicit Counted-Freeze Checkpoint

Do not pause for a separate counted-freeze stage when Step 3 already proves the
exact snapshot. Proceed directly to blind solving and run `probe.py prepare` as
the first mechanical action there. A user may request an explicit checkpoint
for inspection, but it creates no additional model role or quality claim.

Do not create an intermediate ZIP. Packaging before the difficulty gate adds
no evidence and produces an archive that later style/submission work replaces.

### 5. Run the Local Solve Probe

Use `task-local-solve-probe` in counted mode with fresh subagents and isolated
solve copies. Counted preparation must validate and hash-bind both the V3
evidence-inferability receipt and the frozen semantic coverage/verifier
receipts. Do not expose the solution, verifier tests, rubrics, reports,
expected outputs, or hidden fixtures.

Unless Step 4 was explicitly requested, begin this stage directly with:

```bash
python3 .agent/skills/task-local-solve-probe/scripts/probe.py prepare \
  workspace/tasks/<slug> --profile core_advanced_frontier
```

Use the actual subagent model available in the current environment. Preserve the real diff, verifier result, and failure classification for each attempt.

Run exactly two fresh attempts concurrently. After both agents return, run
their materialization and verifier evidence pipeline sequentially. Do not add a
third run.

- A semantic failure is valid difficulty evidence only when it matches the
  documented crux and the contract is instruction-sufficient.
- Setup, compilation, dependency, refusal, and timeout failures do not count.
- If all local attempts solve the task, fairly strengthen it once or replace it;
  do not send a locally 100% candidate to platform iteration.
- If at least one attempt fails semantically, retain the candidate and record a
  provisional tier signal from the observed local pass rate. Do not present that
  signal as the final platform tier.
- A `0/2` or `1/2` result qualifies for CORE+ handover when both runs are valid
  and every quality gate is green. Union coverage, common misses, and semantic
  geometry remain diagnostic only.
- A split result is a valid Core signal when both the passing and
  failing runs are trustworthy, but a local 1/2 maps near the platform's 62.5%
  ceiling, so treat it as marginal rather than comfortable. Python follows the
  same rule as every language.
- If `2/2` solve the task, the builder may strengthen the task fairly once,
  rerun every invalidated quality receipt, and run one fresh two-solver probe.
  If the second probe is also `2/2`, reject the candidate.

The platform measures difficulty once, after the quality panel passes: four
runs per current reference model, eight total. A new submission needs at least
3 of those 8 runs to fail, so no more than 5 may pass and the ceiling is 62.5%
accuracy. Tasks already on the platform by the morning of Sep 11, 2026 keep the
prior one-failure rule, including their later revisions. Local evidence remains
provisional.

If hardening changes instructions, tests, fixtures, solution, environment, or
metadata, return to Step 3 and prepare fresh counted runs.

For a provably mechanical task-visible edit only (whitespace, Unicode,
punctuation, or an allowlisted lexical substitution with unchanged V3 mapping),
follow the editorial-rebind rule in the quota workflow reference: rerun
  deterministic checks and hashes, but do not recall the reviewer. Any
requirement/evidence/interface change is semantic and invalidates the affected
review.

### 6. Harden the Shortlist and Audit Submission Prose

Only shortlisted candidates enter this step. Run applicable full local
Harbor/Terminus checks that do not require an API key, then create the final
submission file described below from the frozen task and observed probe
evidence.

Do not run Harbor during mining, scaffold, fairness remediation, mutant
debugging, or pre-shortlist reviewer remediation. A requirement that Harbor pass
before delivery does not authorize moving it earlier. The only exception is an
explicit user request for an early Harbor integration diagnosis; record that
exception and do not treat it as difficulty evidence.

Before drafting rubric prose, use `terminus-rubric-authoring` to build
`workspace/reports/<slug>/rubric-coverage.md` from the exact frozen task,
agent-visible contract, and verifier cases. Every requested output, public
field, preservation promise, supported mode, and important interaction must map
to a discriminating witness and a rubric criterion. A `partial` or `uncovered`
row blocks this stage: repair the task/verifier, return to Step 3, and rerun all
snapshot-bound evidence and counted probes affected by the semantic change.
Never narrow the rubric to conceal the gap.

Draft task-specific criteria from that matrix; there is no default count of
positive or negative lines. Then check the current packet together with the
accepted packets in the active batch portfolio and save a hash-bound receipt:

```bash
python3 .agent/skills/terminus-rubric-authoring/scripts/check_rubric.py \
  workspace/submissions/SUBMISSION-<slug>.md \
  <accepted-portfolio-submission-files...> \
  --coverage-matrix workspace/reports/<slug>/rubric-coverage.md \
  --output workspace/reports/<slug>/rubric-check.json
```

The current packet must pass. Portfolio topology and catch-all warnings require
an explicit adjudication in `style-audit-transcript.md`; include the exact
warning text beside the keep/rewrite decision. Rewrite only when the warning
reflects templating rather than the task's evidence. The handover gate
hash-checks both the current submission and coverage matrix from this receipt
and rejects warnings absent from that transcript.

The task-visible prose was already reviewed before the counted snapshot. After
the rubric check, use `task-llm-style-audit` on external post-probe surfaces.
The required auditor reviews these surfaces in its permitted final follow-up:

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
external submission surface. Bind it to the required auditor's actual identity.

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

Reuse the consolidated auditor's runtime/model/session identity for this final
ZIP review and `style-audit.json`. Post-probe transcripts
must cover the exact final submission and ZIP; do not reuse an old transcript
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
  --profile core_advanced_frontier \
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

The four explanations (`difficulty_explanation`, `solution_explanation`,
`verification_explanation`, `relevant_experience`) are written only into
`task.toml` `[metadata]`, which the platform reads from the ZIP: name the
professional role, state where any corpus or fixtures came from (or that no
external data is used), base difficulty on the actual design and observed probe
failures, and never copy the Oracle or hidden fixture values. Do not repeat them in
the packet (user decision 2026-09-26). Use this exact structure:

```markdown
# SUBMISSION — <slug>

- Task: <one sentence: what the agent must produce, in domain words>
- Category: <Category> / <Subcategory>
- ZIP: `workspace/submissions/<slug>.zip`

# Metadata

- Does this task use an approved canonical base image? Yes — `<exact image reference>` / No — `<reason>`
- Did you use a Task Inspiration from the Task Gallery? Yes — `<Inspiration ID>` / No

# Rubrics

`<task-specific criteria derived from rubric-coverage.md; one physical line each>`
```

Rubrics must:

- grade observable behavior, not implementation style;
- use one physical line per rubric item;
- start with `Agent`;
- end with an allowed signed score;
- avoid hidden fixture values, test names, solution details, and private failure evidence;
- cover the task's main independent behavior clusters;
- remain consistent with the instruction and verifier.
- use no fixed positive/negative count or repeated score topology;
- pass `terminus-rubric-authoring/scripts/check_rubric.py` against the current
  packet and active portfolio, with a complete contract-witness matrix.

Run the style audit on the `task.toml` explanations and the completed submission file.

## Acceptance Gate (`campaign_ready` only)

Count a task toward `N` only when all of the following are true:

- The task is fresh and uses a domain-appropriate language.
- The incremental batch index contains the task and every accepted predecessor;
  the final sealed index contains exactly `N` tasks. Every listed pair has
  unique domain keys and architecture families and was compared on all axes.
- The schema-v3 candidate ledger contains every qualified attempt, imposes no
  candidate limit, preserves rejected dispositions, and lists
  the same `N` accepted tasks as the final batch index. It passes domain-crux,
  convention-symmetry, source-smoke, structural-diversity, anti-retrieval, and
  orthogonal-trap validation without enforcing an exact track allocation. Each
  derived entry still proves a non-reskin transformation.
- The task folder is complete.
- The goal is clear and the graded domain model is inferable from visible evidence under schema version 3.
- The frozen semantic coverage receipt passes, covers every public surface,
  and contains executable dedicated mutants for every mechanism and interaction.
- The mining architecture plan passed before scaffolding, and the finalized
  verifier matrix passed before Oracle/NOP with exact platform-visible IDs,
  cluster mappings and honest cross-cluster witnesses. Counts are diagnostics,
  not proof of semantic breadth or difficulty.
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
- The exact snapshot clears all five quality-panel axes with no blocking
  verdict: no `Minor` or `Major` on `coherent_contract`,
  `correct_reference_solution`, `sound_verifier`, or `deterministic_execution`,
  no `Major` on `protected_ground_truth`, and no axis left undecided.
- Exactly two valid fresh attempts exist and zero or one solved the task. At
  least one trustworthy semantic failure provides a local difficulty signal,
  which remains provisional against the platform's 3-of-8-failure gate.
- The role receipt and final probe evidence prove one persistent builder, one
  fresh reviewer identity covering contract and final review, one distinct
  auditor identity, and exactly two valid blind-solver results. Failed attempts
  and corrective follow-ups are retained without a session-count ceiling.
- The quota ledger hash-binds builder critiques and independent orchestrator
  adjudications for both `contract_review` and `final_review`.
- The audit ledger records every actual model turn, enforces Sol-medium for
  `gpt-5.6-sol` medium for every Codex subagent or Opus 5 medium for every
  Claude subagent. It enforces no turn, remediation, session, or candidate cap,
  and passes pre-solver and handover checks.
- Union coverage, common misses, and failure geometry are retained for diagnosis
  but never block a valid `0/2` or `1/2` CORE+ candidate.
- The pre-freeze task-tree style audit and post-probe submission-only style
  audit are both clean and hash-bound to their exact surfaces.
- `rubric-coverage.md` has no partial or uncovered contract rows, and
  `rubric-check.json` passes while hash-binding both that matrix and the exact
  current submission packet. Portfolio warnings have a recorded adjudication.
- `workspace/submissions/<slug>.zip` exists and matches the final task state.
- `workspace/submissions/SUBMISSION-<slug>.md` exists and is accurate.
- The final `workspace/reports/<slug>/handover.json` is schema version 2,
  hash-binds every required evidence file, and says `candidate_ready` after a
  successful `scripts/batch-handover.py` run.

Do not count rejected, infrastructure-failed, ambiguous, locally all-pass, or
merely packaged candidates. A trustworthy split is valid Terminus 3 evidence.

For `panel_ready`, use the acceptance and truthful-label rules in
`execution-profiles.md`; do not call this campaign gate or
`batch-handover.py`.

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
- the two probe run results;
- provisional local tier signal;
- ZIP path;
- submission file path;
- final ZIP SHA-256 and handover receipt path.

Also list every qualified discarded candidate and its concise rejection reason;
distinguish verified results from unavailable external checks. Report the
unbounded candidate-attempt count, established/derived attempt counts, accepted tracks,
pattern IDs, and any non-blocking rolling-portfolio advisories. For every
derived attempt, include its `X-*` ID and one-sentence non-equivalence rationale.
