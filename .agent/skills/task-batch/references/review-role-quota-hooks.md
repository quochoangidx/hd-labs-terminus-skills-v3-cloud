# Fairness and Auditor Quota Hooks

Fairness reviewers and the consolidated auditor are Luna Codex tasks. They use
Codex `SessionStart`, `PreToolUse`, and `Stop` hooks through
`review_role_guard.py`. Do not route these roles through Claude or substitute a
different model when Luna is unavailable.

The guard is additive to model-turn accounting without imposing a fixed
per-candidate turn cap. It enforces exactly two
fairness leases and one auditor lease; reviewer `high` and auditor `max`
routing; 12 minutes/12 tool calls per fairness phase; 18 minutes/20 tool calls
per auditor phase; and read-only operation. Fairness packets cannot expose
`AGENTS.md`, builder receipts, critique, prior rejections, `solution/`, or
`tests/`. Each reviewer permits at most one `re_review`; the auditor permits at
most one `re_audit` and reuses its session for `post_probe`.

Hooks cannot cancel a model request that is still thinking. While waiting, the
orchestrator calls `review_role_guard.py check` at intervals no longer than 60
seconds and stops the exact Codex task when a lease expires.

## Fairness pair

Materialize a sanitized task-visible directory containing `instruction.md`,
the agent-visible repository/evidence, and nothing from `tests/`, `solution/`,
builder reports, or intended mechanisms. Then create the shared packet:

```bash
python3 .agent/skills/task-batch/scripts/role_context_packet.py \
  --role fairness_reviewer --phase initial --task tbrain-example \
  --input instruction=workspace/review-packets/tbrain-example/instruction.md \
  --input task_visible_tree=workspace/review-packets/tbrain-example/visible \
  --output workspace/reports/tbrain-example/fairness-initial-packet.json

python3 .agent/skills/task-batch/scripts/review_role_guard.py open \
  --role fairness_reviewer --phase initial --task tbrain-example \
  --packet workspace/reports/tbrain-example/fairness-initial-packet.json \
  --count 2
```

Open the leases immediately before creating the two Luna-high Codex tasks.
Create only that pair until both `SessionStart` hooks claim distinct leases.
The guard refuses a second unclaimed/active Luna cohort in the same worktree
because `SessionStart` has no orchestrator-supplied lease token. Parallel
cohorts require separate worktrees and separate `TERMINUS_ROLE_LEASE_DIR`
values.

After both reviewers stop, either close both leases or, after the one permitted
builder remediation, create a `re_review` packet containing the sanitized
`remediation_summary` and transition each existing lease before messaging the
same reviewer task:

```bash
python3 .agent/skills/task-batch/scripts/review_role_guard.py transition \
  --lease tbrain-example-fairness_reviewer-1 --phase re_review \
  --packet workspace/reports/tbrain-example/fairness-re-review-packet.json
```

Run `close --lease ...` after the final fairness verdict. A new reviewer task
is not a valid remediation replacement.

## Consolidated auditor

Create one `pre_freeze` packet from the task folder and mechanical receipts,
then open exactly one lease with `--role consolidated_auditor --count 1` before
creating the Luna-max task. The auditor may inspect verifier, Oracle, semantic
coverage, and packaging evidence included in its packet, but not campaign
memory or builder critique/rejection reports.

After an optional single `re_audit`, preserve the same task/session. Following
the blind probes, create a `post_probe` packet containing the final task, probe
report, and submission packet, transition the same lease, and message the same
auditor task. `Stop` marks `post_probe` complete automatically.

## Ledger binding

Every lease mirrors a receipt under
`workspace/reports/<slug>/role-leases/`. Add the final three receipt paths and
SHA-256 values to `quota-ledger.json` as `role_lease_receipts`.
`quota_guard.py --phase pre-solver` requires two completed fairness leases and
one phase-complete pre-freeze auditor lease whose session IDs match the actual
Codex task turns. `--phase handover` additionally requires that same auditor
lease to finish `post_probe`.

`review_role_guard.py check` persists an overdue awaiting/active lease as
`expired` in both runtime state and its receipt. This prevents an abandoned
cohort from blocking every later batch while preserving the failed lease as
quota evidence; never delete or hand-edit the stale receipt.
