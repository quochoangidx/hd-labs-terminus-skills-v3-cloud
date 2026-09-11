# Root-cause remediation

Use this only after the four-axis discovery pass has finished and the user asked
to update the task, or to interpret the root-invariant map when consolidating
a review-only report (without authorization to edit). The goal is to close each violated semantic invariant, not to
make the reported example pass.

## Build the root-invariant map

Create one group for findings that share the same authority and failure
mechanism. Do not group findings merely because they touch the same file.

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
    "shrink": "surface that can be removed or narrowed",
    "preserve": "shared implementation boundary that can be repaired"
  },
  "chosen_repair_boundary": "one authority point to change",
  "proof_obligations": ["focused reproduction", "property", "mutant"],
  "regression_risks": {
    "coherent_contract": [],
    "correct_reference_solution": [],
    "protected_ground_truth": [],
    "sound_verifier": []
  }
}
```

Derive missing map fields from the frozen task with concrete citations. Do not
ask reviewers for iterative follow-ups and do not start editing an incomplete
group.

## Choose the repair boundary

For size-driven simplification, apply
[panel input hygiene](../../terminus-regular-task-authoring/references/panel-input-hygiene.md).
The 800-line warning alone never creates a repair group; retain necessary
evidence and witnesses even when a file stays large.

Prefer, in order:

1. remove a promise, mode, field, or case family that is unnecessary and whose
   removal keeps a coherent useful task;
2. narrow an over-broad input or output contract at its natural schema boundary;
3. centralize a validator, selector, state transition, or authority lookup used
   by every affected path;
4. repair multiple sites only when the domain genuinely has separate mechanisms.

Do not add a condition keyed to a fixture, test name, literal platform example,
or one record subtype when the rule applies more broadly. Do not make hidden
tests visible, prescribe the solution path, or turn inferred domain work into a
checklist.

Do not remove core requested behavior merely to obtain `None`. Narrowing must
preserve the user's intended task and align instruction, schemas, Oracle, and
verifier; a material redesign requires user direction. Shrinking unused surface
is an option, not a substitute for repairing a required invariant.

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

If a group cannot meet these obligations without substantially enlarging the
task, prefer shrinking the contract or report the design as needing redesign.
Do not accumulate patches solely to chase stochastic panel output.
