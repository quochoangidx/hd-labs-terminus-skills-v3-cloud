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
scripted Sound Verifier sweep (§4, blueprint C1–C18) and the narrow panel are
what find the ones not yet seen.

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
- **Separate semantic content from representation.** For every schema field or
  attribute, decide whether consumers require the native storage type/encoding
  or only the decoded value. Do the same for symlinks, record ordering, package
  layout, compression and diagnostic output. If the representation does not
  affect interoperability, do not promise it and do not grade it.
- **Run `contract_review` now**, blind to tests and solution, on the note plus
  instruction plus shipped code. Adjudicate and repair before the verifier
  exists. A contract repair is cheap here and expensive after the receipts.

## 2. Correct reference: does the reference satisfy the documented task?

- Model before Oracle, never importing the package (`contract-closure.md` §5).
  Put it in `solution/model.py` and let its `__main__` seal expectations (and
  generated inputs) into `tests/expected/` with a SHA manifest. A model or
  generator that runs inside `tests/` is the "no end-to-end solver in tests"
  human-review return that hit crop-water and royalty after clean platform runs.
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
- A shipped copy used for differentials is owned by **its own uid, mode 0700**, and
  run as that uid. *Missed:* a world-readable shipped copy let a candidate delegate
  to it (moving-average, escrow: Major). "Readable, not writable" is not enough.
- **Run a verifier-owned copy of any fixed driver, and check the submitted one.** If
  the instruction fixes a driver the tests go through, never execute the agent's
  `/app/tools/<pkg>_run.py`. *Missed:* grading through it let a driver-side shim
  score reward 1 with the package unfixed, in three tasks (`review_task.py` blocks
  it as `verifier-trusts-candidate-driver`). Three refinements from later returns:
  - add a test that the submitted driver is byte-identical to
    `tests/shipped/tools/`, or a broken submitted driver passes (midi v1, Major);
    say why in the instruction ("we file with our own copy");
  - run that byte check **after** candidate code too (a last test, or in `test.sh`
    after pytest): a submission rewrote the driver on import and still scored 1
    (retail-inventory human review);
  - run the documented command at the documented path and cwd. A copy under
    `/opt/driver` beside `/opt/driver/src -> /app/src` changes `argv[0]`, and a
    package that misbehaved only when `argv[0]` was the `/app` path scored reward 1
    (groundwater v2). For interpreted drivers, `os.replace` the shipped copy onto
    `/app/tools/<pkg>_run.py` after recording the submitted bytes, then run exactly
    the documented command from the verifier's copy of `/app`.
- **Prove the boundary.** A test runs `ls`/`cat` as the sandbox uid on `/tests`,
  the expectations, the shipped copy and `/logs/verifier` and asserts each fails;
  check it once with `/tests` world-readable to see it go red. Make `/tests` 0700
  in `tests/Dockerfile`, not only in `test.sh`.
- **No case label reaches the candidate.** Stage each job in a prefix-less
  `mkdtemp()` under a content-digest name; vary input file names per job. A
  `mkdtemp(prefix=name)` or a run file named after the case let a package key on it
  (genomic, retail-inventory).
- **Never grade a byte copy of a visible sample** (moving-average v0, Protected
  Ground Truth Major; transformer-metering v1).
- Seed generated inputs from a constant in the sealing code, never from a hash of
  candidate files (an inert nonce file steered the graded cases in overtime v4).
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
- **Cross the invocation boundary.** For each state machine, run at least one
  case where the first requested event must change the initialized state. A
  later excursion does not expose an implementation that emits the first
  result before applying its transition.
- **Partition signed derived values.** If an equation permits negative, zero and
  positive results, ensure existing fixtures collectively cross those signs.
  A suite of many positive values still leaves one missing branch.
- **Do not use tolerance as a directional assertion.** When the contract says
  nonnegative, monotone, bounded or strictly ordered, assert that property
  independently before any `allclose`/tolerance comparison.
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
- **Run the Sound Verifier class ladder before the first upload**
  ([accepted-task blueprint](accepted-task-blueprint.md) §5, classes C1–C18): every
  visible sentence backed or deleted, ceilings and floors, every bound reached in
  every position and sum, zeros and empties, counts past 1,024 and 65,536,
  cardinalities at their bounds, parameters past 512/2048/4096, field lengths past
  8/64/1024, accumulators past 2^31, exact halves on both signs, the whole
  categorical syntax, two entries per separated accumulator, envelope
  cross-products. Each as an Oracle mutant that must fail its own test. The
  platform found these one class per round in every accepted task (genomic took
  six rounds); a PASS on one round does not clear the next class.
- **Assert the limits on every graded job.** An executable form of the
  instruction's limits sentence runs over every generated **and named** fixture and
  checks which trap inputs each carries. Moving-average's fifth return was one
  hand-built fixture still holding a dropped input class.
- **Keep trap inputs in their own named tests.** Sweeps, whole-run tests and shared
  fixtures stay trap-free, so one over-repair costs one test (rebill: a trap inside
  seven tests turned all seven 0/8 and returned the task as unsolvable).
- **Run one or two alternative correct implementations through the suite** (a
  different loop shape, an algebraically equal but still note-faithful form, a
  different buffer). Include harmless diagnostics, resolving package/artifact
  links, or alternate native text encodings when the contract leaves them free.
  Keep candidate diagnostics off verifier-owned JSON or other machine channels.
  A rejection means the verifier demands the Oracle's shape.

## 5. Deterministic execution: does the same submission grade the same every time?

- Literal or deterministically generated fixtures. No RNG, clock, network or
  library signal generators whose output could move.
- The model and the candidate run on the same interpreter and libm, in a
  digest-pinned image.
- `python -I` ignores `PYTHONHASHSEED`, so sort anything built from a set before
  it reaches output, a seal or a digest; check the sealed expectations under two
  hash seeds.
- Collection order is pinned (`-p no:randomly`), every job has a timeout, and each
  job runs in its own process.
- **Run `preflight.sh --determinism` as soon as the first named tests pass on
  the Oracle** (order step 3), not only at closure. It repeats the verifier, so it
  needs `tests/` to exist.

---

## Order that keeps rework cheap

1. Authority, instruction, domains, state table, global-claim check, then
   `contract_review`. Repair the contract.
2. Model, Oracle, then the model-versus-Oracle fuzz, then the skeleton probe
   (a 2/2 stops here, before any verifier work).
3. Harness shape (§3). Then named tests, with each witness in a revealing state,
   and a first `preflight.sh --determinism` once they pass on the Oracle.
4. Local wrong paths, then alternative implementations.
5. Deterministic closure: preflight strict and determinism, Docker receipts,
   `panel_precheck.py --full`.
6. The Sound Verifier sweep (C1–C18 mutants), `final_review`, then the
   difficulty rescore of the skeleton diffs against the finished verifier.
