# Documented exception: pre-submission panel, correct_reference_solution (builder_certified step 9)

`panel_gate.py write-report` refuses this snapshot: `correct_reference_solution: review incomplete`
(clearance reviewer B marked its input incomplete). The ZIP was therefore built with
`preflight.sh --strict --emit-zip` **without** `--panel-report`. This is a recorded dispute, not a pass.

Axis results on snapshot 25590022...154f:
- coherent_contract, protected_ground_truth, sound_verifier: None, both discovery reviews complete (carried; files unchanged).
- deterministic_execution: None, both clearance reviews complete.
- correct_reference_solution: no defect found by any of four reviewers. Clearance A read all four plans in full: None, complete.
  Discovery A/B and clearance B: Unsure, incomplete, each for one reason: a read-only reviewer cannot sum 715-1413
  transfer costs per day, and the reviewer profile cannot run the checker.

Why the open check is settled by execution:
- strict preflight on this snapshot: Oracle reward 1, all four `test_day_N_plan_meets_target` pass (preflight-final-logs/oracle-ctrf.json);
- solve.sh exits 1 unless the checker reports each plan valid within its target;
- final_review recheck 3 ran the checker on each reference plan: costs equal the targets.

Contract citation: task-batch/references/execution-profiles.md, builder_certified, "When a gate fails and the builder
believes the gate is wrong, record a documented_exception ... Never quietly edit the task." The platform panel can execute
the grader; the local reviewer profile cannot, which is the only source of the incompleteness.
