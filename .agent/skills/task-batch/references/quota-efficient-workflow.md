# Unbounded-Attempt Batch Workflow

Use this policy for every `task-batch` run. It supplements the quality gates;
it never weakens fairness, verifier isolation, or empirical difficulty.

## Model routing

- Codex: use `gpt-5.6-sol`, medium, for builder, fairness reviewer, both blind
  solvers, and consolidated auditor.
- Claude Code: use Opus 5, medium, for every role.
- The reviewer is one fresh collaboration subagent reused for two turns. The
  auditor is one distinct required independent subagent.
- Deterministic scanning, materialization, verifier execution, packaging, and
  handover do not need a model turn.
- Check the execution surface for each role actually requested. If it cannot
  expose the requested profile, stop that role as unavailable. Do not silently
  substitute Terra or another model.
- Record the actual model on every turn. A follow-up to an existing session is
  a new model turn even though the role identity did not change.

The exact provider credit balance is not observable from repository scripts.
The turn ledger is an immutable execution audit, not a quota or a claim about
the provider's remaining credits.

## Builder compute envelope

The turn ledger does not cap compute inside one long model turn. Before every
builder invocation, follow
[`builder-quota-hooks.md`](builder-quota-hooks.md): validate the Codex/Claude
hook setup, create a stage-specific context packet, and open or transition the
single-candidate lease. Stage A contains mining plus the exact canonical-image
source smoke. Stage B scaffolding starts only in a new counted follow-up after
the smoke receipt passes. Later scaffold, Oracle/verifier, and remediation
stages also use separate bounded turns.

The orchestrator checks the lease at most every 60 seconds while waiting and
interrupts the exact builder after its deadline. Close the lease immediately
on rejection; never continue the same turn with a replacement candidate.
Record every infrastructure repair. Retry without an internal attempt cap;
reject only when the source or environment is fundamentally unusable or the
workflow cannot make evidence-based progress.

Use this cost-first stage order inside the builder session:

1. Mine and source-smoke.
2. Build the complete task-visible contract, verifier, and Oracle.
3. Stabilize each mutant with targeted witnesses.
4. Run complete strict Oracle/NOP/noexec and mechanical quality gates.
5. Run reviewer pass 1 and resolve/recheck findings until green.
6. Reuse the reviewer for pass 2 and resolve/recheck findings until green.
7. Run the mandatory auditor; resolve/recheck findings until green or
   fundamentally blocked.
8. Run counted blind probes; run Harbor only for shortlisted candidates.

Do not launch reviewers or solvers against incomplete Oracle/NOP or quality
evidence. Any task change stales and regenerates the affected receipts.

The reviewer and mandatory auditor follow
[`single-reviewer-workflow.md`](single-reviewer-workflow.md). Bind their actual
runtime, model, session, and transcript receipts into `quota-ledger.json`.

## Model-turn accounting

Record every external model turn, including failed, interrupted,
usage-limited, and superseded turns. Do not impose a per-candidate, batch-wide,
turn, session, remediation, retry, or candidate-attempt cap. Continue with the
same builder/reviewer/auditor identities until each required gate passes or an
evidence-backed fundamental blocker is established. Invalid solver attempts
are recorded and replaced; only two valid solver results enter difficulty
classification.
- Deterministic metadata, hash, receipt, packaging, and verifier work belongs
  to the orchestrator. Never invoke a model merely to close or rebind a
  receipt.

Maintain `workspace/reports/<slug>/quota-ledger.json` and validate it with:

```bash
python3 .agent/skills/task-batch/scripts/quota_guard.py \
  workspace/reports/<slug>/quota-ledger.json --phase pre-solver
```

Minimal shape:

```json
{
  "schema_version": 3,
  "task_slug": "tbrain-example",
  "role_policy": "fixed_roles_unbounded_v3",
  "remediations": {"reviewer": 0, "auditor": 0},
  "role_lease_receipts": [],
  "review_adjudications": [
    {
      "phase": "contract_review",
      "builder_critique": {"path": "builder-critique-contract.json", "sha256": "<sha256>"},
      "orchestrator_adjudication": {"path": "orchestrator-adjudication-contract.json", "sha256": "<sha256>"}
    },
    {
      "phase": "final_review",
      "builder_critique": {"path": "builder-critique-final.json", "sha256": "<sha256>"},
      "orchestrator_adjudication": {"path": "orchestrator-adjudication-final.json", "sha256": "<sha256>"}
    }
  ],
  "mechanical_gates": {
    "instruction_preflight": {"status": "pass", "evidence": "instruction-preflight.log", "sha256": "<sha256>"},
    "client_scanner": {"status": "pass", "evidence": "client-scanner.json", "sha256": "<sha256>"},
    "strict_preflight": {"status": "pass", "evidence": "probe-preflight.json", "sha256": "<sha256>"},
    "artifact_independence": {"status": "pass", "evidence": "artifact-independence.json", "sha256": "<sha256>"},
    "anti_cheat": {"status": "pass", "evidence": "anti-cheat.log", "sha256": "<sha256>"}
  },
  "turns": [
    {
      "turn_id": "builder-1",
      "role": "builder",
      "model": "gpt-5.6-sol",
      "reasoning_effort": "medium",
      "status": "complete",
      "execution_surface": "collaboration_subagent",
      "context_mode": "informed",
      "purpose": "design_build",
      "report_inputs": [
        {"kind": "durable_memory", "path": "../../../AGENTS.md", "sha256": "<sha256>"},
        {"kind": "pattern_catalog", "path": "../../../.agent/skills/task-miner/frontier_task_design_patterns.md", "sha256": "<sha256>"},
        {"kind": "batch_portfolio", "path": "../batches/<batch-id>.json", "sha256": "<sha256>"}
      ]
    }
  ]
}
```

Every agent invocation and every `followup_task` appends a turn before the
next invocation starts. Never rewrite or delete an earlier turn to make the
audit pass.

Every role uses `execution_surface: "collaboration_subagent"`. Append every
invocation or follow-up before launch and record its actual runtime/model.

## Builder context and feedback critique

The builder is deliberately **not fresh-context**. Use one persistent runtime-
specific session with `context_mode: "informed"`. Before proposing a
candidate, make it read hash-recorded inputs for:

- the durable `AGENTS.md` campaign memory;
- the current batch portfolio/design signatures;
- relevant prior rejection or probe reports when they exist.

It must then record and hash-bind the pattern-blind domain-crux card. Only after
that checkpoint may it read the frontier pattern catalog to classify the
design or derive a structural transformation. Record the catalog as a separate
post-crux context input so the ordering is auditable.

Do not expose these materials to the reviewer or blind solvers. Those roles
remain fresh-context; the mandatory consolidated auditor remains independent.

Send reviewer/auditor reports back to the same builder session for remediation.
Before editing, require a JSON critique receipt with one row per finding:
`finding_id`, `disposition` (`accept`, `challenge`, or `partial`), concrete
`evidence`, and intended `action`. A challenge must cite task/report evidence;
it is not permission to ignore a gate. The orchestrator resolves any disputed
blocking finding before allowing the task to proceed. Save a separate
orchestrator adjudication after each of the two required reviewer turns.

## Contract-stage gates before reviewer pass 1

Do not launch the reviewer until these cheap deterministic checks
have real evidence:

1. `instruction_preflight.py` passes.
2. `review_task.py <task-folder> --json --mechanical-only` has zero blockers.
   This first scanner run does not use `--manual-review-pass`; it intentionally
   defers only the external reviewer/auditor receipts until those independent
   roles have run. The later folder and ZIP scans use full scope.
3. The canonical source smoke passes, and static checks confirm the planned
   candidate demotion, verifier separation, private scratch, and process-group
   cleanup. Full Docker proof is intentionally deferred until the contract is
   stable.
4. The targeted witnesses' expected values are independently grounded. A second
   implementation, upstream capture/reference, hand-derived fixture, or
   metamorphic invariant must support every artifact field; circular
   self-consistency is not evidence.
5. A schema/type manifest covers every verifier-read public field, including
   array versus scalar shape, nullability, encoding, timestamp precision, and
   canonical ordering where observable.

After reviewer pass 1 closes and the complete implementation is stable, run the full
strict preflight, artifact-independence, and anti-cheat gates before the
reviewer pass 2 and counted probe. Record both the early contract-stage
checks and the later full gates under `mechanical_gates` in the quota ledger.
Each entry contains `status: "pass"`, an evidence path, and its SHA-256.

## Full-run discipline

- Debug Oracle behavior with the smallest targeted witness that reproduces the
  issue. Do not run Oracle/NOP/noexec across the complete matrix until targeted
  Oracle and NOP behavior are green.
- Debug a mutant against its targeted kill and one unrelated retained-pass
  witness. Promote it to the full campaign only after its anchor and geometry
  are correct.
- For a stable snapshot, run strict Oracle/NOP/noexec once and each accepted
  mutant/wrong solution once. A semantic edit stales that evidence and permits
  one regenerated set; infrastructure retries must reuse the same task hash and
  be recorded separately.
- Harbor is post-shortlist. Never run repeated Harbor Oracle/NOP pairs while a
  candidate is still undergoing reviewer, mutation, or auditor remediation.
- Remediation packets are delta-first: critique, changed task-visible files,
  affected witnesses, and an index of prior evidence hashes. Do not copy raw
  CTRF/log bodies or vendored source trees into model context unless the role
  needs those exact bytes.

## Editorial changes after review

Do not rerun the full fairness cohort for an edit that is provably mechanical:
whitespace, Unicode normalization, punctuation, or an allowlisted lexical
substitution that leaves the V3 success-surface and inference-family mappings
unchanged. Re-run the deterministic checks, rebind hashes, and record one
`editorial_rebind` event.

If a change can alter a requirement, constraint, evidence source, arbitrary
convention, public interface, or interpretation, it is semantic. Re-run the
affected fairness/audit gate. When uncertain, classify it as semantic.

## Incremental handover

Finish and hand over each accepted task immediately. The batch index uses
schema version 2 and may have `status: "building"` with fewer than
`expected_count` slugs. Invoke handover with `--incremental-batch`.

When a later task is added, compare it against every already accepted task.
Reject the new task on a diversity collision; do not invalidate an earlier
accepted task. Regenerate pairwise design receipts and rerun the mechanical
handover command for the affected receipts only. Do not rerun fairness reviews
or blind solves when the task snapshot is unchanged.

At `expected_count`, set the batch index to `status: "complete"`, validate the
schema-v3 adaptive candidate ledger and its accepted subset, and rerun handover
without `--incremental-batch` to seal the final batch index. Do not enforce an
exact established/derived output mix.
