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

Selected by a bare `task-batch N`. One persistent builder, **one** reviewer, one
adversarial verifier reviewer, the blind solve probe, and a pre-submission
quality panel (full five-axis discovery, clearance on changed axes); no fairness
reviewer, no consolidated auditor.

The five axes are covered first by executable receipts plus one reviewer, then,
once the probe has shown the task clears CORE+, by a ten-reviewer discovery
panel, so the findings the platform panel would return are found and repaired
before upload. The probe runs first because it is the cheaper filter: in
task-batch 3 all four first probes came back 2/2, and a panel spent before
hardening is spent on a snapshot about to change. Clearance re-runs every axis
that had a finding or whose visible files the repair changed; a repair touching
`tests/` or `instruction.md` therefore re-runs most or all of them, so budget
10–20 panel reviewers per task. The panel is local and bounded; it is not a
claim that the platform panel will be satisfied.

A return is not cheap either. Both `builder_certified` tasks submitted on
2026-09-24 (`tbrain-health-claim-cost-sharing`, `tbrain-intermittent-infusion-regimen`)
came back from the quality panel with 37 findings each, 32–34 of them
`sound_verifier`, before difficulty was measured. Every gate below had been
green. The builder's receipts show that the task agrees with itself; they do not
show that the verifier rejects wrong work the builder did not think of. Step 5b
exists for that gap, and step 8 runs the platform's own five axes before upload.

Required path:

1. Mine and scaffold against the bounded scope ledger, then write the obligation
   manifest including its `closure`, `determinism` and `expected_source` fields.
2. `panel_precheck.py --design-only`. Reject a disconnected core before scaffold
   expansion.
3. Write the contract (authority plus instruction) and answer the five axes at
   scaffold time with the
   [scaffold checklist](../../terminus-regular-task-authoring/references/scaffold-five-axis-checklist.md):
   formula domains, the state table, the global-claim check, and the exact
   conventions. Then run the reviewer's `contract_review` turn
   ([single-reviewer-workflow.md](single-reviewer-workflow.md)), blind to tests
   and solution, and repair the contract **before any verifier exists**. The
   same turn scores the
   [solver-path screen](../../task-miner/solver_path_screen.md) on the written
   instruction; `self_verification_resistance` of 2 or lower stops here to
   redesign the causal core or replace the candidate, the cheapest point to
   catch a task that will come back 2/2. One redesign is allowed; a second score
   of 2 or lower replaces the candidate. A
   contract finding after the receipts forces the whole wrong-path matrix to
   rerun.
4. Build the independent expectation model, then the Oracle, **in that order**.
   An expectation written after the reference tends to copy it. Fuzz the model
   against the Oracle before writing tests, fix the harness shape, and write one
   named test per rule, each run in a state where its violation shows. Score every
   wrong path and one or two alternative correct implementations locally.
5. Deterministic closure, every result written as a receipt:
   - `preflight.sh --strict` (layout, Docker, isolation, Oracle=1, NOP=0, noexec)
   - `preflight.sh --determinism` (repeat runs agree)
   - `independence_check.py` (the expectation model does not import the package)
   - `wrong_path_runner.py` for every core obligation (reward 0, its own witness
     fails, controls pass)
   - `panel_precheck.py --full --profile builder_certified` on the exact snapshot
     (bookkeeping rows such as graph shape and matrix labels report as warnings;
     closure, named silent cases, cited conventions and wrong paths still block)
   5b. **Adversarial verifier pass**, on the closure snapshot. A fresh reviewer
   session, separate from the contract/final reviewer and the builder, gets
   `instruction.md`, `environment/` and `tests/`. It does not see `solution/`,
   the builder's wrong paths, the manifest or the reports. It writes 10–15
   plausible wrong submissions, each contract-valid except for one rule, and aims
   them at the shapes the scaffold checklist §1 and §4 list: undeclared regions,
   job shapes, loose comparators, promised helpers. It also writes one or two
   contract-valid alternatives. Save each submission with its receipt under
   `workspace/reports/<slug>/adversarial/`; revisions rerun them as a regression
   suite. The builder runs each through
   `wrong_path_runner.py`. A wrong submission scoring reward 1, or a valid
   alternative scoring 0, is a finding, and it is answered the §11 way: back the
   rule with a witness, or narrow the promise. Then rerun the affected closure
   gates. This mirrors the panel's own "confirmed by running the grader" step
   (`docs/testing-and-validation/quality-panel-judge-guide.md`) and the docs'
   pre-submission rule that a deliberately wrong solution must fail
   (`docs/understanding-tasks/what-makes-a-good-task.md`).
6. The same reviewer's `final_review` on the frozen snapshot, with full task
   visibility. A repair after it reruns the affected gates and gets a targeted
   recheck in the same session.
7. Blind solve probe, two valid solvers, prepared with `probe.py prepare --exploratory`
   (a counted prepare demands campaign receipts this profile never produces). **The bar is CORE+: at most one of the
   two succeeds.** One success and one failure is accepted; do not keep hardening
   a task to chase `advanced` or `frontier`, and do not reject a candidate for
   landing at CORE. Difficulty stays unmeasured either way — this is a local
   signal, not a tier.

   Read the failures for cause before accepting the number. A solver that could
   not infer a convention is contract evidence, and a solver rejected while
   contract-valid is verifier evidence. Both are defects that must be repaired
   even when the count already clears the bar; neither counts as difficulty.

   If both solvers succeed, the task is under the bar. Deepen the causal coupling
   of the existing core rather than bolting on unrelated surface, rerun steps 5–6
   on the new snapshot, and probe again with a fresh pair. This strengthening
   happens **once**: a second 2/2 rejects the candidate (as in
   `task-local-solve-probe`). No panel runs until a probe clears CORE+.

   Every probe pair gets its own output directory: archive the prior pair and
   pass `--output workspace/local-solve-probes/<slug>-cycle-<N>`, because
   `probe.py` refuses a directory that holds another snapshot.

   Freeze `task.toml` submission prose (`difficulty_explanation` and the other
   explanation fields) before step 8. The `coherent_contract` and
   `deterministic_execution` packets include it, so a prose edit after the panel
   invalidates those verdicts.
8. **Pre-submission quality panel**, in `task-quality-panel-judgement` creation
   mode, on the snapshot after any step-7 repairs, once a fresh
   `panel_precheck.py --full --manifest workspace/reports/<slug>/panel-precheck-manifest.json --profile builder_certified`
   passes on it.
   - Discovery: all five axes, two fresh reviewers each, ten responses collected
     before any edit.
   - Repair: deduplicate retained findings by root cause and answer them in
     **one** consolidated batch through `task-revise-flag-remediation` (back the
     promise or stop promising it), then rerun the affected closure gates.
   - Clearance: run `panel_gate.py clearance-axes` against the discovery packet
     manifest, passing each axis with a retained blocking finding and
     `--discovery-report` so `Unsure` or incomplete discovery axes are re-run
     too. Spawn two new
     reviewers for every axis it lists; the axes it carries keep their discovery
     verdict because none of their visible files changed. Skip clearance when
     discovery is five-axis non-blocking. A blocking clearance stops with
     `rescope_required`; there is no third round.
   - Re-probe: if the batch removed or narrowed an obligation, or changed graded
     behaviour of the core, the step-7 signal no longer describes the task. Probe
     once more with a fresh pair on the cleared snapshot. A 2/2 here means the
     cut took the hard thing: stop with `rescope_required` rather than harden a
     panel-cleared snapshot. Editorial or witness-only repairs keep the step-7
     signal. A defect found by reading a re-probe failure for cause also stops
     with `rescope_required`: fixing it would need a third panel round.
9. Build the panel receipt with `panel_gate.py write-report <task>
   --adjudication <adjudication.json> --report <report.json>`: it reads the raw
   reviewer files, computes completeness and the snapshot hash, refuses a verdict
   below a raw severity without a `downgrade_reason`, and then runs `check`.
   Never write `report.json` by hand. Package through
   `scripts/preflight.sh <task> --strict --emit-zip <zip> --panel-report <report.json>`,
   where a failing `panel:receipt` row blocks the ZIP. Then report it
   as `builder_certified`, reporting each axis verdict with the snapshot it was
   reviewed on. Any later semantic edit makes that check fail until the changed
   axes are cleared again.

The builder never asserts a gate result. Every claim in the report must name a
receipt file bound to the snapshot hash; a gate with no receipt is not run.

When a gate fails and the builder believes the gate is wrong, record a
`documented_exception` in the manifest with the reason and the contract citation.
Never quietly edit the task to satisfy a rule you think is mistaken — a wrong
gate silently rewrites correct work, and the panel reviewers never see the
manifest to notice it.

`builder_certified` is not `local_panel_cleared` (its clearance covers only
changed axes, not a fresh five-axis panel), `candidate_ready`, a measured tier, or guaranteed
platform acceptance.

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
