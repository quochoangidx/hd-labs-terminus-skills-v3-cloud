# Contract review r1: tbrain-occupational-noise-dose-survey

Scope: I read only `instruction.md` and `environment/` (Dockerfile, README, manual HC-4, `src/noisedose/*`, `tools/noisedose_run.py`, `examples/press-shop-day.json`).

## Part 1: Contract review

### Summary of what the authority requires versus today's code

| Site | Code today | Manual HC-4 |
|---|---|---|
| Counted reading | `level > 80.0` | `>= 80.0` (2.3) |
| Criterion / exchange | 90 / 5 | 85 / 3 (3.1) |
| Sampled time | minutes of counted runs only | minutes of all *readings* (runs >= 40.0), so sub-threshold readings count and 0.0 runs do not (2.2, 2.4) |
| Projection target | 480 min | the worker's `shift_minutes` (3.3) |
| TWA formula | 90 + 16.61 log10 | 85 + 3 log2 (4.1) |
| TWA rounding | floor to tenth | nearest tenth, half up (1.2) |
| Status bands | over >= 90, action >= 85 | over > 85.0, action 82.0 to 85.0 inclusive (5.3) |
| Impulse | `> 140.0` | `>= 140.0` (2.5) |
| Ceiling | `> 115.0` | `> 115.0` on readings (5.1), which is unchanged |
| Group | mean of rounded member TWAs, dose from the federal formula | mean of unrounded member shift doses, TWA from 4.1, bands only (6.1) |

Goal clarity is good. The symptoms in the instruction line up with these defects: shifts longer than 480 minutes under-projected, the group averaged over TWAs, and the 140.0 impulse check. The output schema is fully given by the README, and the driver is kept byte for byte.

### Findings

**F1 (should-fix): group mean membership for a member with no shift dose.**
Citations: 6.1 "A group's dose is the mean of its members' shift doses"; 3.3 "A survey without a reading has no shift dose"; 1.3 "The mean of no figures is nought"; README "`0.0` for a worker who has no shift dose".
Two readings are defensible:
(a) A member with no shift dose contributes no figure and is left out.
(b) The member counts as the 0.0 the report prints.
There is also a third, natural wrong path: keeping today's `twa is not None` filter, which also drops quiet members whose shift dose is 0.
Counterexample: group G with A `[[480, 88.0]]` (dose 200), Q `[[480, 79.9]]` (quiet, shift dose 0) and E `[]`. All shifts are 480.
- (a) gives (200+0)/2 = 100 → TWA 85.0, "action".
- (b) gives 200/3 = 66.67 → TWA 83.2, "action".
- The today-filter gives 200 → 88.0, "over".

The 1.3 clause "mean of no figures is nought" can only apply under reading (a), so the text does point to (a). But the chain runs over three sections and the README's 0.0 representation invites (b). The fix is to add one clause to 6.1: "a member without a shift dose adds no figure; a member whose shift dose is nought adds nought".

**F2 (should-fix / trap check): sampled time and 0.0 runs.**
Citations: 2.2 "A reading is a run logged at 40.0 dBA or more"; 2.4 "sampled time is the total length of the worker's readings".
This is governed and unambiguous, but it sits inside the exposure aggregate that the repair forces the solver to rebuild. A solver who sets sampled time to the sum of all run minutes gets a different answer.
Counterexample: `[[240, 0.0], [240, 88.0]]`, shift 480.
- Correct: sampled 240, dose 200, TWA 88.0, "over".
- Sum-all reading: dose 100, TWA 85.0, "action".

This counts as a legitimate definitional-chain trap, not a defect.

**F3 (polish): half-up on binary floats.**
Citation: 1.2 "rounded to the nearest tenth of a decibel ..., an exact half going up".
Python `round(x, 1)` is correctly rounded on the binary value, so it differs from half-up only at binary-exact halves such as 84.25 or 84.75. `Decimal(repr(x))` and `floor(10x + 0.5)` also differ only within about 1e-14 of a half. A TWA lands exactly on such a value only by float coincidence, because every half needs an irrational dose. It is practically unreachable unless the generator deliberately constructs float-exact TWAs. It is worth confirming that the hidden generator avoids TWAs within 1e-9 of a .x5 boundary.

**F4 (polish): the preservation clause has no visible target.**
Citation: "Where it gives no rule for a figure, the figure the package works out today stands".
I could not find a reported figure that HC-4 plus the README leave ungoverned. Every figure has a governing rule: ids and groups echoed, order, dose 0.0 for no shift dose, group sort, flags, bands, projection, rounding. The clause is harmless, but it may push a solver to keep today's `twa is not None` group filter as "the step the code takes today", which is the F1 trap. If the clause is meant to protect something specific, it needs naming.

**F5 (polish): ceiling and impulse asymmetry.**
Citations: 5.1 "above 115.0 dBA" versus 2.5 "140.0 dBC or more".
Both conditions are written into their rule sentences, so the asymmetry is clear. It still invites a symmetry "fix" to `>= 115.0`.
Counterexample: `[[1, 115.0]]`, shift 480. Correct output: ceiling false, dose 102400, TWA 115.0, "over". Only the flag differs.
This counts zero as a trap.

**Checks passed.**
- Numeric ranges: every one in 1.4 has a floor and a ceiling, with ends included.
- Silent/open list: the instruction's list (out-of-range values, logs over 2,880 minutes, duplicate ids, non-README files) matches the 1.4 limits. Nothing in the manual positively governs any of them.
- Ordering, tie-breaks and output formats all have an authority sentence: README for order, 1.2 for rounding, the README key list for fields.
- Dose tolerance is stated.

### Grounded witnesses

All worked by hand from HC-4; each is a single worker unless stated.

| # | Input (shift; log; peaks) | Output (dose; twa; status; ceiling; impulse) | Guess? |
|---|---|---|---|
| W1 | 480; `[[480, 85.0]]` | 100; 85.0; action; F; F | no |
| W2 | 600; `[[300, 88.0]]` | 250 (125 × 600/300); 89.0; over | no |
| W3 | 480; `[[480, 80.0]]` | 31.498026; 80.0; below (threshold counts) | no |
| W4 | 480; `[[240, 79.9], [240, 88.0]]` | 100 (sampled 480, no projection); 85.0; action | no |
| W5 | 480; `[[240, 0.0], [240, 88.0]]` | 200 (sampled 240); 88.0; over | no |
| W6 | 480; `[]`; peaks `[140.0]` | 0.0; null; over; F; T | no |
| W7 | 480; `[[1, 115.0]]` | 102400; 115.0; over; ceiling F | no |
| W8 | 480; `[[480, 82.0]]` → 50; 82.0; action. `[[480, 81.9]]` → 48.857998; 81.9; below | | no |
| W9 | 60; `[[480, 85.0]]` | 100 (sampled over shift, not scaled down); 85.0; action | no |
| W10 | Group G = {A `[[480,88.0]]`, Q `[[480,79.9]]`, E `[]`} | group dose 100; 85.0; action | **yes (F1)** |
| W11 | `examples/press-shop-day.json` | P-0117 358.671144/90.5, P-0122 234.718144/88.7, P-0130 370.172922/90.7, T-0041 46.102988/81.6/over (impulse 142.6), T-0048 0.0/null/below. PRESS group 321.187403 → 90.1 over; TOOL2 23.051494 → 78.6 below (quiet T-0048 included as 0) | no |

## Part 2: Solver-path screen

**A) Pre-mortem.**
A strong solver diffs `levels.py`, `twa.py`, `exposure.py`, `flags.py` and `groups.py` against HC-4 and finds all ten deltas in the table above in one careful pass. Each is a one-line constant or operator change, plus rewriting `groups.py` to average unrounded shift doses. It then writes its own reference straight from the manual and fuzzes within 1.4, which agrees with its patch by construction. The places it can go wrong:
- The sampled-time rebuild: counting 0.0 runs, or still restricting to counted readings.
- The group rebuild: averaging the reported 0.0 of no-reading members, or keeping today's `twa is not None` filter, which drops quiet members.
- Less likely: using `round()` for half-up.

A solver that reads 2.2, 2.4, 3.3 and 1.3 closely gets all of these right. Its self-built reference cannot catch a misreading of F1, because the reference encodes the same reading.

**B) Scores** (5 = strongly resists solving):
- reference_unreachable: **1**. Closed-form arithmetic, and every rule has a sentence.
- authority_incomplete_for_grading: **2**. F1 needs a three-section chain and has a competing README representation. F3 is negligible.
- hidden_state_not_closed_form: **1**.
- restraint_traps: **2**. Two qualifying sites: (i) no-reading versus quiet members in the rebuilt group mean, reached through the definitional chain in 2.2/3.3/1.3; (ii) 0.0 runs excluded from the rebuilt sampled time through the "reading" definition. Ceiling strictness, the absence of flags on groups and the impulse comparison are all written into their rule sentences and score zero.
- fuzz_blind_spot: **2**. Only F1-type misreadings survive self-fuzzing.

**C) Verdict.**
- self_verification_resistance: **2**
- prediction: **collapses**
- confidence: about 0.7
- decisive_reason: every defect is a visible constant or operator mismatch against an explicit manual sentence, and the only real split between solvers is the group-mean treatment of members without a shift dose, which a careful reader resolves from 1.3.
