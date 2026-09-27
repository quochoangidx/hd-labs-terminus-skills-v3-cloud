# Contract review r1 — tbrain-warehouse-cycle-count-variance

Scope: instruction.md + environment/ only.

## PART 1 — Contract review

1. **BLOCKING — tolerance of an ungraded class (D–Z): rule 1.2 positively governs it.**
   Instruction: "Where the procedure gives no rule for a figure ... keeps working the figure out the way it does today". CC-2 2.3 defines tolerance only for graded items, so the ungraded tolerance looks silent and the kept code is `round(system*5/100)` (Python banker's rounding). But 1.2 says, with no qualifier, "A tolerance is a whole number of units, a fraction of a unit dropped. Nothing else is rounded." A careful reader applies that to *every* tolerance the report prints, including the kept 5% figure, which gives `floor(system*5/100)`.
   Counterexample: class D, system 70, count 74, recount null. Reading K (kept round) gives tol 4 → "ok". Reading F (1.2 floor) gives tol 3 → "recount". Also system 10 (0.5): round gives 0, floor gives 0 (same). System 30 (1.5): round gives 2, floor gives 1.
   Fix: have 2.3/1.2 say "the tolerance of a graded item is a whole number..." and say plainly that CC-2 gives no tolerance for other classes. Or drop the silent tolerance.

2. **BLOCKING — `booked` for "ok" and "recount" lines is neither clearly governed nor clearly silent.**
   3.3 says only "An adjusted line books its variance". README: `booked` is "the units posted to stock". The instruction complains that recount lines are "posted straight to stock", which implies booked=0 for them. Nothing positively says a non-adjusted line posts nought, though. The silence clause would keep `booked = off`, and then a recount line still "posts" its variance, contradicting the stated bug. The instruction also names "a reading that a silent figure is nought" as the trap. Here that reading is the natural domain reading.
   Counterexample: example CTN-7781 (B, -12, tol 24, ok). Reading 0 gives booked 0. Reading kept gives booked -12. A recount line, class A, system 5, count 3, null: booked 0 vs -2.
   Fix: add 3.3 sentence "A line that is not adjusted books nought units", or state explicitly that booked on non-adjusted lines is left to the package.

3. **SHOULD-FIX — status for ungraded lines depends on finding 1.** 2.4/3.1 apply to "a line", so ungraded lines are routed ok/recount/adjust using whatever tolerance the reader chose. Status is therefore doubly ambiguous. Once finding 1 is fixed, this resolves.

4. **SHOULD-FIX — the "kept value uniquely derivable" test needs Python's `round` semantics.** Even under reading K, the grader must use banker's rounding (round-half-even: 2.5 gives 2, 3.5 gives 4). This is derivable from the shipped code, so it is fine, but an agent that "tidies" it into `int(x+0.5)` diverges at every half. That would be a restraint trap, but it is only fair once finding 1 is closed.

5. **POLISH — the shrink sign is clear.** 3.4 plus "A surplus does not reduce shrink" is unambiguous. Shrink ≥ 0.

6. **POLISH — the fractional B/C tolerance is clear.** 1.2 floor. For B, `system*2//100`; for C, `system*5//100`. Integer arithmetic avoids float error at 100,000 (5000.0 is exact anyway).

7. **POLISH — `value` for non-adjusted lines.** 3.2 governs all lines (variance × cost), so recount/ok lines keep a nonzero value. Unambiguous.

Numeric ranges: 1.3 gives a floor and ceiling for every field. Lines 1–300, lengths 1–12. Fine. Duplicate SKUs and out-of-range values are declared open. Fine.

Exact conventions with authority: final count (2.1), variance sign (2.2), tolerance floor (1.2), status strings (3.1 + README), shrink (3.4), key order/types (README). All present. The two gaps are the ungraded tolerance line and booked for non-adjusted lines.

### Witnesses (hand-worked)
| # | line | variance | tol | status | value | booked |
|---|------|----------|-----|--------|-------|--------|
| W1 | A 240/238/239 @18450 | -1 | 0 | adjust | -18450 | -1 |
| W2 | B 1200/1188/null @320 | -12 | 24 | ok | -3840 | 0 or -12 (F2) |
| W3 | C 90/97/96 @75 | 6 | 4 (4.5 floor) | adjust | 450 | 6 |
| W4 | example shrink | – | – | – | – | 18450 (surplus W3 not netted; shipped gives 18450-450=18000) |
| W5 | B 50/48/null @1 | -2 | 1 | recount | -2 | 0 or -2 |
| W6 | C 20/21/null @1 | 1 | 1 (exact edge) | ok | 1 | 0 or 1 |
| W7 | C 0/1/0 @9 | 0 | 0 | ok | 0 | 0 |
| W8 | D 70/74/null @1 | 4 | 4 (round) or 3 (floor) | ok or recount (F1) | 4 | ? |
| W9 | D 50/53/53 @1 | 3 | 2 (round 2.5 half-even; floor 2) | adjust | 3 | 3 |
| W10 | A 100000/0/100000 @1000000 | 0 | 0 | ok | 0 | 0 |

## PART 2 — Solver-path screen

A) Pre-mortem: a solver fixes final_count, splits tolerance per class with floor, adds the recount status, and fixes the shrink sign. All of that is easy and visible. It then hits D–Z. Most solvers either apply 1.2 floor to the 5% fallback (fail under reading K) or treat ungraded as tolerance 0, or keep round (pass). For booked, most set 0 on non-adjusted lines because the bug narrative says recount lines must not post. If the reference keeps `booked=off`, most solvers fail. If the reference uses 0, the "silent → keep" clause is contradicted. Either way the outcome turns on the ambiguity, not on skill. Failures will look like contract disputes on review.

B) Scores:
- reference_unreachable: 4. Every figure is computable once the readings are fixed.
- authority_incomplete_for_grading: 2. Two blocking splits (F1, F2) hit many lines of random 300-line sheets with every class letter.
- hidden_state_not_closed_form: 4. The only hidden state is the kept round() and 5%, which are visible in the shipped code.
- restraint_traps: 2. There is one candidate: the kept round() for ungraded lines. It fails the 0/8 screen because 1.2 is a competing positive sentence and the expert instinct (floor) runs contrary. The booked trap likewise has strong contrary instinct plus narrative support.
- fuzz_blind_spot: 4. Every class letter, exact edges and fractional tolerances are enumerated, so the fuzz will hit both ambiguities heavily.

C) self_verification_resistance: 2. The example plus the procedure let a solver verify all graded behaviour, and nothing verifies the silent choices. Prediction: 0–2/8 pass, with failures driven by F1/F2 rather than difficulty. Confidence: medium-high. decisive_reason: the ungraded tolerance and non-adjusted booked are each readable two ways, and 1.2 and the instruction's own bug narrative push toward the reading that the "keep today's behaviour" clause seems to forbid.

### Departures of shipped package from CC-2
1. `final_count` ignores the recount (2.1).
2. There is a single 5% tolerance for all classes, not A=0 / B=2% / C=5% (2.3).
3. The tolerance uses `round()` (half-even) instead of dropping the fraction (1.2).
4. There is no "recount" status. Every outside-tolerance line becomes "adjust" (3.1).
5. `booked = off` on every line, including ok/recount lines. This depends on F2: 3.3 only covers adjusted lines, and recount lines must not post, per the instruction.
6. Shrink = −Σ value over adjusted lines, so surpluses net against it and it can go below 0 (3.4).
(`value` = variance×cost already matches 3.2 once variance uses the final count.)
