# Batch execution profiles

Choose one profile before Stage A and record it in the batch index. Do not run
the full campaign and label missing role receipts as expected failures.

## `campaign_ready` (explicit opt-in)

Use only when the user explicitly asks for the full campaign, measured difficulty
beyond CORE+, or `candidate_ready`.
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
2. Run `terminus-regular-task-authoring/scripts/panel_precheck.py --design-only`
   before scaffolding. Reject a disconnected core or serialization-only bundle.
3. Run relevant deterministic structure, isolation and cloud-compat checks.
4. Run exact local Docker Oracle=1, NOP=0 and noexec Oracle=1, then require a
   passing snapshot-bound `panel_precheck.py --full` result. This lightweight
   closure includes natural wrong-path and harness-bypass evidence but is not a
   campaign mutation sweep or difficulty measurement.
5. Freeze one snapshot and run one ten-reviewer discovery panel: five axis
   packets, two fresh independent reviewers each.
6. If needed, adjudicate all findings, make one consolidated remediation batch,
   and rerun affected checks plus one full Oracle/NOP/noexec closure.
7. Run one fresh ten-reviewer clearance panel. Five adjudicated `None`
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

## `builder_certified` (default)

Selected by a bare `task-batch N`. Task creation without a quality panel. One persistent
builder, **one** reviewer, and the blind solve probe; no ten-reviewer panel, no
fairness reviewer, no consolidated auditor.

The trade is deliberate and must be stated in every report: the five axes are
covered by executable receipts plus one reviewer, not by ten isolated reviewers.
This lowers cost by roughly an order of magnitude and raises the chance of a
platform return. It is not a claim that the panel was satisfied.

Required path:

1. Mine and scaffold against the bounded scope ledger, then write the obligation
   manifest including its `closure`, `determinism` and `expected_source` fields.
2. `panel_precheck.py --design-only`. Reject a disconnected core before scaffold
   expansion.
3. Build the contract, the independent expectation model, then the Oracle — **in
   that order**. An expectation written after the reference tends to copy it.
4. Deterministic closure, every result written as a receipt:
   - `preflight.sh --strict` (layout, Docker, isolation, Oracle=1, NOP=0, noexec)
   - `preflight.sh --determinism` (repeat runs agree)
   - `independence_check.py` (the expectation model does not import the package)
   - `wrong_path_runner.py` for every core obligation (reward 0, its own witness
     fails, controls pass)
   - `panel_precheck.py --full` on the exact snapshot
5. One reviewer, per [single-reviewer-workflow.md](single-reviewer-workflow.md):
   `contract_review` blind to `tests/` and `solution/`, then `final_review` on
   the frozen snapshot.
6. Blind solve probe, two valid solvers. **The bar is CORE+: at most one of the
   two succeeds.** One success and one failure is accepted; do not keep hardening
   a task to chase `advanced` or `frontier`, and do not reject a candidate for
   landing at CORE. Difficulty stays unmeasured either way — this is a local
   signal, not a tier.

   Read the failures for cause before accepting the number. A solver that could
   not infer a convention is contract evidence, and a solver rejected while
   contract-valid is verifier evidence. Both are defects that must be repaired
   even when the count already clears the bar; neither counts as difficulty.

   If both solvers succeed, the task is under the bar. Deepen the causal coupling
   of the existing core rather than bolting on unrelated surface.
7. Package as `builder_certified`.

The builder never asserts a gate result. Every claim in the report must name a
receipt file bound to the snapshot hash; a gate with no receipt is not run.

When a gate fails and the builder believes the gate is wrong, record a
`documented_exception` in the manifest with the reason and the contract citation.
Never quietly edit the task to satisfy a rule you think is mistaken — with no
panel above it, a wrong gate silently rewrites correct work.

`builder_certified` is not `local_panel_cleared`, `candidate_ready`, a measured
tier, or guaranteed platform acceptance.

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
