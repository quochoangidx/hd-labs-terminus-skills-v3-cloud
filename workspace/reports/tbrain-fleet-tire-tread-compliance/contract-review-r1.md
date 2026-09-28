# Contract review r1 — tbrain-fleet-tire-tread-compliance (reviewer C)

Scope: instruction.md + environment/ only.

## Part 1 — Contract review

### Findings

1. **should-fix — depth of a non-measurement reading.** 4.1: "A tire's latest depth is the depth of its latest reading." 3.1 defines depth only for "a measurement" (2.1: shown >= 10). A wear-bar reading therefore has no standard depth, and the instruction's precedence paragraph sends it to today's code (`depth = shown`, no offset). A second reader can take 4.1 as positively saying every reading has a depth and apply 3.1 to it anyway, or read 1.5 ("the probe rests on the bar itself") as depth = 0. Counterexample: drive tire, latest reading `[.., .., 5, G]` where G has offset +3. Reading A (intended) latest=5; reading B latest=8; reading C latest=0. `worn`/`rate` differ across all three; `status` is `pull` in every reading. The line holds, but it rests on a single defined term and on "the depth of" in 4.1 being read as not governing. Suggest one sentence stating what 4.1 means when the latest reading is not a measurement, or accept this as the intended restraint site and keep it.
2. **should-fix (intended trap, check wording) — tread worn / distance for a non-fresh tire.** 4.2 governs only "A fresh tire's tread worn". For a moved-over tire no rule settles worn or distance, so today's `depths[0]-depths[-1]` over first-to-last reading odometers applies, with standard depths (offsets) as inputs. The competing reading (new_depth − latest over mount-to-latest for every tire) is what "new tires are credited with far slower wear" invites a solver to generalise. Counterexample: new 200, mounted 90000, readings `[.., 100000, 150, g0]`, `[.., 120000, 110, g0]` (offset 0): intended worn 40 / dist 20000 / rate 20; generalised worn 90 / dist 30000 / rate 30. The precedence paragraph is explicit, so this is a fair trap.
3. **polish — fresh when first depth exceeds new depth.** 2.3 "no more than 10 tenths below" literally makes a first depth above `new_depth` (positive offset) fresh; an abs-difference reading makes it fresh too unless >10 above. Counterexample: new 60, first shown 72 offset +9 = 81 (21 above). Literal: fresh; abs reading: not fresh. Literal reading is the natural one.
4. **polish — negative worn / rate.** Readings are not required to decrease, so a fresh tire can have latest > new_depth. Half-up "to the larger number" (1.1) settles negative halves (-2.5 -> -2). Clear. Python `round` would give -2 here as well, so the difference only shows on positive halves.
5. **OK — rounding.** 1.1 gives an authority sentence for the only division (4.3). Only `rate` is divided. Integer arithmetic `(2n + d) // (2d)` is exact.
6. **OK — ranges.** Every numeric input has a floor and ceiling (1.3–1.5). Distance > 0 is guaranteed for both the mount-based and the reading-based distance (1.5).
7. **OK — status / retread.** 2.4, 5.1 ("at or below") and 6.1 (age in days `< 2190`, retreads `< 2`, pull only) are unambiguous. Casing age is report_date − casing in days.
8. **polish — ordering.** Readings are "in date order", and the code uses list order. That is consistent, and out-of-order input is left open.

No sentence in the standard positively governs a case the instruction calls open, apart from the 4.1 "depth of its latest reading" wording in finding 1.

### Witnesses (hand-worked)

- W1 (sample job): latest 91, fresh (175 ≥ 166), worn 85, distance 67812, rate 850000/67812 = 12.53 → 13, steer 91 > 56 → in service, retread false.
- W2 status boundaries: steer latest 40 → pull, 56 → watch, 57 → in service; drive/trailer 32 → pull, 48 → watch, 49 → in service.
- W3 wear-bar: drive, latest shown 5 on a +3 gauge → latest 5 (not 8), pull. *(guess-adjacent: relies on finding 1)*
- W4 non-fresh: see finding 2 → worn 40, distance 20000, rate 20.
- W5 half-up: fresh, worn 1, distance 4000 → 2.5 → rate 3 (today's code gives 2).
- W6 retread: pulled, retreads 1, report 2025-03-31, casing 2019-04-03 → 2189 days → true (today's code gives false, year diff 6). Casing 2019-04-01 → 2191 → false. Casing exactly 2190 days old → false. Retreads 2 → false. Not pulled → false.
- W7 negative: fresh, new 60, first 65, latest 70, worn −10, distance 40000 → −2.5 → −2.
- W8 non-measurement with negative offset: shown 9, offset −9 → latest 9. Shown 10, offset −9 → measurement, latest 1.

## Part 2 — Solver-path screen

A) Pre-mortem: a strong solver reads the 7-section standard and fixes gauges.py (offset), status.py (steer 40, `<=`), retread.py (days, `<`, pull-only), rounding.py (half-up integer) and wear.py (new − latest from mount for fresh tires). It then writes a small reference and property tests. The likely failure points are (a) applying the offset to every reading instead of only measurements (shown >= 10), because the one-line fix in `reading_depths` is the natural edit, and (b) generalising 4.2 to non-fresh tires, or failing to keep today's first-to-last worn/distance for them. The solver can also forget the "pull-only" gate on retread. The instruction's heavy restraint paragraph and the defined term "measurement" point directly at (a) and (b), so a careful Opus 5 or GPT-5.6 class solver will likely catch both. Its self-written tests share its own reading, so they will not catch a misread.

B) Scores:
- reference_unreachable: 2
- authority_incomplete_for_grading: 2 (see finding 1; otherwise closed)
- hidden_state_not_closed_form: 1
- restraint_traps: 3. Offset limited to measurements sits inside `reading_depths`, which the repair forces the solver to rebuild. The non-fresh worn/distance is a kept routing decision. Pull-only retread is written into the rule sentence and scores 0.
- fuzz_blind_spot: 2

C) self_verification_resistance: 2. Prediction: **collapses** (both solvers likely fully solve). Confidence: medium (about 60%). decisive_reason: every trap is signposted by a defined term ("measurement", "fresh") and the explicit "exactly as far as it reaches" paragraph, so a careful reader closes both restraint sites without hidden state.
