# Contract review r1 — tbrain-microbial-plate-count-reporting (reviewer B)

Scope: instruction.md + environment/ only.

## Part 1 — Contract review

Defects visible in the shipped code against SOP: `plated_amount` ignores volume (2.2); range 25–250 vs 20–300 (2.4); `colonies(None)=0` makes TNTC neither crowded nor countable (2.5), so an all-TNTC sample goes to "below"; only the first countable dilution is counted, not the next step (2.7); Python `round` is half-even (1.2); "above" uses first dilution and 250 (4.4 says last dilution and 300); "estimate" pools every non-crowded plate across dilutions (4.2 says first dilution holding a colony only); "below" uses last dilution (4.3 says first). Goal, schema (README) and output format are otherwise clear.

1. **should-fix (borderline blocking) — mixed crowded + sparse sample with no countable plate is ungoverned, and "keep today's figure" leaves it open to more than one reading.** 4.1 needs a countable plate, 4.2/4.3 need a *sparse sample* ("every one of whose plates is sparse"), 4.4 needs every plate crowded. A sample such as step1 `[400, 5]` or `[null, 3]` matches none of them. The instruction says "keep the figure that step works out today, from the figures the SOP does define". Readings:
   - (a) keep `estimate()` pooling, with SOP classes: TNTC and >300 are crowded and excluded, and volume is in the plated amount. `[null, 3]` at step1 vol 1.0 gives 3/0.1 = 30 → estimate `3.0E1`.
   - (b) keep literal today's code, where TNTC is counted as a 0-colony non-crowded plate: 3/0.2 = 15 → `1.5E1`.
   - (c) a solver applies 4.2 anyway ("first dilution with a colony"). For `[400,5]@1, [2,0]@2` pooling gives 7/(0.1+0.02)=58.3 → `5.8E1`, but 4.2-style gives 5/0.2=25 → `2.5E1`.
   - Mixed with zero colonies on the non-crowded plates, e.g. `[null,0]@1, [0,0]@2`: today's step gives BELOW with the **last** dilution, 1/0.01 → `<1.0E2`. A solver who rewrites `estimate` to follow 4.3 gets the first dilution, `<1.0E1`. Which "step" owns that figure depends on how the solver refactors.
   The instruction names this as the governed/silent line ("mixed" samples are not listed as left open, and the batch description lists only "countable at one or several", "no countable plate at all"), so it is graded. Reading (a) is the most defensible, but it relies on the solver keeping a pooling function the SOP never describes. Fix: add an explicit sentence, or add a SOP rule for mixed samples.
2. **polish — 2.7 "the dilution a tenth of that one, when the analyst plated it".** This is clear for a skipped step (k, k+2 means k+2 is not counted), but a solver could still read it as "the next listed dilution". Example: `[250]@1, [30]@3` gives `2.5E3` under the SOP reading and (250+30)/(0.1+0.001) = 2772 → `2.8E3` under the misreading. The authority is fine, so this is a trap and not a defect.
3. **polish — countable plates on the counted dilutions only.** 4.1 says "countable plates of its counted dilutions", so a 19 or 301 on those dilutions is excluded. This is clear.
4. **polish — 2.6 / 2.5 edge cases.** A reading of 301 is crowded, 300 is countable, 20 is countable and 19 is sparse. Floors and ceilings are all stated, and ranges in 1.3 are inclusive.
5. Rounding and format (1.2) have a full authority sentence with examples. Order and exact fields come from the README. No other arbitrary convention is missing.

### Witnesses (hand-worked)
| # | input | output |
|---|---|---|
| W1 | RM-101 example: @1 [TNTC,TNTC], @2 [212,187], @3 [19,24] (mL, v1.0) | count `2.0E4` (423/0.021=20142.9) |
| W2 | CH-7: @1 [4,7], @2 [0,1] g | estimate `5.5E1` (11/0.2) |
| W3 | YG-22: all zeros @1,@2 | below `<1.0E1` (first dilution, 1/0.1) |
| W4 | @3 [TNTC,TNTC], @4 [TNTC,400] | above `>3.0E6` (300/1e-4, last dilution) |
| W5 | @1 v1.0 [125] | count `1.3E3` (half up; the current code gives 1.2E3) |
| W6 | @1 v0.1 [250], @2 v1.0 [30] | count `1.4E4` (280/(0.01+0.01)) |
| W7 | @1 [250], @3 [30] (skip) | count `2.5E3` |
| W8 | PT @2 v0.1 [45,50] | count `4.8E4` (95/0.002=47500) |
| W9 | @1 [TNTC,3] | GUESS: estimate `3.0E1` (reading a) |
| W10 | @1 [TNTC,0], @2 [0,0] | GUESS: below `<1.0E2` (today's last-dilution figure) vs `<1.0E1` |

W9 and W10 needed a guess.

## Part 2 — Solver-path screen

A) Pre-mortem: a strong solver reads the short SOP and diffs each clause against 60 lines of code. It finds all eight defects (volume, 20–300, TNTC as crowded, 2.7 next step, half-up rounding, above last/300, estimate first-colony dilution, below first dilution) and rewrites `results.py`/`plates.py` with Fractions. It builds its own reference from the SOP and fuzzes it, which confirms everything except the mixed crowded+sparse branch, where the reference is the solver's own interpretation. The likely failures are (i) the mixed branch (whether to keep the pooling, keep last-dilution BELOW, or rewrite it to look like 4.2/4.3) and (ii) the step+1 versus next-listed misreading. Missing a single edge in the rounding or TNTC classification is unlikely, because each is named in the instruction's symptoms.

B) Scores: reference_unreachable 1; authority_incomplete_for_grading 3 (the mixed branch is a defect); hidden_state_not_closed_form 1; restraint_traps 2 (keeping the ungoverned mixed-branch pooling inside `estimate()`, which the 4.2 repair forces the solver to rebuild; the step+1 rule is in the rule sentence and scores 0); fuzz_blind_spot 2 (mixed samples only).

C) self_verification_resistance 2. prediction: collapses (the mixed branch is the only realistic point of failure, and if it fails that is ambiguity, not difficulty). confidence: medium. decisive_reason: every graded defect is named plainly by a short SOP clause and is closed-form, so the only thing that resists a solve is the underspecified mixed crowded+sparse case, which is a contract defect to fix rather than legitimate difficulty.
