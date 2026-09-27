# Contract review r3: tbrain-occupational-noise-dose-survey (fairness recheck)

Scope: I read only the r3 `instruction.md` and `environment/`: the Dockerfile, README, manual HC-4, `src/noisedose/*`, the driver and the example. I re-read the manual and the dose code in full.

## What the packet now says

**Manual changes**
- 2.3 now adds "one logged no higher than the ceiling level is counted at its own level".
- 2.5 now defines a **partial survey**: sampled time is at least 3/4 of the shift but shorter than the shift.
- 3.3 now reads: a partial survey projects to the shift; sampled time >= shift uses the measured dose. Surveys with sampled time below 3/4 of the shift are no longer mentioned.
- 3.1 and 3.2 now use "the level it is counted at".
- 5.1 now names "the ceiling level" as 115.0.

**Code change**
- `runs.py` now counts each run at `min(level, CEILING_DBA)`.

**Instruction changes**
- The preservation rule now reads: "keep the figure that step works out today, from the figures the manual does define; every other step still follows the manual".
- The r2 "for instance ... sampled too little" pointer is gone.
- The goal narrative is narrowed to long shifts "whose dosimeters ran most of the day".
- The test list now includes readings "up to 140.0 dBA" and surveys sampling "anything from a few minutes of the shift to more than all of it".

## Part 1: Is every graded value uniquely derivable?

### Unruled figures

**U1: the shift dose when sampled time is below 3/4 of the shift.**

(a) Is it detectably unruled? Yes. 2.5 bounds "partial survey" to [3/4·shift, shift), 3.3's first sentence covers only partial surveys, and its second covers only s >= shift. The three cases (s >= shift, partial, the rest) partition the input, so a careful engineer writing the branch structure is forced to confront the third case. Nothing else in the manual names the shift dose. 6.1 and 4.1 consume it but do not define it.

(b) What does keeping today's step yield? From `shift.py`: `sampled == 0 → 0.0`; `sampled < 480 → measured × 480 / sampled`; otherwise `measured`. The new clause "from the figures the manual does define" closes r2's F1: the `sampled` and `measured` fed in are the manual's sampled time (all readings >= 40.0, not 0.0 runs) and measured dose (85/3, >= 80.0, U1 counted level). The 480 is the step's own constant; it is not a manual figure to substitute.

Unique. The r2 counterexample (shift 480, `[[120, 88.0], [120, 70.0]]`) now has a single answer: sampled 240, measured 50 → 100 / 85.0 / action. The counted-only reading (200 / 88.0) is excluded by "from the figures the manual does define".

**U2: the level at which a reading above 115.0 dBA is counted.**

(a) Is it detectably unruled? Yes. 2.3 defines a counted reading as any reading >= 80.0. It fixes the counted-at level only for readings "no higher than the ceiling level". 3.2 needs "the level it is counted at" for every counted reading. So for readings above 115.0 the level is used but never given.

(b) What does keeping today's step yield? `counted = min(level, CEILING_DBA)` gives 115.0, which is the manual's ceiling level. Unique. The threshold test in that step follows the manual (>= 80.0 on the logged level), and it has the same outcome for these readings.

Counterexample if misread: shift 480, `[[480, 118.0]]`.
- Correct: 102400 → 115.0 → over (ceiling flag set).
- Own-level: 204800 → 118.0.

Status is "over" either way. `dose` and `twa` differ, and so does any group row containing the worker.

**Other candidates checked; all are ruled:**
- 0.0 runs: not readings (2.2), so no sampled time and no dose.
- Readings from 40 to 79.9: add sampled time (2.4) but no dose (3.2).
- Dose 0: no TWA (4.1).
- Workers without a TWA: status below (5.3).
- Group membership: every member now has a shift dose (U1 guarantees 0.0 for no readings).
- Ordering and format: README.
- Ceiling and impulse flags: 5.1 and 2.6.
- Rounding: 1.2.

I found no sentence in the authority that positively governs a value the instruction treats as unruled, and no unruled value that is graded without a determinable step.

### Findings

**F1 (should-fix, low): the "no clamp" sentence competes with the kept clamp.**
Citations: "Add no exception, clamp or guard that the manual does not give" versus `counted = min(level, CEILING_DBA)`, a clamp the manual does not give.
The verb is "add", and the preservation sentence explicitly keeps today's step for unruled figures, so the correct reading is determinable. But a solver who reads "clamp" as a ban may delete `min()`. See the U2 counterexample: 102400 / 115.0 versus 204800 / 118.0.
It is fair as written. Optional: "Add no new exception ..." or "keep the ones it has for figures the manual leaves open".

**F2 (should-fix / trap check): the kept legacy branch below 3/4 of the shift.**
- Shift 720, `[[500, 85.0]]` (500 < 540): unprojected 104.1667 → 85.2, "over". A projection to the shift gives 150 → 86.8.
- Shift 90: `[[67, 85.0]]` → 100 / 85.0 / action; `[[68, 85.0]]` → 18.75 / 77.8 / below.
- Shift 1440, `[[400, 140.0]]` → 102400 / 115.0. Projecting to the shift gives about 307200 / 119.8; dropping the clamp too gives about 3.3e7 / 140.0.

This is a definitional-chain trap and the text determines it. Removing the r2 pointer makes it less signposted but not ambiguous. The discontinuity at the 3/4 boundary is intended.

**F3 (polish): "partial survey" means different things in code and manual.**
The docstring in `shift.py` uses the term for "less than a full day". HC-4 2.5 now defines it as [3/4·shift, shift). The manual governs, and the code comment is not an authority. This is a mild naming trap, not a defect.

**F4 (polish): half-up rounding on floats.**
Unchanged from r1/r2. `round()` differs from half-up only at binary-exact .x5 values (84.25, 84.75), which are reachable only by float coincidence. The generator should stay at least 1e-9 away from them. Levels above 115 now produce exact powers of two (TWA exactly 115.0), which are safe.

**Checks passed.**
- Every 1.4 range has a floor and a ceiling.
- The 3/4 test is exact in integers (4s >= 3·shift).
- The r2 goal-narrative tension (F3 there) is fixed by "whose dosimeters ran most of the day": P-0117 (410 of 600) is not "most" at the 3/4 bar.
- The open list matches 1.4.

## Hand witnesses

Single worker, no peaks unless stated.

| # | Input (shift; log) | dose; twa; status | Guess? |
|---|---|---|---|
| W1 | 480; `[[360, 85.0]]` (partial, exactly 3/4) | 75 × 480/360 = 100; 85.0; action | no |
| W2 | 480; `[[359, 85.0]]` (U1 legacy) | 74.79 × 480/359 = 100; 85.0; action | no |
| W3 | 720; `[[500, 85.0]]` (U1, s >= 480) | 104.166667 (unprojected); 85.2; over | no |
| W4 | 480; `[[120, 88.0], [120, 70.0]]` (U1 with manual sampled time) | 100; 85.0; action | no |
| W5 | 90; `[[67, 85.0]]` → 100; 85.0; action. 90; `[[68, 85.0]]` → 18.75; 77.8; below | | no |
| W6 | 480; `[[480, 118.0]]` (U2) | 102400; 115.0; over; ceiling T | no |
| W7 | 480; `[[1, 120.0]]` (U1 + U2) | 213.333 × 480/1 = 102400; 115.0; over; ceiling T | no |
| W8 | 480; `[[480, 115.0]]` | 102400; 115.0; over; ceiling F (TWA > 85) | no |
| W9 | 480; `[]`; peaks `[140.0]` | 0.0; null; over; impulse T | no |
| W10 | 480; `[[480, 80.0]]` → 31.498026 / 80.0 / below. `[[480, 82.0]]` → 50 / 82.0 / action | | no |
| W11 | `examples/press-shop-day.json` | P-0117 286.936916 / 89.6 / over (410/600 is not partial → legacy to 480); P-0122 234.718144 / 88.7 / over; P-0130 370.172922 / 90.7 / over (380/480 partial); T-0041 46.102988 / 81.6 / over (impulse 142.6); T-0048 0.0 / null / below. PRESS 297.275994 → 89.7 over; TOOL2 23.051494 → 78.6 below | no |

No witness needed a guess.

## Part 2: Solver-path screen

**A) Pre-mortem.**
A strong solver diffs the modules against HC-4 and fixes the constants (85/3, >= 80), sampled time over all readings, half-up rounding, the bands, `>= 140` impulse, and the group mean of unrounded shift doses. It then reaches `shift.py`. Writing the 2.5/3.3 branches forces a third case (below 3/4). The preservation paragraph tells it to keep today's step fed by manual figures, and a careful solver does. It then fuzzes against a self-written reference, which shares its readings. The failure modes:
- (i) Rewriting `measure()` from scratch and dropping `min(level, CEILING_DBA)`, possibly citing "add no ... clamp".
- (ii) Projecting every sub-shift survey to the shift, following the lead's complaint and the code's own "partial survey" docstring.
- (iii) Replacing the legacy `480` with the shift.

Minimal-diff solvers keep (i) by default. For (ii) and (iii) the solver must spot a gap that is no longer named. Self-fuzzing cannot detect any of the three.

**B) Scores** (5 = strongly resists solving):
- reference_unreachable: **2**. Closed form; the two legacy steps are visible in the code.
- authority_incomplete_for_grading: **1**. Both unruled figures are detectable and uniquely resolved. F1 is a wording tension, not an ambiguity.
- hidden_state_not_closed_form: **1**.
- restraint_traps: **3**. Three qualifying sites inside aggregates the repair forces the solver to rebuild:
  - the legacy shift-dose branch below 3/4 (2.5 definitional chain);
  - the kept 115.0 counted-level clamp, which sits inside the measured-dose rewrite (2.3 restrictive clause);
  - 0.0 runs left out of sampled time (2.2 "reading" definition).

  None fails the 0/8 screen: no competing positive enumeration exists in the authority, each has a definitional chain, and the contrary instincts (project to shift, count at own level) are countered by explicit text. The ceiling-flag strictness, the impulse `>=` and the lack of flags on groups are in their rule sentences and score zero.
- fuzz_blind_spot: **3**. All three traps are reading choices that a self-built reference reproduces.

**C) Verdict.**
- self_verification_resistance: **3**
- prediction: **collapses** (borderline; a split of one solver at 1/2 is plausible)
- confidence: about 0.55
- decisive_reason: every graded value is now uniquely derivable. Both unruled figures fall out of the text, and a careful solver who writes the three-way 2.5/3.3 branch and keeps `min()` solves it fully. The residual risk is solvers who rewrite `measure()` or generalise the projection, not contract ambiguity.
