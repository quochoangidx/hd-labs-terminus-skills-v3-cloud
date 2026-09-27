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
early skeleton probe pair, and a narrow pre-submission panel; no fairness reviewer,
no consolidated auditor, no separate adversarial reviewer.

**Lean route (user decision, 2026-09-26: cut model sessions without losing what
catches returns).** A task costs about 7–10 model sessions instead of 15–27:
builder, reviewer, two skeleton solvers, four panel reviewers, and two clearance
reviewers on a tests-only repair. Where each cut comes from, and why it is safe:

- **Probe early, not late.** Most candidates fail by collapsing at 2/2 (all four
  task-batch-3 first probes), so the pair runs on a skeleton right after the model
  and Oracle exist (step 4), before the verifier and gates are built. The final
  difficulty check (step 7) rescores the preserved skeleton diffs against the
  finished verifier instead of spawning a new pair; a fresh pair runs only when
  the agent-visible contract changed after the skeleton. The skeleton screen
  predicted the platform result for crop-water, IFTA and royalty.
- **No separate adversarial reviewer.** The builder runs the Sound Verifier class
  ladder (blueprint §5, C1–C18) as scripted Oracle mutants plus one or two
  contract-valid alternatives. Those classes are what every accepted task's panel
  returns were about.
- **Panel on the two axes that fail.** Discovery spawns reviewers for
  `sound_verifier` and `correct_reference_solution` only. The other three axes are
  carried by receipts (`panel_gate.py` `source: "gate"`): `coherent_contract` by
  the blind `contract_review`/`final_review` adjudication, `protected_ground_truth`
  by the strict preflight static gates plus the candidate-read test,
  `deterministic_execution` by `preflight.sh --determinism`. In the six accepted
  tasks those three axes were clean in almost every return; the one ground-truth
  Major (a graded visible sample) and the correct-reference overflow class are now
  gates. Run a full five-axis panel only when the user asks, or when the task's
  contract shape is new to the team (a first task in a new category/work surface).
- **Clearance by what changed.** `panel_gate.py clearance-axes` now re-runs an
  axis only when a file that axis judges changed: a tests-only repair re-runs
  `sound_verifier` alone; `tests/Dockerfile`/`tests/test.sh` add ground truth and
  determinism; `solution/` adds reference and determinism; `instruction.md` or
  `environment/` re-run everything. Genomic (6 rounds), crop (4) and rebill (4)
  repaired tests only and never broke another axis. `--strict-visibility`
  restores the old rule.

The panel is local and bounded; it is not a claim that the platform panel will be
satisfied. If Sound Verifier returns start rising again, go back to the full
five-axis panel and the adversarial reviewer.

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
   instruction. Only `self_verification_resistance` 1 stops here (every task scored
   1 collapsed); a score of 2 is advisory and the skeleton pair decides, because
   rejecting at 2 also drops resisting tasks (workers-comp scored 2 and cleared
   CORE+; user decision 2026-09-27: loosen screens so candidates reach the probe). A
   contract finding after the receipts forces the whole wrong-path matrix to
   rerun.
4. Build the independent expectation model, then the Oracle, **in that order**.
   An expectation written after the reference tends to copy it. Fuzz the model
   against the Oracle.

   4a. **Skeleton probe (mandatory, before any verifier).** Prepare two solve
   copies with `probe.py prepare --exploratory` from `instruction.md`,
   `environment/` and the shipped package, run two fresh `terminus-probe` solvers
   (Opus 5, launched without a `model` argument), and score each diff with the
   model on generated inputs (`task-local-solve-probe` *Exploratory skeleton
   mode*). **Run the pair only after `contract_review` has no blocking or
   should-fix finding on the trap wording; never launch it in parallel with the
   review.** A pair run on wording the review then finds ambiguous is discarded
   (batch-8, 2026-09-27: four of five candidates lost a pair this way). **2/2 → one
   strengthening or redesign, then a second 2/2 replaces the candidate.** Allow
   exactly one: it saved workers-comp (2/2 → 1/2) and trace-metal (2/2 → 0/2),
   while repeated rewording after that never did (3PL billing spent six pairs and
   still went 2/2). 0/2 or 1/2
   with semantic failures → continue. A trap every solver misses goes through
   the blueprint §4.3 0/8 screen now, while fixing the contract is still cheap.
   Keep both solver diffs: step 7 rescores them. **A pair discarded as ambiguity
   evidence does not count:** once `contract_review` repairs the wording, run a
   fresh skeleton pair before writing the verifier (trace-metal skipped this and
   first learned how the repaired wording read after the verifier was built).

   Then fix the harness shape and write one named test per rule, each run in a
   state where its violation shows. Score every wrong path and one or two
   alternative correct implementations locally.
5. Deterministic closure, every result written as a receipt:
   - `preflight.sh --strict` (layout, Docker, isolation, Oracle=1, NOP=0, noexec)
   - `preflight.sh --determinism` (repeat runs agree)
   - `independence_check.py --model solution/model.py` (the expectation model
     does not import the package, and it lives in `solution/`, sealing its output
     into `tests/expected/`; a model under `tests/` blocks as `model_in_tests`)
   - `wrong_path_runner.py` for every core obligation (reward 0, its own witness
     fails, controls pass)
   - `panel_precheck.py --full --profile builder_certified` on the exact snapshot
     (bookkeeping rows such as graph shape and matrix labels report as warnings;
     closure, named silent cases, cited conventions and wrong paths still block)
   5b. **Sound Verifier sweep (builder, no extra session).** Run the class ladder
   ([accepted-task blueprint](../../terminus-regular-task-authoring/references/accepted-task-blueprint.md)
   §5, C1–C18) as scripted Oracle mutants with
   `terminus-regular-task-authoring/scripts/sound_verifier_sweep.py` (a JSON
   catalog of edits on top of `solution/fix.patch`; it scores each through
   `wrong_path_runner.py`, checks the alternatives score 1 and lists untouched
   classes, each of which needs a one-line reason): caps,
   lower ends and derived extremes (stated minimum counts, the smallest "above
   nought" value, products of range tops, each run kind's copy of a range),
   cardinalities, floors, float values on a limit (C8: a stated margin, not an
   exact-on-limit promise), integer widths, signs and halves, categorical syntax,
   separated accumulators, envelope cross-products and harness shapes. Each must
   score reward 0 on its own named test; also run one or two contract-valid
   alternatives, which must score 1. A surviving mutant or a rejected alternative
   is answered the §11 way (back the rule with a witness, or narrow the promise),
   then the affected closure gates rerun. Save the mutants under
   `workspace/reports/<slug>/sweep/`; revisions rerun them as a regression suite.
   Before the sweep, run `terminus-regular-task-authoring/scripts/fixture_bounds_check.py`
   with a `ranges.json` listing every range the authority states (both ends, none left
   open) and a small `observe.py` adapter; every `GAP` is a missing fixture or an open end
   to close. Clear the `panel_packet_budget` and `shared_id_stem` warnings of
   `panel_precheck.py` too: the platform panel skips what it cannot read, and reads
   `R507-6`/`R507-17` as a repeated id (worked example:
   `workspace/reports/tbrain-icpms-sop-data-reduction/bounds/`).
6. The same reviewer's `final_review` on the frozen snapshot, with full task
   visibility. A repair after it reruns the affected gates and gets a targeted
   recheck in the same session.
7. **Difficulty check.** Rescore the two step-4a skeleton diffs against the
   finished verifier (`probe.py materialize`/`apply` on each run, then the
   verifier); this costs no model session. Run a **fresh** pair (`probe.py
   prepare --exploratory`, new `--output`) only when `instruction.md`,
   `environment/` or the shipped package changed after the skeleton, or when a
   rescored diff is rejected on a point the contract allows (a verifier defect to
   repair first). **The bar is CORE+: at most one of the two succeeds.** One
   success and one failure is accepted; do not keep hardening
   a task to chase `advanced` or `frontier`, and do not reject a candidate for
   landing at CORE. Difficulty stays unmeasured either way — this is a local
   signal, not a tier.

   Read the failures for cause before accepting the number. A solver that could
   not infer a convention is contract evidence, and a solver rejected while
   contract-valid is verifier evidence. Both are defects that must be repaired
   even when the count already clears the bar; neither counts as difficulty.

   A single trap missed by **both** solvers (and by every earlier pair) is a
   0/8 risk, not a strong signal: royalty's 4/4 local common miss became a platform
   "not passed by any agent run" return, and rebill's and moving-average's did the
   same. Run the blueprint §4.3 screen on it (competing positive enumeration, no
   definitional chain, contrary expert instinct, unnamed shared step, the trap
   inside several tests). Judge each trap on its own, never only the pair's total:
   - **Prefer isolation** (blueprint §4.2 rule 3): keep trap inputs out of broad,
     generated and capacity families when that is cheap, since a trap threaded
     through them multiplies a platform 0/8 across tests. It is not a blocker
     (icpms was accepted with its trap in three tests).
   - A trap missed by every solver on the current contract, or by at least three
     of four local runs, with **two or more** §4.3 flags (for example contrary
     expert instinct plus no isolation) is a 0/8 risk to report with the package,
     not a blocker: the icpms non-detect spike trap had exactly that local profile
     (Opus 5 2/2 missed, contrary instinct, threaded into three tests) and the
     platform accepted the task. Isolate it if that is cheap; answer a real
     platform 0/8 by governing the case, never by disclosing it.
   - Otherwise accept when the misses split across two or more independent
     traps, or when the screen is clean and the trap is isolated in its own test. Probes run on the `opus` alias (Opus 5.5, all probes before
   2026-09-26) did not predict the platform's per-model split or its tier: a local
   1/2 on a one-trap shape came back BASE 7/8. `terminus-probe` is now pinned to
   `claude-opus-5`, the platform's model; launch it without a `model` argument.

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
   - Discovery: `sound_verifier` and `correct_reference_solution`, two fresh
     reviewers each, four responses collected before any edit. The other three
     axes enter the adjudication as `"source": "gate"` with their
     `gate_receipts` (contract/final review adjudication; strict preflight static
     rows and the candidate-read test; `preflight.sh --determinism`). Prepare all
     five packets anyway, so every carried verdict is hash-bound to a snapshot.
   - Repair: deduplicate retained findings by root cause and answer them in
     **one** consolidated batch through `task-revise-flag-remediation` (back the
     promise or stop promising it), then rerun the affected closure gates.
   - Clearance: run `panel_gate.py clearance-axes` against the discovery packet
     manifest, passing each axis with a retained blocking finding and
     `--discovery-report` so `Unsure` or incomplete discovery axes are re-run
     too. Spawn two new
     reviewers for every reviewer axis it lists, and refresh the gate receipts for
     any gate-carried axis it lists; the axes it carries keep their verdict because
     none of the files they judge changed. Skip clearance when discovery is
     non-blocking. A blocking clearance stops with
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
10. **Submission packet (last, once the ZIP is final).** Write the Rubrics block
   with `terminus-rubric-authoring` against the exact ZIP, and put it with the
   Metadata answers in `workspace/submissions/SUBMISSION-<slug>.md`, as the title `# SUBMISSION — <slug>` with its Task, Category and ZIP lines, then `# Metadata` and `# Rubrics`, nothing else (layout in `task-clone` *Submission Explanation Workflow*).
   The four explanations (`difficulty_explanation`, `solution_explanation`, `verification_explanation`, `relevant_experience`) live only in `task.toml` `[metadata]`, which the platform reads from the ZIP; do not write them again into a source draft or the packet (user decision 2026-09-26: generating text that is never pasted only spends quota). Skip this step while the task may still change: a rubric written
   before the last repair has to be rewritten.

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
