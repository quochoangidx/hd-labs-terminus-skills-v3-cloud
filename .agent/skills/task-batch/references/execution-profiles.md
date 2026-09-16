# Batch execution profiles

Choose one profile before Stage A and record it in the batch index. Do not run
the full campaign and label missing role receipts as expected failures.

## `campaign_ready` (default)

Use when the user asks for measured local difficulty or `candidate_ready`.
Run the complete task-batch workflow: deterministic checks, inferability and
semantic evidence, required reviewer/auditor roles, blind solve probe,
packaging and handover. Difficulty remains empirical; design-shape counts do
not establish a tier.

## `panel_ready` (explicit opt-in)

Use only when the user explicitly asks to omit difficulty probes and ordinary
fairness/auditor roles while retaining the quality panel. The only model roles
are one persistent builder and the fresh reviewers required by
`task-quality-panel-judgement`.

Required path:

1. Mine and scaffold using the bounded scope ledger. Keep one primary outcome,
   one causal core and supplied/narrow support boundaries.
2. Run `task-quality-panel-judgement/scripts/panel_precheck.py --design-only`
   before scaffolding. Reject a disconnected core or serialization-only bundle.
3. Run relevant deterministic structure, isolation and cloud-compat checks.
4. Run exact local Docker Oracle=1, NOP=0 and noexec Oracle=1, then require a
   passing snapshot-bound `panel_precheck.py --full` result. This lightweight
   closure includes natural wrong-path and harness-bypass evidence but is not a
   campaign mutation sweep or difficulty measurement.
5. Freeze one snapshot and run one eight-reviewer discovery panel.
6. If needed, adjudicate all findings, make one consolidated remediation batch,
   and rerun affected checks plus one full Oracle/NOP/noexec closure.
7. Run one fresh eight-reviewer clearance panel. Four adjudicated `None`
   verdicts with complete coverage permit packaging as `local_panel_cleared`.

Do not run the fairness reviewer, consolidated auditor, blind solver, counted
probe, campaign mutation campaign, semantic-coverage reviewer receipt, rubric
generation, quota/session gate, or `candidate_ready` handover unless separately
requested. The precheck's minimal wrong-path closure and a focused reproduction
needed to adjudicate a panel claim are verifier-quality evidence, not a campaign
mutation campaign or difficulty evidence. Never fabricate or waive a missing
receipt from the other profile.

If discovery is already five-axis non-blocking and the task is unchanged, package it
without a duplicate clearance panel. If clearance is blocking or incomplete,
stop with `rescope_required`; do not enter another repair-panel round. A user
may authorize a new rescope, but it starts from a revised scope ledger and is
not called another clearance of the same contract.

`local_panel_cleared` means the exact snapshot passed the bounded local panel
approximation and deterministic gates. It is not `candidate_ready`, a measured
tier, submit-ready certification, or guaranteed platform acceptance.

## Validation and revision accounting

During a remediation batch, use focused reproductions and affected checks.
Run the full Docker closure once after semantics stabilize; editorial-only
changes use the existing editorial rebind rule. Do not rerun every mutant or
full Docker matrix merely to refresh prose, formatting or archive metadata.

Track separately:

- `semantic_revision`: task-visible or graded behavior changed;
- `package_build`: the same task snapshot was archived again;
- `validation_run`: checks reran without changing the task.

Only a semantic change increments the semantic revision. A rollback records
its source snapshot; repackaging and validation do not create a new task
version.
