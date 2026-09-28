# Contract review r2: tbrain-sealed-source-decay-inventory

**Scope.** I read fresh only the r2 packet: `instruction.md` and `environment/` (Dockerfile, .dockerignore, README, manual, example, driver, `src/sealsrc/*.py`).

**Method.** I worked the witnesses out by hand from the manual. I then confirmed them with an inline Python reference that I piped over stdin, so no file was written.

## Part 1: Contract review

### Where the package departs from the manual

1. `decay.activity_on` uses `exp(-t/T)`. Rule 3.1 says `2^(-t/T)`.
2. `DAYS_PER_YEAR = 365`. Rule 1.4 says 365.25.
3. `dates.elapsed_days` counts in 30-day months. Rule 1.2 says real calendar days.
   - The `max(days, 0)` clamp is the "step the package takes today" for a reference date after the survey. It must stay.
4. `decay.daughter_activity` returns the parent activity. It should be the parent activity times the branching fraction (3.2).
5. `checks.is_exempt` compares the parent alone. Rule 4.1 compares the total.
6. `checks.leak_test_due` tests `ref_bq`. Rule 5.1 tests current activity. The per-class thresholds are already right.
7. `checks.last_leak_test` takes `wipes[-1]` (list order) and counts every wipe. The manual says otherwise:
   - 1.7: only wipes below 185 Bq are leak tests.
   - 5.2: take "the latest by date".
8. `checks.disposal_eligible` uses `A <= A_ref/1000`. Rule 7.1 says t >= 10T.
9. `locations.location_rows` sums `ref_bq`. Rule 6.1 says sum current activity. Its licensed filter (`ref_bq <= Q -> skip`) is correct in shape and must keep using the certificate figure (1.8).
10. No comparison applies the 1.1 rule that "two figures that agree to one part in 10^9 are the same figure". This touches exempt (<=), leak-testable (>=), licensed (>), over limit (>) and leak-test removable (< 185).

### Findings

**F1 (should-fix): does a leaky wipe fall outside the manual?**
- Citation, 1.7: "it is evidence of a leak, which the Office handles by its incident procedure rather than by this manual".
- Citation, instruction: "Where the manual gives no rule for a figure it defines, the answer the package gives for that figure today is the one the Office wants".
- Reading A (intended, I believe): 5.2 still decides `leak_test_due`. The leaky wipe simply isn't a leak test, and the latest qualifying test by date governs.
- Reading B: "rather than by this manual" makes an entry with leak evidence a case the manual doesn't provide for. The package's answer today (the list-last wipe, whatever its reading) then stays.
- Counterexample: Co-60, A_ref 1e7, ref 2031-01-01, survey 2031-09-30, wipes `[{2031-08-01, 12}, {2031-09-01, 400}]`.
  - A: last leak test 2031-08-01, 60 days before the survey, so not due.
  - B: the package's list-last wipe is 2031-09-01, so not due. The two agree here.
  - Reverse the wipe order to `[{2031-09-01, 400}, {2031-08-01, 12}]`. It still agrees (not due) under both.
  - Use wipes `[{2031-01-10, 12}, {2031-09-01, 400}]`. Reading A: last leak test 263 days before, so due. Reading B: the list-last wipe is 29 days before, so not due. The readings diverge.
- Reading A is better supported: `leak_test_due` is a figure 5.2 defines with a rule, and "leak test" is defined in 1.7. Still, the incident sentence reads like a carve-out.
- Fix: say "the wipe is not a leak test; section 5 still applies to the entry."

**F2 (polish): the tolerance metric in 1.1 is not fully defined.**
- Citation: "Two figures that agree to one part in 10^9 are the same figure".
- Open points: relative to which figure (the larger, the threshold, or the mean), and whether exactly 1e-9 counts as "agree".
- These readings differ only at about 1e-18 relative, or at an exact representable 1e-9 gap. A verifier is unlikely to probe that.
- Two points are clear: 1.1 makes every threshold decision tolerance-aware, and it also applies to raw inputs (`ref_bq` against Q in 1.8, `removable_bq` against 185 in 1.7).
- Counterexample: Co-60 with A_ref = 1e5·(1+5e-10) on its reference date.
  - With the tolerance: exempt is true, and the entry is not licensed, so held stays 0.0.
  - With strict comparisons: exempt is false, and the entry is licensed, so held is 100000.00005.

**F3 (polish): the "figure" named in the silence clause is loose.**
- Citation: "the answer the package gives for that figure today ... For such an input the step the package takes today stays".
- For a reference date after the survey, rule 1.3 leaves elapsed time undefined.
- Keeping the clamp (t = 0), or keeping today's current activity, gives the same answer: A = A_ref. Today's disposal answer (false) equals 7.1 at t = 0.
- I checked about 55k future-dated date pairs. The 30-day count and the real-day count both clamp to 0 on every one, so the outputs are unambiguous.

**F4 (none, noted): licensed material follows the certificate, not current activity.**
- Rules 1.8 and 6.1 say this positively and explicitly: "stays licensed however far it decays", "whatever its daughters add".
- So a decayed or disposal-eligible licensed entry still counts in held activity at its current activity.
- An exempt-by-certificate Cs-137 whose total exceeds Q is neither licensed nor exempt.
- The instruction's symptom "store postings that still carry the certificate figures" pushes a solver to swap `ref_bq` for current activity throughout `location_rows`. That swap would wrongly change the filter too.
- This is a real restraint site, not a defect.

**Goal, schema and ranges.**
- The goal is clear. The README fixes the input, including `leak_tests` in arbitrary order, and the output types.
- Every range has a floor and a ceiling, including removable activity (0 to 1e6), wipes (0 to 50), and no wipe dated after the survey.
- Comparison directions are all explicit: <=, >=, "more than 182", >= 10T, <= 120 d, "above" Q, "below 185".
- Summation order is now fixed (1.1, inventory order), and ordering is fixed by 8.1. No convention is left without an authority sentence.

**Preservation and silence.**
- The open list in the instruction matches the complement of 1.5.
- A reference date after the survey is genuinely silent: 1.3 defines elapsed time only when the survey is on or after the reference date.
- Apart from F1, no manual sentence governs a case the instruction calls silent.

**Verdict:** one should-fix (F1), no blockers.

### Grounded witnesses (survey 2031-09-30 unless stated; store L has limit 1e18 unless stated)

1. **The bundled `examples/small-inventory.json`.**
   - CS-0107: activity 236305533.173434, daughter 223072423.31572166, exempt F, due F (latest leak test 2031-05-02, 151 days), disposal F.
   - AM-0012: activity 3509940.1610663035, exempt F, due T (alpha, 285 days), disposal F.
   - CO-0310: activity 22868951.04505732, exempt F, due T (never wiped).
   - BA-0044: activity 171964.31990477606, exempt T, due F. It is not licensed (3.7e5 <= 1e6).
   - HOTLAB-SAFE: held 239815473.33450028, sources 2, fraction 4.7963094666900056e-4, over F.
   - B14-CABINET: held 22868951.04505732, sources 1, fraction 0.1143447552252866, over F.
2. **Cs-137 below its exempt quantity by certificate.** Cs-137, A_ref 1e4, on its reference date: activity 1e4, daughter 9440.0. Exempt is F (total 19440). Not licensed, so held 0.0 and sources 0.
3. **Sr-90 exactly on its exempt quantity.** Sr-90, A_ref 5e3, on its reference date: daughter 5e3, total exactly 1e4, exempt T. Not licensed.
4. **Tolerance band on Q.** Co-60 with A_ref 1e5·(1+5e-10) on its reference date: exempt T, not licensed, held 0.0. With strict comparisons it would be exempt F, and held would be 100000.00005 with sources 1.
5. **Leak-test boundary at 185 Bq.** Co-60, A_ref 1e7, on its reference date.
   - Only wipe `{2031-09-01, 185.0}`: no leak test on record, so due T.
   - Only wipe `{2031-09-01, 184.99}`: not due.
6. **Wipe order.** Co-60, A_ref 1e7, ref 2031-01-01, wipes `[{2031-08-01, 12}, {2031-02-01, 3}]` in list order.
   - Latest by date is 2031-08-01, 60 days before the survey, so due F. Activity is 9067183.715037204.
   - The package's list-last wipe (2031-02-01) would give due T.
7. **Reference date after the survey.** I-125, A_ref 5e6, ref 2032-01-01: t = 0, activity 5e6, testable, never wiped so due T, disposal F. Licensed (5e6 > 1e6), so held 5e6.
8. **Disposal-eligible entry stays in the store.** P-32, A_ref 1e8, ref 2031-05-10 (t = 143 >= 142.68): activity 96149.84748046967, exempt T, due F, disposal T. Still licensed, so held 96149.84748046967 and sources 1.
9. **Limit boundary.** Two Co-60 entries at 4e7 and 6e7 on their reference date in store L, limit 1e8: held 1e8, fraction 1.0, over F. A single entry of 1e8·(1+5e-10): over F (same figure), fraction 1.0000000005.
10. **Alpha threshold.** Am-241, A_ref 3.7e5, on its reference date, never wiped: leak-testable (alpha), due T. Licensed, so held 3.7e5.

Guesses: only for witness 6's F1-adjacent variants. I used reading A. The F2 metric does not affect any witness above.

## Part 2: Solver-path screen

### A) Pre-mortem

A strong solver would diff the roughly 90-line manual against the 7-file package and fix items 1–9 directly. That means:
- `date` subtraction with the clamp kept;
- 365.25 days per year and `2**`;
- the branching fraction and the total for exemption;
- current activity against the per-class threshold;
- a filter for wipes below 185 Bq and `max` by date;
- t >= 10T for disposal;
- held activity summed from current activity.

It would write its own reference and fuzz it against inventories. Likely slips, in order of risk:
1. Missing the 1.1 tolerance clause. It is one sentence in the units section, and ordinary fuzzing never lands in the 1e-9 band. The verifier's "exactly on a threshold" cases with float-computed totals (Cs-137, decayed values) or crafted near-equal inputs catch strict comparisons, both in the solver's code and in its self-written reference.
2. Rewriting the licensed filter onto current activity or onto the exempt determination while "fixing" the certificate figures in `location_rows`.
3. Applying reading B of F1, or taking the latest wipe regardless of its reading.
4. Dropping the future-date clamp. The instruction warns about this explicitly.

Items 2–4 are each caught by a careful reader. Item 1 is the most likely shared blind spot, but it is written in the authority, so it is fair.

### B) Scores (1 = easy, 5 = strongly resists)

| Axis | Score | Reason |
|---|---|---|
| reference_unreachable | 1 | Closed-form transcription of the manual. |
| authority_incomplete_for_grading | 2 | F1 carve-out wording; F2 metric is second-order only. |
| hidden_state_not_closed_form | 1 | Stateless per entry, plus an ordered sum. |
| restraint_traps | 3 | Three sites count; see below. |
| fuzz_blind_spot | 3 | Random fuzz won't hit the 1e-9 band, the exact-185 boundary, or out-of-order wipes with interleaved leaky readings unless the solver constructs them. The solver's own reference shares the same blind spot if it missed 1.1. |

Restraint-trap sites that count:
- The licensed filter must keep the certificate figure inside the location aggregate the repair forces the solver to rebuild. The defined-term chain is 6.1 → 1.8.
- Leaky wipes are an unlabelled subtype of wipe, excluded only by the 1.7 definition.
- The future-date clamp is a kept routing decision.

Sites that count zero:
- The tolerance clause, because it is written as a rule, not a restraint.
- Per-class thresholds, because they are labelled.

### C) Verdict

- **self_verification_resistance:** 2
- **prediction:** collapses (weakly; at least one of two strong solvers likely fully solves)
- **confidence:** medium (about 0.6)
- **decisive_reason:** Every departure maps to an explicit manual sentence, and a careful solver who reads 1.1 and 1.8 closely can rebuild the exact reference. The main thing keeping it alive is a solver skimming past the 1e-9 "same figure" sentence or rewriting the licensed filter onto current activity, and both are fully authorized, so a strong solver will usually catch them.
