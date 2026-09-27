# Contract review r2 — tbrain-warehouse-cycle-count-variance

Scope: contract-packet-r2 only. The r2 changes are to rule 1.2, rule 2.3, and one symptom in the instruction ("marked for adjustment" replaces "posted straight to stock").

## Status of r1 findings
- **F1 (ungraded tolerance vs 1.2 floor): CLOSED, with a residue (see N1).** Dropping the fraction now lives in 2.3 and is scoped to graded items ("each a whole number of units with any fraction of a unit dropped"). No sentence floors the tolerance for classes D to Z any more, so the kept `round(system*5/100)` stands. Old counterexample (class D, system 70, count 74, no recount): there is now one reading, tolerance 4 and status "ok".
- **F2 (booked on non-adjusted lines): CLOSED as a contract matter, but it is a weak trap (see N2).** The symptom that implied recount lines book nought is gone. 3.3 covers adjusted lines only, so booked on "ok" and "recount" lines is silent and keeps `booked = variance`. Example line CTN-7781 books -12.
- **F3 (ungraded status): CLOSED.** 2.4 and 3.1 route every line using the kept tolerance.
- **F4 (half-to-even rounding): now the live restraint site.** It is derivable from the code; see the kept-figure table.
- **F5–F7: unchanged, clear.**

## New findings
- **N1 SHOULD-FIX — "Only the rules that say so round a figure" (1.2) can be read as governing the kept ungraded tolerance.** No rule says to round the class D to Z tolerance, so one reading is that the kept `round()` must go. That reading gives 3.5 for system 70 (unrepresentable, since README requires an integer) or pushes the solver to floor or int() it (3). The other reading is that the silence clause keeps the whole step, round included, which gives 4. The instruction's "keeps working the figure out the way it does today" favours the kept reading, and the README's integer type makes the unrounded reading impossible. Most careful readers will still keep round(). I would still add to 1.2 "...; figures this procedure does not define are outside this rule", or say so in the instruction.
  Counterexample: class D, system 70, count 74, no recount. Kept: tolerance 4, "ok". Floor reading: tolerance 3, "recount".
- **N2 SHOULD-FIX (trap quality) — booked=variance on "ok" and "recount" lines runs against strong expert instinct.** README defines booked as "the units posted to stock". A line sent back for a recount posting -2 units to stock contradicts warehouse practice, and a solver can reason by contrapositive: 3.3 ties posting to adjusted lines, so other lines post nought. No sentence positively says nought, so the contract is technically closed, but under the 0/8 screen this is a trap with strong contrary instinct. The fix is either a sentence ("a line that is not adjusted keeps whatever booked figure the package gives today"), or to make booked governed, with non-adjusted lines booking nought.
  Counterexample: class B, system 50, count 48, no recount → "recount". Kept booked is -2; the instinctive reading is 0.
- No other sentence reads two ways. The added "each" in 2.3 scopes cleanly to all three graded tolerances, including class A's 0.

## Figures left to today's code
| figure | kept formula | uniquely derivable? witness | any sentence that could govern it? |
|---|---|---|---|
| tolerance, class not A/B/C | `round(system*5/100)`, half-to-even | Yes. Class D, system 50 → 2 (2.5 rounds to 2); system 70 → 4; system 30 → 2 (1.5 rounds to 2); system 100000 → 5000. system*5/100 at x.5 is exact in floating point, so there is no drift. | 1.2 "only the rules that say so round" (N1); a nought reading via "tolerance of a graded item" (someone treating ungraded as tolerance 0 would give "recount" for class D, system 70, count 71; kept gives "ok"). Weak. |
| booked, "ok" line | variance | Yes. B 1200/1188/null → -12 | README "units posted to stock" plus 3.3 contrapositive gives a nought reading (N2) |
| booked, "recount" line | variance | Yes. B 50/48/null → -2 | Same (N2), and stronger, because the line is literally pending recount |

Everything else (variance, graded tolerance, status, value, adjusted booked, shrink) is governed.

## Witnesses (updated)
| line | variance | tolerance | status | value | booked |
|---|---|---|---|---|---|
| A 240/238/239 @18450 | -1 | 0 | adjust | -18450 | -1 |
| B 1200/1188/null @320 | -12 | 24 | ok | -3840 | -12 |
| C 90/97/96 @75 | 6 | 4 | adjust | 450 | 6 |
| example shrink | | | | 18450 | |
| B 50/48/null @1 | -2 | 1 | recount | -2 | -2 |
| C 20/21/null | 1 | 1 | ok | 1 | 1 |
| D 70/74/null | 4 | 4 | ok | 4 | 4 |
| D 50/53/53 | 3 | 2 | adjust | 3 | 3 |
| Z 30/33/null | 3 | 2 | recount | 3 | 3 |
| A 100000/0/100000 @1000000 | 0 | 0 | ok | 0 | 0 |

## PART 2 — Solver-path screen
A) Pre-mortem: the graded fixes (final count, per-class floor tolerance, recount status, shrink) are straightforward and verifiable against the example. The failures concentrate on two kept sites. (1) Solvers "clean up" the tolerance into a single per-class function and floor it for every class, or give ungraded lines 0 or 5% floor, driven partly by 1.2. (2) Many solvers set booked to 0 on non-adjusted lines because the README calls it units posted to stock. The fuzz includes every class letter and many non-adjusted lines, so either slip fails nearly every sheet. Solvers that read the silence clause literally pass.

B) Scores (1 to 5, 5 = strongly resists)
- reference_unreachable: 5. There is now one derivable answer.
- authority_incomplete_for_grading: 4. N1 is a minor residual.
- hidden_state_not_closed_form: 4. Half-to-even is visible in the code.
- restraint_traps: 3. There are two sites. Kept round() for ungraded classes passes the screen (it is a definition chain from 2.3 "graded item", and the fix must stop inside a tolerance function the repair rebuilds). Kept booked on non-adjusted lines is borderline: it has a definitional chain via 3.3, but strong contrary instinct (N2).
- fuzz_blind_spot: 4

C) self_verification_resistance: 3. The example has no ungraded line, and its ok line's booked (-12) is only kept if the solver leaves it. Prediction: 2 to 4 of 8 pass, failures mostly on booked, some on ungraded rounding. Confidence: medium. Decisive reason: the contract is now closed, but the booked trap relies on the solver resisting the README's "posted to stock" instinct.

### Departures of shipped package from CC-2 (r2)
1. The final count ignores the recount (2.1).
2. There is a single 5% tolerance for classes A, B and C; it should be 0, 2% and 5% (2.3).
3. The graded tolerance uses round() instead of dropping the fraction (2.3).
4. There is no "recount" status (3.1).
5. Shrink nets surpluses and can go negative (3.4).
(booked=variance is correct for adjusted lines and kept for the others. value already follows 3.2 once variance uses the final count. The ungraded tolerance is kept.)
