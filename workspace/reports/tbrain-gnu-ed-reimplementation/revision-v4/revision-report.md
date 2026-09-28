# tbrain-gnu-ed-reimplementation — revision v4

**Returned snapshot** `59a910038fda9755816301c8a405245619650c29ba511233a4f9dce528da7507`
(byte-identical to the rev3 archive this project shipped)
**Return** pre-difficulty gate again: 50 blocking findings, down from 52.

## Two findings were right, and both were mine

| What | Where it came from |
|---|---|
| A graded `ed -v` invocation while the instruction lists six options "and no others" | a case added in v3 to pin an errata sentence; the sentence said the program accepts `-v`, which is true, but grading it contradicted the contract |
| A binary-file flag that never cleared, so after any NUL-holding file a later empty read stripped the final newline from a text buffer | the flag added in v2 to implement the manual's Limitations rule |

Probing around the second one also exposed a path the reference did not implement at all:
reading a file into a buffer whose last line arrived without a newline makes ed insert one and
say *Newline inserted*, counting only the bytes read. The reference now does that, and keeps a
binary buffer's missing final newline across a later read that supplies one.

## What the evidence showed

| Platform claim | Raw evidence | Root-cause class | Decision |
|---|---|---|---|
| 8 contract and verifier findings about `-v` | the corpus graded an option the instruction excludes | contract defect I introduced in v3 | backed: case removed, errata clarified |
| 2 reference findings about binary state | after `E text`, ed writes `B\n` and the reference wrote `B` | reference defect I introduced in v2 | backed: flag set per load, four cases pin the states |
| 7 reference findings | GNU ed matches the reference on every script | not a defect | disputed, each script added as a case |
| 33 coverage findings | the returned corpus had no case for any of them | missing behavioural coverage | backed: 35 cases added |

## A note on the errata sentence about empty matches

Three findings read "a substitution with the g suffix is refused when its expression can match
the empty string" as a property of the expression. ed refuses when a zero-length match repeats
at the same position, so `s/a*/X/g` succeeds on `a` and fails on `b`. The sentence now says
that, and both scripts are graded.

## Results

| Run | Result |
|---|---|
| Differential over the whole corpus | 1816 cases, 0 differ from GNU ed 1.19 |
| Oracle / NOP / noexec, determinism | reward 1 / 0 / 1, pass |
| Wrong paths | 13 of 13 rejected on their own witness, including a new one for the binary state |

## Final state

| Item | Value |
|---|---|
| Repaired snapshot | `9d7ea2b31325...` |
| Upload archive | `tbrain-gnu-ed-reimplementation-rev4.zip`, sha256 `7381ddeb26fa6bbd5836...`, 46 entries |
| Returned archive | untouched, sha256 `8908026e1f518786d439...` |
| Corpus | 1770 → 1816 cases, 25 platform-visible tests |
| Panel precheck, ledger, maps, zip review | pass, 50 answered, 21 errata + 42 findings mapped, ready |

The seven disputed findings need `contest-note.md` posted in `#terminus-3-submissions`.
