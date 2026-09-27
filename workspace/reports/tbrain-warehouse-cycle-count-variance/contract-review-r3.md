# Contract review r3 — tbrain-warehouse-cycle-count-variance

Scope: contract-packet-r3 only. The r3 changes: rule 1.2 is now "Every figure is worked out from unrounded figures." The shipped `booked` is now `count - system`, i.e. the first count. The instruction adds the symptom "adjusted lines post the first count's difference to stock rather than the recount's".

## Status of r2 findings
- **N1: CLOSED.** No sentence now speaks about rounding in general, and 2.3 floors only the graded tolerances. The kept `round(system*5/100)` for classes other than A, B and C has no competing sentence. "Worked out from unrounded figures" is satisfied, because `system` is exact.
  Old counterexample: class D, system 70, count 74, no recount now has one reading, tolerance 4, "ok".
- **N2: CHANGED SHAPE, still OPEN as a trap-quality issue (see N3).** On a "recount" line (no recount taken) the kept `count - system` equals the variance, so the kept figure is the same as before (B 50/48/null → -2). The nought instinct from the README's "the units posted to stock" is unchanged: nothing positively says nought, but it still pulls.

## New findings
- **N3 SHOULD-FIX (trap quality) — `booked` on an "ok" line that has a recount.** This is the only place the kept figure differs from the variance. The kept value is `count - system`, the first count. The new symptom criticises exactly this behaviour ("post the first count's difference ... rather than the recount's") but scopes it to adjusted lines. A literal reader keeps the first-count difference on ok lines that were recounted. A natural reader makes one fix, `booked = variance`, for every line, reasoning that the same defect is a defect everywhere. A third reader books 0, because ok lines are not posted.
  Counterexample: class B, system 1200, count 1188, recount 1190. Variance -10, tolerance 24, "ok". Kept booked = -12; the one-fix reading gives -10; the nought reading gives 0.
  The contract technically resolves it: rule 3.3 governs adjusted lines only, and the silence clause keeps "the way it does today" for the rest. But the kept value is an acknowledged defect (the symptom names it) and it sits beside the correct figure. So the trap has a definitional chain, yet runs into strong contrary expert instinct plus a competing reading of the symptom as an example of a general bug. I expect it to fail the 0/8 screen. Either make booked on non-adjusted lines governed (for example, "every line books nought unless adjusted"), or accept that failures here will read as contract disputes.
- **N4 POLISH — "from the figures the procedure does define".** The kept booked uses the raw `count`. The procedure uses "count" in 2.1 without a numbered definition, though 1.3 bounds it, so a pedant could argue the raw count is not a defined figure and the kept step must use the final count. That is weak, but it reinforces the one-fix reading in N3.
- No other sentence reads two ways.

## Figures left to today's code
| figure | kept formula | derivable? witness | could any sentence govern it? |
|---|---|---|---|
| tolerance, class not A/B/C | `round(system*5/100)`, half-to-even | Yes. D, system 50 → 2; system 70 → 4 | Only the weak "tolerance of a graded item" reading, under which ungraded is 0. No competing rule remains. |
| booked, "recount" line | `count - system` (= variance here) | Yes. B 50/48/null → -2 | README "posted to stock" gives a nought reading (N2) |
| booked, "ok" line without a recount | `count - system` (= variance) | Yes. B 1200/1188/null → -12 | Nought reading (N2) |
| booked, "ok" line with a recount | `count - system` (≠ variance) | Yes. B 1200/1188/1190 → -12 | The symptom sentence read broadly gives the variance, -10; the nought reading gives 0 (N3, N4) |

## Witnesses
| line | variance | tolerance | status | value | booked |
|---|---|---|---|---|---|
| A 240/238/239 @18450 | -1 | 0 | adjust | -18450 | -1 |
| B 1200/1188/null @320 | -12 | 24 | ok | -3840 | -12 |
| C 90/97/96 @75 | 6 | 4 | adjust | 450 | 6 (the shipped code gives 7) |
| example shrink | | | | 18450 | |
| B 1200/1188/1190 @1 | -10 | 24 | ok | -10 | -12 (kept) |
| C 20/30/21 @1 | 1 | 1 | ok | 1 | 10 (kept) |
| B 50/48/null | -2 | 1 | recount | -2 | -2 |
| D 70/74/null | 4 | 4 | ok | 4 | 4 |
| D 50/40/53 | 3 | 2 | adjust | 3 | 3 |
| A 100000/0/100000 | 0 | 0 | ok | 0 | -100000 (kept) |

## PART 2 — Solver-path screen
A) Pre-mortem: the graded fixes are easy. The decisive site is the booked step. Most solvers read the new symptom and replace `line["count"] - line["system"]` with `off`, which fixes adjusted lines and also silently changes the ok lines that have a recount. The fuzz explicitly includes "recounts that bring a line back inside its tolerance", so almost every sheet has such a line, and those solvers fail. A minority set booked to 0 on non-adjusted lines and fail more widely. Only a solver who writes `off if status == "adjust" else count - system` passes. The ungraded tolerance is now a clean keep and should rarely fail. The A 100000/0/100000 row (booked -100000 on an "ok" line) looks absurd to an expert, which strengthens the urge to "fix" it.

B) Scores (1 to 5, 5 = strongly resists)
- reference_unreachable: 5
- authority_incomplete_for_grading: 3. The rule is technically closed, but the symptom sentence invites the broad reading (N3, N4).
- hidden_state_not_closed_form: 4
- restraint_traps: 2. There are two sites. The ungraded round() passes the screen. The booked-on-recounted-ok-line site fails it: the kept value is the named defect, it has strong contrary instinct, and the symptom competes with it.
- fuzz_blind_spot: 5. Recounted ok lines are guaranteed.

C) self_verification_resistance: 3. The example has no recounted ok line, so a solver cannot self-verify the booked choice. Prediction: 0 to 2 of 8 pass, nearly all failing on booked for recounted ok lines. Confidence: medium-high. Decisive reason: the only thing separating pass from fail is whether the solver keeps a figure the instruction itself describes as the bug, which is an ambiguity-driven failure rather than difficulty.

## Departures of shipped package from CC-2 (r3)
1. The final count ignores the recount (2.1). This also makes variance, value and status wrong.
2. There is one 5% tolerance for classes A, B and C; it should be 0, 2% and 5% (2.3).
3. The graded tolerance uses round() instead of dropping the fraction (2.3).
4. There is no "recount" status (3.1).
5. An adjusted line books `count - system` rather than its variance (3.3).
6. Shrink nets surpluses and can go below 0 (3.4).
Kept (silent): the ungraded tolerance `round(system*5/100)`, and booked `count - system` on "ok" and "recount" lines.
