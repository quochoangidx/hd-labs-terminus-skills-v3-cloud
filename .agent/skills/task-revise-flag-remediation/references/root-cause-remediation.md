# Root-cause remediation

Use this only after the discovery pass has finished on every axis in the panel's scope (the two reviewer axes plus gate-carried receipts under the lean `builder_certified` route, all five in a full panel) and the user asked
to update the task, or to interpret the root-invariant map when consolidating
a review-only report (without authorization to edit). The goal is to close each violated semantic invariant, not to
make the reported example pass.

## Build the root-invariant map

Create one group for findings that share the same authority and failure
mechanism. Do not group findings merely because they touch the same file.
Conversely, when a report repeats the same mutation or reachable path in two
numbered findings, keep both finding IDs but map them to one root group and one
reproduction/closure pair. Duplicate prose does not justify duplicate tests or
an expanded obligation set.

Each group must record:

```json
{
  "group_id": "ROOT-1",
  "finding_ids": ["CRS-1"],
  "affected_axes": ["correct_reference_solution"],
  "root_invariant": "general rule that must hold",
  "authority": ["agent-visible contract or external invariant citation"],
  "failure_mechanism": "why the current design violates the invariant",
  "implementation_sites": ["every reachable site implementing the rule"],
  "variant_dimensions": ["record type", "scope", "time", "state", "boundary"],
  "sibling_variants": ["same invariant through another branch or subtype"],
  "interaction_variants": ["combination with another independent rule"],
  "repair_options": {
    "repair": "fix the shared implementation boundary without changing the contract",
    "narrow": "restrict an unnecessary domain or promise coherently",
    "remove": "drop a separable non-core feature and its dependent surface",
    "expand": "add justified evidence, logic or discriminating checks for a necessary promise",
    "retire_or_redesign": "stop pursuing this design if no credible bounded repair remains"
  },
  "decision": "repair | narrow | remove | expand | retire_or_redesign",
  "decision_reason": "retained task value versus coupling, validation cost and regression risk",
  "prior_attempts": ["snapshot and evidence of what did or did not close this root cause"],
  "stop_or_switch_condition": "observable failure of this repair strategy, not a model vote count",
  "chosen_repair_boundary": "one authority point to change",
  "proof_obligations": ["focused reproduction", "property", "mutant"],
  "regression_risks": {
    "coherent_contract": [],
    "correct_reference_solution": [],
    "protected_ground_truth": [],
    "sound_verifier": [],
    "deterministic_execution": []
  }
}
```

Derive missing map fields from the frozen task with concrete citations. Do not
ask reviewers for iterative follow-ups and do not start editing an incomplete
group.

## Choose the repair boundary

Apply [bounded task design](../../terminus-regular-task-authoring/references/bounded-task-design.md)
to the existing scope ledger: no new promises by default, and every necessary
addition must identify the retained obligation it closes. Report before/after
obligations and witness coverage, not merely test counts or changed lines.

For size-driven simplification, apply
[panel input hygiene](../../terminus-regular-task-authoring/references/panel-input-hygiene.md).
The 800-line warning alone never creates a repair group; retain necessary
evidence and witnesses even when a file stays large.

Choose by task value and evidence, not a fixed shrink-first or add-first order.
Compare the viable alternatives briefly; mark others inapplicable with a reason.

| Choice | Appropriate when |
| --- | --- |
| Repair | A shared validator, selector or transition fixes a necessary invariant with contained regression risk. A slightly larger coherent refactor can be cheaper than many small exceptions. |
| Narrow | An unnecessary domain or promise creates disproportionate ambiguity or cost, and an explicit natural boundary leaves a useful, fair task. |
| Remove | A separable non-core feature has low value and repeated confirmed repair failures or excessive coupling. Remove its contract, implementation and grading obligations together. |
| Expand | A necessary promise lacks authentic evidence, correct logic or a discriminating witness. Add only what closes that gap; do not introduce unrelated features. |
| Retire/redesign | The failing mechanism is central and no credible bounded repair preserves usefulness, fairness and sound verification. Do not keep patching solely because much work has already been spent. |

Assess expected verification cost, changed authorities, interaction fan-out and
new special cases, not just changed lines or fixture count. Mixed choices across
root groups are allowed within the same consolidated batch.

Do not add a condition keyed to a fixture, test name, literal platform example,
or one record subtype when the rule applies more broadly. Do not make hidden
tests visible, prescribe the solution path, or turn inferred domain work into a
checklist.

Do not remove core requested behavior merely to obtain `None`. Narrowing must
preserve the user's intended task and align instruction, schemas, Oracle, and
verifier; a material redesign requires user direction. Shrinking unused surface
is an option, not a substitute for repairing a required invariant.

## Switch strategy rather than accumulate patches

At batch planning, inspect prior snapshot-bound attempts for this root cause.
Before clearance, use deterministic evidence to check the chosen closure
obligations. A strategy is not converging when the same invariant still fails
after attempted fixes, sibling paths repeatedly regress, or each repair demands
new exceptions and authorities without reducing the confirmed defect set.
Provider errors, truncated reviews, new unverified claims and stochastic verdict
changes alone do not establish non-convergence.

When a strategy fails those checks, stop adding symptom patches: switch to a
credible shared repair, narrowing or removal if it is within the authorized
batch. If it is not, report the decision needed instead of expanding scope.
There is no universal N-attempt or line-count cutoff; obey explicit user budgets
and the existing discovery/batch/single-clearance limit. A blocking clearance
does not authorize another repair cycle; recommend the next disposition and stop.
Use `rescope_required` when the same public obligation set would otherwise enter
another panel round. A rescope must change the core, support or non-goal
boundary; another witness batch under the same contract is continued
remediation, not rescoping.

For an authorized feature removal, preserve a recoverable snapshot outside the
upload, enumerate dependencies, and update instruction, schemas, environment,
Oracle, verifier, rubric and inventory/coverage receipts as applicable. Mark
removed obligations as removed rather than falsely covered; keep all witnesses
for retained promises. Never delete only the failing test while leaving its
requirement active, remove a genuine difficulty case merely for failing, or
weaken protection against reward bypass. Re-measure any changed task; no old
tier or clearance survives semantic reduction.

When the removed promise is a representation constraint, retain and verify its
semantic payload. For example, dropping a native text encoding may still require
the same keys and decoded values. Run the formerly rejected representation as a
valid-alternative case so removal is proved by acceptance rather than inferred
from deleted assertions.

Any authority edit can invalidate copied-evidence hashes, sufficiency manifests,
packet hashes, verifier matrices, wrong-path receipts and the revision ledger.
Update these dependencies before interpreting Oracle failures; a stale evidence
digest is bookkeeping fallout, not a semantic regression. Regenerate receipts
only after the task snapshot is final.

Retiring a task means mark it not-for-submission and preserve its artifacts and
reasons, not delete its directory/history or call it fixed. Replacement mining
is allowed only within an already authorized batch; otherwise request direction
before abandoning the user's required core or starting another task.

## Close the variant space

For each invariant, enumerate only dimensions supported by the contract and
implementation. Typical dimensions include:

- subtype or command mode;
- same-scope versus cross-scope identity;
- missing, duplicate, conflicting, superseded, or reversed state;
- before, equal, and after temporal boundaries;
- empty, singleton, and repeated collections;
- success, failure, and partial lifecycle states;
- interaction with one other independent mechanism.

Every listed variant must end in one of three dispositions:

- covered by the shared repair and an existing discriminating witness;
- covered by the repair and a new minimal witness or mutant;
- explicitly outside the contract with cited authority.

This is semantic closure, not a Cartesian-product demand. Do not add fixtures
that repeat the same branch without increasing discrimination.

## Prove the repair

Before clearance, require:

1. the original reproducer changes from wrong to correct;
2. any relevant sibling path is exercised independently, or its absence is justified;
3. each separate implementation site has a dedicated partial-fix mutant, unless
   the repair demonstrably centralizes the sites into one path;
4. a relevant interaction survives, or inapplicability is justified;
5. pre-existing unrelated behavior remains passing;
6. the contract, reference, verifier, and protection model remain aligned.

If a group cannot meet these obligations, revisit the option comparison rather
than automatically expanding or shrinking. Stop/retire when no justified option
remains. Report retained value, removed/narrowed obligations, necessary additions,
proof results, and any unresolved decision. Do not accumulate patches solely to
chase stochastic panel output.
