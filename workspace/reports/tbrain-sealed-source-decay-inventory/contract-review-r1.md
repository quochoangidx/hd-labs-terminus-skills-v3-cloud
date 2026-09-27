# Contract review r1: tbrain-sealed-source-decay-inventory

Scope: I read only `instruction.md` and `environment/` (Dockerfile, .dockerignore, app/README.md, app/docs/source-inventory-manual.md, app/examples/small-inventory.json, app/tools/sealsrc_run.py, app/src/sealsrc/*.py).

## Part 1: Contract review

### Defects the package carries (from comparing it with the manual)

1. `decay.activity_on` uses `exp(-t/T)` where 3.1 says `2^(-t/T)`.
2. `nuclides.DAYS_PER_YEAR = 365`, but 1.4 says 365.25.
3. `dates.elapsed_days` counts 30-day months, but 1.2 says real Gregorian days.
4. `decay.daughter_activity` returns the parent activity and ignores the branching fraction (3.2).
5. `checks.is_exempt` compares the parent alone, but 4.1 compares the total.
6. `checks.leak_test_due` tests `ref_bq` where it should test current activity, and it has no alpha threshold of 3.7e5 (5.1).
7. `checks.disposal_eligible` uses `A <= A_ref/1000`, but 7.1 says elapsed >= 10T.
8. `locations.location_rows` sums `ref_bq` where it should sum current activity, and it counts disposal-eligible entries, which 1.7/6.1 remove from storage.

Every one of these maps to a visible manual sentence. This is a closed-form list.

### Findings

**F1 (polish): the float expression and summation order are not fixed.** 1.1 says "carried and reported at the full precision of the arithmetic". That phrase does not fix a formula form (`A*2**(-t/T)`, `A*0.5**(t/T)`, `A*exp(-t*ln2/T)`), the total form (`A + A*b` or `A*(1+b)`), or the order of the location sum (inventory order, `math.fsum`, sorted).
- Counterexample: a store holding reference-date entries of 1e14, 3 and 3 Bq with limit 100000000000006.0. Summed left to right in inventory order the held total is 100000000000006.0, so `over_limit` is false. `math.fsum` gives the same value here, but ULP-level gaps between summation forms can appear on other multi-term sums. So `over_limit` can flip when the limit is set to an exact float sum.
- I checked the exactly constructible boundaries: Cd-109 at t=4619 d (10 T) and Ge-68 at t=5419 d (20 T). All four decay forms give exactly 1.0e6, 5.0e4 and 3.7e6 there. Formula form is therefore safe at the practical boundaries.
- Risk: if the verifier compares numbers with a relative tolerance and builds boundaries at t=0 or at integer half-lives, there is no issue. If it compares floats exactly, or builds a location limit from a multi-term float sum, a correct solution can fail.
- Fix: state "summed in inventory order" or compare with a tolerance.

**F2 (polish): the paragraph-2 wording is convoluted.** The instruction says: "keeping the step the package takes for it today comes before anything else in this paragraph, and every other step it goes through still follows the manual."
- The reading is recoverable: keep `max(days, 0)` and fix everything else. Under that reading a future-dated certificate gets t = 0, A = A_ref, and is not eligible.
- I brute-forced about 55k (ref, survey) pairs with ref after survey. The 30-day count and the Gregorian count both clamp to 0 on every pair, so "the step" is unambiguous in its output.
- A solver who rewrites `elapsed_days` with `date` subtraction and drops the `max` gets negative t and a grown activity. The instruction forbids that clearly enough, so this is not a defect.

**F3 (polish, no conflict): a leak test dated after the survey date is positively governed.** It is governed by 5.2 ("more than 182 days ... before the survey date" is false, so the entry is not due). The package's clamp gives the same answer. The instruction does not call this case silent, so nothing conflicts.

**F4 (none, noted): a disposal-eligible entry is still subject to 4.1 and 5.2.** 1.7 removes it only from "in storage", and 5.2 has no storage condition. Example: a P-32 entry with A_ref 1e14, ref 2031-01-01, survey 2031-05-24 (t = 143). It gives A = 9.6149847480e10, and it is leak-testable, due, eligible and excluded from its store. A solver might suppress the leak-test flag for logged sources out of instinct. The authority is positive here, so this is not ambiguous.

**Goal, schema and ranges.** The goal is clear. The README fixes the report keys and types. Every range has a floor and a ceiling: activity 1 to 1e14, dates 1950 to 2099, limits 1 to 1e18, entries 0 to 5000 (the instruction says "up to 5000", which is consistent), locations 1 to 200. The comparisons each have an explicit direction:
- exempt: <= ("at or below")
- leak threshold: >= ("reaches ... or more")
- leak interval: > ("more than 182")
- disposal: >= ("ten times ... or more")
- short-lived: <= 120 ("or less")
- over limit: > ("more than")

There is no tie-breaking or ordering convention without an authority; 8.1 fixes inventory order.

**Preservation and silence line.** The line is drawn with defined terms. "Elapsed time" (1.3) is defined only for survey >= reference, so the future-certificate case really is silent in the manual. The left-open list in the instruction (out-of-range values, unknown nuclide, dangling location, duplicate ids, malformed file) matches the complement of 1.5 exactly. No manual sentence governs a case the instruction calls silent.

**Verdict:** no blocking or should-fix defects.

### Grounded witnesses (worked by hand, confirmed with a scratch Python one-liner)

1. **30-day vs Gregorian.** Co-60, ref 2031-01-31, survey 2031-03-01. Manual t = 29; the package gives 30.
2. **Leap day.** ref 2028-02-28, survey 2028-03-01 gives t = 2. ref 2028-02-29, survey 2029-02-28 gives t = 365.
3. **Future certificate.** Ref 2032-01-01, survey 2031-09-30: t = 0 (kept clamp), activity = A_ref, disposal false.
4. **Cs-137 exemption.** Cs-137 with A_ref 1e4 on its reference date gives activity 1e4, daughter 9440.0, total 19440 > 1e4, so exempt is false. The package says true.
5. **Sr-90 exemption at the boundary.** Sr-90 with A_ref 5e3 on its reference date gives daughter 5e3 and total exactly 1e4, so exempt is true.
6. **Alpha leak threshold.** Am-241 with A_ref 3.7e5 on its reference date and no test on record is leak-testable (alpha threshold) and due. The package says false.
7. **182-day interval.** Last test 2031-03-31, survey 2031-09-30 is 183 real days, so the entry is due. The package counts 179 and says not due.
8. **I-125 disposal.** I-125, ref 2031-01-01, survey 2032-08-17 (t = 594 < 594.9) is not eligible. Survey 2032-08-18 (t = 595) is eligible. A solver who keeps the `A <= A_ref/1000` test with correct days gets 986.86 <= 1000 on t = 594 and wrongly says eligible.
9. **`examples/small-inventory.json` (survey 2031-09-30).**
   - CS-0107: activity 236305533.173434, daughter 223072423.31572166, exempt F, due F (151 d since last test), disposal F.
   - AM-0012: activity 3509940.1610663035, daughter 0.0, exempt F, due T (alpha, 285 d), disposal F.
   - CO-0310: activity 22868951.04505732, exempt F, due T (no test), disposal F.
   - BA-0044: activity 171964.31990477606, exempt T, due F, disposal F.
   - HOTLAB-SAFE: held 239815473.33450028, sources 2, fraction 4.7963094666900056e-4, over F.
   - B14-CABINET: held 23040915.364962094, sources 2, fraction 0.11520457682481047, over F.
10. **Store with an eligible entry, and an empty store.** A store with one eligible P-32 entry and nothing else gives held 0.0, sources 0, fraction 0.0, over F. The same holds for an empty store. A limit exactly equal to held gives over F.

None of these needed a guess. The only unforced choice is float expression and summation form (F1), and it does not change any witness above.

## Part 2: Solver-path screen

**A) Pre-mortem.**
- A strong solver reads the 60-line manual next to the roughly 150-line package, and the eight defects are one-to-one with manual sentences.
- It would replace `elapsed_days` with `date.fromisoformat` subtraction and `max(...,0)`, use 365.25, write `2**(-t/T)`, multiply by the branching fraction, test the total for exemption, and use current activity with per-class thresholds.
- It would switch disposal to `t >= 10*T` and rebuild `location_rows` from the per-entry current activity, skipping eligible entries.
- It would self-check with a from-scratch reference plus date and boundary unit tests; every rule is a single arithmetic comparison, so its reference and the hidden one converge.
- Plausible slips:
  - dropping the negative clamp; the instruction explicitly warns against this.
  - forgetting the "in storage" exclusion in the location aggregate. 1.7 and 6.1 both use the defined term, and a careful reader catches it.
  - suppressing leak or exempt flags for logged entries.
- I expect a strong solver to avoid all three.

**B) Scores (1 = easy, 5 = strongly resists)**

| Axis | Score | Reason |
|---|---|---|
| reference_unreachable | 1 | The whole oracle is a direct transcription of the manual. |
| authority_incomplete_for_grading | 1 | Every figure and flag is determined; F1 is ULP-level only. |
| hidden_state_not_closed_form | 1 | Stateless, per-entry closed form plus one sum. |
| restraint_traps | 2 | See the breakdown below. |
| fuzz_blind_spot | 1 | Random inventories within 1.5 exercise every rule; the boundaries are simple comparisons that a solver's own fuzz against a hand reference covers. |

Restraint-trap breakdown:
- The "in storage" exclusion inside the rebuilt location aggregate is reached through the definitional chain 6.1 → 1.7 → 7.1. It counts.
- Keeping the future-date clamp is a kept routing decision. It counts, but it is weak because the instruction names it.
- Leak or exempt flags on logged entries count zero: 5.2 governs them positively and there is no strong contrary instinct.

**C) Verdict**
- self_verification_resistance: 1
- prediction: collapses (both of two solvers fully solve)
- confidence: high (about 0.85)
- decisive_reason: Every defect is a one-line mismatch with a single explicit manual sentence, and the only multi-step inference (disposal-eligible entries leave the store) sits in two adjacent defined-term sentences, so a strong solver can rebuild and self-verify the exact reference.
