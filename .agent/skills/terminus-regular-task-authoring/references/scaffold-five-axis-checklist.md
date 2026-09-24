# Scaffold-time five-axis checklist

The platform's quality panel asks five questions. The gates in
`execution-profiles.md` step 5 answer them after the build, and a reviewer answers
them after the gates. Both catch defects, but late: every contract finding after
the gates forces the whole wrong-path matrix to rerun. Answer each question with an
artifact while you scaffold, before the first test is written.

Every item below comes from a defect that reached review in
`tbrain-lookahead-compressor-ballistics` or `tbrain-quantized-depthwise-convolution`,
or from the two platform panel returns of 2026-09-24
(`tbrain-health-claim-cost-sharing`, `tbrain-intermittent-infusion-regimen`,
37 findings each, about 17 and 25 root causes once duplicates are merged).
None of them was caught by a gate.

This list is a floor, not the review. It names defects already seen. The
adversarial verifier pass (§4, last item) is what finds the ones not yet seen.

Keep the artifacts under `workspace/reports/<slug>/`, never in the task.

**Profile scope.** The order below, with `contract_review` before any verifier,
is the `builder_certified` order. `campaign_ready` still runs `contract_review`
after its full mechanical gates (`task-batch/references/campaign-ready.md`); under
that profile, do every item here except the early `contract_review`, and run the
review where that profile places it.

---

## 1. Coherent contract: can a candidate determine every graded rule?

Write the authority and the instruction first. Then:

- **Declare the input domain** of every field the job or call carries: its type,
  and whether it may be absent, null, nought, negative or unbounded
  (`contract-closure.md` §1). The panel checks a missed input against this
  documented domain.
- **State each formula's domain.** Name the arguments the rule covers ("for a knee
  of positive width", "with the rate above nought"). A rule without a domain is
  either universal, so it silently overrides the silence clause, or ambiguous.
  *Missed:* the lookahead formula said nothing about the rate, and a reviewer had
  to find it.
- **Write the rule × region table** (`rule-regions.md`) for every rule left
  universal. Rows are rules; columns are the regions the declared domain admits
  (nought, negative, very large, each side of each threshold, and each order in
  which two rules can meet). Every cell names its witness. A cell you will not
  witness means the rule gets a narrower domain. *Missed, 24 times in two returns:*
  a family deductible and out-of-pocket maximums of nought or less; a primary
  payment above the allowed amount; half of 30000000000000001 cents; a negative
  elimination rate; a zero or negative dosing interval; a height below the
  formula's reference; a creatinine cap applied before or after the female factor.
- **Budget the promises.** Rules × regions, plus every promised helper and every
  named coverage family, is the surface the panel samples. If the table above
  cannot be filled, cut rules or narrow domains now
  ([bounded task design](bounded-task-design.md)); do not plan to test your way
  out.
- **Write the state table** (`state-table.md`): one row per operation (each setter,
  reset, process, a refused call, a repeated call with the same value) and one
  column per piece of observable state (every stored setting, carried values,
  buffers, the last report). Every cell says *changes*, *keeps* or *not
  described*. A blank cell is a contract gap. Every *not described* cell falls
  under the silence clause and needs a decision (see §4).
  *Missed:* "does setting a lookahead of the same length store the new value?"
  was a blank cell. It was observable through a later rate change.
- **Check every global claim against the silence clause.** For each "X follows
  from all this" or "whatever the other settings" sentence, try it on the silent
  inputs. *Missed:* "a ratio of one returns the input whatever its other
  settings" was false for an attack time of nought, which raises.
- **List every exact convention** (format, operation order, rounding, sign of
  zero, precedence, defaults) with its anchor sentence. That list becomes
  `exact_output_requirements`.
- **Check every example against every rule.** An example in the note that breaks
  the note's own type or format rule is a contract finding. *Missed:* a type rule
  said every other field is numeric, and the required example carried a string
  regimen name.
- **Promise helpers only when they are the deliverable** (`contract-closure.md`
  §1, entry point). Otherwise the note describes what the entry point returns and
  nothing about internal functions.
- **Run `contract_review` now**, blind to tests and solution, on the note plus
  instruction plus shipped code. Adjudicate and repair before the verifier
  exists. A contract repair is cheap here and expensive after the receipts.

## 2. Correct reference: does the reference satisfy the documented task?

- Model before Oracle, never importing the package (`contract-closure.md` §5).
- **Fuzz the model against the Oracle as soon as both exist**, and before any test:
  a few hundred random inputs and sessions compared exactly. A disagreement is a
  bug in one of the two readings, and it is far cheaper to find now.
- **Decide how the model treats each silent case**: either it refuses to answer
  (and the witness is a shipped differential), or it mirrors the shipped
  expression and says so in a comment. Never let it answer with its own natural
  reading. *Missed:* the depthwise model saturated a reversed clamp with
  max-of-min while the package checks the lower bound first. The promised case
  could never be witnessed, and the platform failed the task on it.
- **Probe the numerics of both the model and the Oracle.** Fuzzing the two
  against each other misses what they share. Take the model to exact arithmetic
  (`Fraction`, integers) and try:
  - values one ulp below a rounding half;
  - magnitudes above 2^53 and near the float limits;
  - every numeric format the contract allows, decoded through `json.loads` and
    checked against the value the job writes.

  *Missed:* `floor(x + 0.5)` rounds the float just below one half up; an
  intermediate quotient overflowed for an exact multiple; a rate the contract
  allowed decoded to `0.0`.
- Head `solve.sh` with the contract-topic to change table (`contract-closure.md` §9).

## 3. Protected ground truth: can candidate code obtain or control the answer?

Fix the harness shape at scaffold time. Do not retrofit it.

- Separate verifier. Expected values exist only in the verifier image, or only in
  pytest's memory.
- Every candidate process drops privilege
  (`setpriv --no-new-privs --reuid --regid --clear-groups`) in its own session, with
  a fixed small environment.
- A Python candidate runs as `python3 -I -S`. `-I` alone still exposes the
  verifier's site-packages, so a "standard library only" rule goes unenforced
  (`docs/testing-and-validation/quality-panel-examples.md` C-11). *Missed:* in
  both returns of 2026-09-24.
- Seal `/tests` and `/logs/verifier` (0700) before the first candidate process.
  Root writes the reward only after pytest has exited.
- **Make `/app` readable to the demoted user** (`chmod -R a+rX /app` in `test.sh`).
  *Missed:* a file the agent leaves 0600 would fail every job for a reason that
  has nothing to do with the code.
- A shipped copy used for differentials is readable and not writable.
- **Run a verifier-owned copy of any fixed driver, pointed at `/app/src`.** If the
  instruction fixes a driver the tests go through, stage `/opt/driver/tools/<pkg>_run.py`
  from `tests/shipped/tools/` with `/opt/driver/src -> /app/src`. *Missed:* grading
  through `/app/tools/<pkg>_run.py` let a driver-side shim score reward 1 with the
  package unfixed, in three tasks. `review_task.py` blocks it as
  `verifier-trusts-candidate-driver`.
- Plan the harness-bypass wrong paths now: a wrong solution that tries to write
  the reward and read the model, and one that fixes the driver instead of the package.
- Compiled languages: follow [compiled verifier hardening](compiled-verifier-hardening.md).

## 4. Sound verifier: does grading reject wrong solutions and accept valid ones?

- One named test per rule. CTRF drops parametrize IDs, so a parametrised sweep
  reports as one row.
- **A wrong path for every obligation**, covering both the departure reverted and
  each *natural over-repair* (`contract-closure.md` §15). Score them locally
  first, and write Docker receipts only once every one is killed by its own
  witness.
- **Run every witness in a state where its violation can show.** For each witness
  ask: *if this rule were broken, would the state at this point make the output
  differ?* *Missed, five times:*
  - a rate-change test ran with no lookahead, so refilling the line was invisible;
  - refusal tests ran before any state existed, so a refusal that reset the
    state still passed;
  - a silent-setting session drove levels far above the knee, so a clamped knee
    gave the same output.
  The fix each time was a richer state, not more tests.
- Every named silent case has a witness (`closure.silence.named_cases`). Every
  family in the coverage envelope is actually exercised: if the instruction
  promises three-channel blocks, run a three-channel session.
- **Put one fixture exactly on the accepting edge of every strict boundary** ("below",
  "above nought", "from 0 up to 1"). *Missed:* `charged <= minimum` and a ratio check
  that refused `0.0` both scored reward 1, because every case sat off the edge.
- For each *not described* cell of the state table, decide now: witness it with a
  shipped differential, or narrow the prose so it is not promised
  (`contract-closure.md` §11).
- **Vary every job shape the declared domain admits**, and nothing it does not
  (`docs/creating-tasks/writing-tests.md`, perturbation re-runs):
  - an optional field absent, and null where null is allowed;
  - an object that gives only some of its fields;
  - an empty list, and a list longer than any plausible hard-coded bound;
  - list items and members in a different order, with ids that are not the
    usual ones (the "first listed" member is not always `S`);
  - identifiers of nought and below where the contract allows them;
  - a boolean flag both true and false;
  - no field held at one value in every fixture (a `year_start` that is always
    the same is never tested).

  *Missed, 19 times in two returns.*
- **Compare type-strictly and to the promised shape.** Compare native types
  as well as values (`3`, `3.0` and `True` are equal under `==`; C-12). Reject
  extra fields and check key order only where the contract fixes them (C-13). A
  named input class is checked on its full result, not one field. Every promised
  error output has a witness.
- **Run one or two alternative correct implementations through the suite** (a
  different loop shape, an algebraically equal but still note-faithful form, a
  different buffer). A rejection means the verifier demands the Oracle's shape.
- **Adversarial verifier pass before packaging** (`task-batch`
  `execution-profiles.md`, `builder_certified` step 5b). A fresh reviewer who has
  not seen the builder's wrong paths reads only the contract and `tests/`, writes
  plausible wrong submissions that stay contract-valid elsewhere, and runs them
  through the verifier. Each one that scores reward 1 is a finding. This is how the
  panel works ("confirmed by running the grader"), and it is what the builder's own
  wrong-path matrix cannot do: v1 of the claims task killed all 51 of its own wrong
  paths while 15 of the panel's passed.

## 5. Deterministic execution: does the same submission grade the same every time?

- Literal or deterministically generated fixtures. No RNG, clock, network or
  library signal generators whose output could move.
- The model and the candidate run on the same interpreter and libm, in a
  digest-pinned image.
- Collection order is pinned (`-p no:randomly`), every job has a timeout, and each
  job runs in its own process.
- **Run `preflight.sh --determinism` as soon as the first named tests pass on
  the Oracle** (order step 3), not only at closure. It repeats the verifier, so it
  needs `tests/` to exist.

---

## Order that keeps rework cheap

1. Authority, instruction, domains, state table, global-claim check, then
   `contract_review`. Repair the contract.
2. Model, Oracle, then the model-versus-Oracle fuzz.
3. Harness shape (§3). Then named tests, with each witness in a revealing state,
   and a first `preflight.sh --determinism` once they pass on the Oracle.
4. Local wrong paths, then alternative implementations.
5. Deterministic closure: preflight strict and determinism, Docker receipts,
   `panel_precheck.py --full`.
6. `final_review`, the adversarial verifier pass, then the blind probe.
