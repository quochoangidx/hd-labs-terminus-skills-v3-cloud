# Quota-Efficient Batch Workflow

Use this policy for every `task-batch` run. It supplements the quality gates;
it never weakens fairness, verifier isolation, or empirical difficulty.

## Model routing

- Candidate design and builder: `gpt-5.6-sol`, `reasoning_effort: medium`.
- Fairness reviewers and consolidated auditor: `gpt-5.6-luna`,
  with `reasoning_effort: high` for fairness reviewers and
  `reasoning_effort: max` for the consolidated auditor. Run these roles as
  independent Codex tasks, not collaboration subagents; follow
  `luna-thread-orchestration.md`.
- Counted blind solvers: `gpt-5.6-sol`, `reasoning_effort: medium`.
- Do not spend Sol turns on prose review, receipt review, or audit. Deterministic
  scanning, materialization, verifier execution, packaging, and handover do not
  need a model turn.
- Check Sol in the collaboration-subagent runtime and Luna in the Codex task
  runtime separately. If either execution surface cannot expose its requested
  profile, stop that role as unavailable. Do not silently substitute Terra or
  another model.
- Record the actual model on every turn. A follow-up to an existing session is
  a new model turn even though the role identity did not change.

The exact provider credit balance is not observable from repository scripts.
The turn ledger is therefore a fail-closed planning floor, not a claim about
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
Record every infrastructure repair. The third attempt rejects the candidate.

Fairness reviewers and the auditor use the separate Codex-only procedure in
[`review-role-quota-hooks.md`](review-role-quota-hooks.md). Open the exact Luna
cohort leases before creating its tasks, poll their deadlines, and bind their
final receipts into `quota-ledger.json`. Do not run two unclaimed Luna cohorts
inside one worktree; separate worktrees and lease directories are required for
safe cross-task concurrency.

## Model-turn accounting

Record every external model turn, including failed, interrupted,
usage-limited, and superseded turns, but do not impose a fixed per-candidate
turn cap or a synthetic pre-solver turn reserve. Cost boundaries come from the
user's explicit batch-wide candidate/session budget plus the role-specific
stage deadlines, tool-call limits, and remediation caps.

- At most one fairness remediation cycle: one builder repair followed by one
  re-review by the existing fairness pair.
- At most one consolidated-auditor remediation cycle: one builder repair and
  one re-audit by the existing auditor.
- If the same gate still fails, reject the candidate. Do not keep asking the
  same reviewers to reconsider slightly different drafts.
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
  "schema_version": 2,
  "task_slug": "tbrain-example",
  "remediations": {"fairness": 0, "auditor": 0},
  "role_lease_receipts": [
    {"path": "role-leases/tbrain-example-fairness_reviewer-1.json", "sha256": "<sha256>"},
    {"path": "role-leases/tbrain-example-fairness_reviewer-2.json", "sha256": "<sha256>"},
    {"path": "role-leases/tbrain-example-consolidated_auditor-1.json", "sha256": "<sha256>"}
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
budget pass.

Every Luna reviewer/auditor `create_thread` or `send_message_to_thread` also
appends a turn before launch. Set `execution_surface: "codex_thread"`,
`runtime: "codex-thread"`, `session_id` and `thread_id` to the actual thread
ID, and `host_id` to the returned host ID. The builder and blind solvers use
`execution_surface: "collaboration_subagent"`. A client-generated pending ID
does not satisfy thread provenance.

## Builder context and feedback critique

The Sol-medium design/build agent is deliberately **not fresh-context**. Use one
persistent builder session with `context_mode: "informed"`. Before proposing a
candidate, make it read hash-recorded inputs for:

- the durable `AGENTS.md` campaign memory;
- the current batch portfolio/design signatures;
- relevant prior rejection or probe reports when they exist.

It must then record and hash-bind the pattern-blind domain-crux card. Only after
that checkpoint may it read the frontier pattern catalog to classify the
design or derive a structural transformation. Record the catalog as a separate
post-crux context input so the ordering is auditable.

Do not expose these materials to fairness reviewers or blind solvers. Those
roles remain fresh-context; the consolidated auditor remains independent.

Send fairness/auditor reports back to the same builder session for remediation.
Before editing, require a JSON critique receipt with one row per finding:
`finding_id`, `disposition` (`accept`, `challenge`, or `partial`), concrete
`evidence`, and intended `action`. A challenge must cite task/report evidence;
it is not permission to ignore a gate. The orchestrator resolves any disputed
blocking finding before allowing the task to freeze.

## Mechanical gates before reviewers

Do not launch either fairness reviewer until all of these deterministic checks
have real evidence:

1. `instruction_preflight.py` passes.
2. `review_task.py <task-folder> --json --mechanical-only` has zero blockers.
   This first scanner run does not use `--manual-review-pass`; it intentionally
   defers only the external fairness/auditor receipts until those independent
   roles have run. The later folder and ZIP scans use full scope.
3. Strict `scripts/preflight.sh` passes, proving separate agent/verifier images,
   Oracle/NOP, reward-channel isolation, and noexec behavior.
4. The verifier's expected values are independently grounded. A second
   implementation, upstream capture/reference, hand-derived fixture, or
   metamorphic invariant must support every artifact field; circular
   self-consistency is not evidence.
5. The anti-cheat threat model is exercised: candidate code cannot read tests,
   solution, expected outputs, reward files, or verifier-only dependencies;
   only declared artifacts cross into the verifier.

Record these five checks under `mechanical_gates` in the quota ledger. Each
entry contains `status: "pass"`, an evidence path, and its SHA-256. The quota
guard rejects missing, empty, external, or stale evidence.

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
