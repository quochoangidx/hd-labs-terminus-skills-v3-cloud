# Scaffold-time five-axis checklist

The platform's quality panel asks five questions. The gates in
`execution-profiles.md` step 5 answer them after the build, and a reviewer answers
them after the gates. Both catch defects, but late: every contract finding after
the gates forces the whole wrong-path matrix to rerun. Answer each question with an
artifact while you scaffold, before the first test is written.

Every item below comes from a defect that reached review in
`tbrain-lookahead-compressor-ballistics` or `tbrain-quantized-depthwise-convolution`.
None of them was caught by a gate.

Keep the artifacts under `workspace/reports/<slug>/`, never in the task.

---

## 1. Coherent contract: can a candidate determine every graded rule?

Write the authority and the instruction first. Then:

- **State each formula's domain.** Name the arguments the rule covers ("for a knee
  of positive width", "with the rate above nought"). A rule without a domain is
  either universal, so it silently overrides the silence clause, or ambiguous.
  *Missed:* the lookahead formula said nothing about the rate, and a reviewer had
  to find it.
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
- Head `solve.sh` with the contract-topic to change table (`contract-closure.md` §9).

## 3. Protected ground truth: can candidate code obtain or control the answer?

Fix the harness shape at scaffold time. Do not retrofit it.

- Separate verifier. Expected values exist only in the verifier image, or only in
  pytest's memory.
- Every candidate process drops privilege
  (`setpriv --no-new-privs --reuid --regid --clear-groups`) in its own session, with
  a fixed small environment.
- Seal `/tests` and `/logs/verifier` (0700) before the first candidate process.
  Root writes the reward only after pytest has exited.
- **Make `/app` readable to the demoted user** (`chmod -R a+rX /app` in `test.sh`).
  *Missed:* a file the agent leaves 0600 would fail every job for a reason that
  has nothing to do with the code.
- A shipped copy used for differentials is readable and not writable.
- Plan the harness-bypass wrong path now: a wrong solution that tries to write
  the reward and read the model.
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
- For each *not described* cell of the state table, decide now: witness it with a
  shipped differential, or narrow the prose so it is not promised
  (`contract-closure.md` §11).
- **Run one or two alternative correct implementations through the suite** (a
  different loop shape, an algebraically equal but still note-faithful form, a
  different buffer). A rejection means the verifier demands the Oracle's shape.

## 5. Deterministic execution: does the same submission grade the same every time?

- Literal or deterministically generated fixtures. No RNG, clock, network or
  library signal generators whose output could move.
- The model and the candidate run on the same interpreter and libm, in a
  digest-pinned image.
- Collection order is pinned (`-p no:randomly`), every job has a timeout, and each
  job runs in its own process.
- **Run `preflight.sh --determinism` as soon as the Oracle exists**, not only at
  closure.

---

## Order that keeps rework cheap

1. Authority, instruction, domains, state table, global-claim check, then
   `contract_review`. Repair the contract.
2. Model, Oracle, then the model-versus-Oracle fuzz.
3. Harness shape (§3). Then named tests, with each witness in a revealing state.
4. Local wrong paths, then alternative implementations.
5. Deterministic closure: preflight strict and determinism, Docker receipts,
   `panel_precheck.py --full`.
6. `final_review`, then the blind probe.
