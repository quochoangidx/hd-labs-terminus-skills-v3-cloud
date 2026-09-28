# Contract review r2: tbrain-occupational-noise-dose-survey

Scope: I read only the r2 `instruction.md` and `environment/`: the Dockerfile, README, manual HC-4, `src/noisedose/*` (now `runs.py` and `shift.py` in place of `exposure.py`), the driver and the example. I re-read everything fresh.

## What changed from r1 (as seen from the packet)

- **Manual 2.5 is new.** It adds the full-shift survey: sampled time is at least three quarters of the shift.
- **Manual 3.3 now covers only full-shift surveys.** The "survey without a reading has no shift dose" sentence is gone.
- **Manual 1.3 lost** "the mean of no figures is nought".
- **Manual 4.1 lost** "a worker with no shift dose has no TWA".
- **The README** no longer prints a no-shift-dose worker as 0.0; `dose` is simply the shift dose.
- **The instruction** now states the preservation rule explicitly: "A rule the manual states for some inputs gives no rule for the others". It names the case: "a survey that sampled too little of its shift for the manual's rules on the shift dose to cover it, down to one whose dosimeter measured nothing at all".

Net effect: r1's F1 (whether members without a shift dose count in the group mean) is gone. Every worker now has a shift dose. A non-full-shift worker's shift dose comes from the kept legacy step in `shift.py`, so every member enters the group mean. The design centre has moved to the non-full-shift branch.

## Implied reference, as I read it

| Figure | Rule |
|---|---|
| Reading / counted reading | Level >= 40.0 / level >= 80.0 (2.2, 2.3) |
| Sampled time | Minutes of all readings, excluding 0.0 runs (2.4) |
| Measured dose | 100 × Σ m · 2^((L−85)/3) / 480 over counted readings (3.1, 3.2) |
| Full-shift, sampled < shift | Measured × shift / sampled (3.3) |
| Full-shift, sampled >= shift | Measured (3.3) |
| Non-full-shift (4·sampled < 3·shift) | Ungoverned, so today's `shift.py` step stands: sampled 0 → 0.0; sampled < 480 → measured × 480 / sampled; else measured. Sampled time and measured dose inside it follow the manual. |
| TWA | 85 + 3 log2(D/100), rounded half up to a tenth; D = 0 → null (4.1, 1.2) |
| Status | Over on ceiling, impulse, or TWA > 85.0; action for 82.0 to 85.0; else below (5.3) |
| Flags | Ceiling: reading > 115.0. Impulse: peak >= 140.0. |
| Group | Mean of all members' shift doses; TWA by 4.1; bands only (6.1) |

## Part 1: Contract findings

**F1 (should-fix): which sampled time goes into the kept legacy step.**
Citations:
- Instruction: "the step the package takes for that figure today stands ... every other step the figure passes through still follows the manual".
- Code today: `measure()` counts only runs `> 80.0` toward `sampled`.
- Manual 2.4: sampled time counts all readings.

Two readings are possible:
- (A) The legacy step divides by the manual's sampled time, because sampled time is a manual-governed figure the step passes through.
- (B) The legacy step divides by today's counted-only minutes, reading the whole step as it is today.

Counterexample: shift 480, log `[[120, 88.0], [120, 70.0]]`. Sampled time is 240, which is below 360, so the survey is non-full.
- (A): 50 × 480/240 = 100 → TWA 85.0, "action".
- (B): 50 × 480/120 = 200 → TWA 88.0, "over".

The instruction's "every other step ... follows the manual" favours (A), and a solver who fixes `measure()` once lands on (A) naturally. But (B) is a defensible literal reading of "keeping that step comes first". The fix is one clause, e.g. "... with the sampled time and measured dose the manual defines".

**F2 (should-fix / trap check): the kept step keeps 480 as both the comparison and the target.**
Citations: 3.3 "A full-shift survey whose sampled time is shorter ..."; 2.5 "at least three quarters of the worker's shift"; code `if sampled < EIGHT_HOURS: return measured * EIGHT_HOURS / sampled`.
The natural fix is to project every survey to `shift_minutes`, and it must stop at the 2.5 boundary.
- Counterexample 1: shift 720, log `[[500, 85.0]]`. Sampled is 500, below 540, so non-full; 500 >= 480, so the kept step returns measured. Correct: 104.1667 → 85.2, "over". Naive: 150 → 86.8.
- Counterexample 2: shift 90, `[[67, 85.0]]`. Non-full, projected to 480, giving 100 → 85.0, "action". Naive: 18.75 → 77.8, "below".

This is governed through a definitional chain (2.5 → 3.3 scope) and is signposted in the instruction, so it counts as a legitimate trap. It produces a deliberate discontinuity at the three-quarter boundary. At shift 90, 67 sampled minutes give 85.0 and 68 give 77.8. That is odd but correct by the contract.

**F3 (polish): the goal narrative pulls against F2.**
Citation: "people on ten- and twelve-hour shifts come out lower than their logs support".
In the example, P-0117 has a 600-minute shift with 410 sampled minutes (below 450), so it is non-full and stays projected to 480, not 600. A solver who uses the complaint as a spec would project it to 600. The symptom is still true for full-shift long-shift workers, e.g. 500 of 600 minutes, which today go unprojected. So the complaint is not wrong, only broader than the fix. Optionally narrow it to "...on long shifts whose dosimeter ran most of the day".

**F4 (polish): half-up rounding on floats.**
Same as r1. Python `round()` differs from half-up only at binary-exact halves (84.25, 84.75), which are reachable only by float coincidence. Confirm the generator stays at least 1e-9 away from .x5 boundaries.

**F5 (polish, zero-count trap): ceiling vs impulse comparison.**
The strict `> 115.0` ceiling and `>= 140.0` impulse are both written into their rule sentences.

**Checks passed.**
- Every 1.4 range has a floor and a ceiling.
- The three-quarter test is exact in integers (4·s >= 3·shift), and "exactly three quarters" is full-shift.
- The open list matches 1.4, and nothing in the manual governs it.
- Every ordering, rounding and format rule has an authority sentence.
- Groups: every member now has a shift dose, so the r1 ambiguity is closed.
- Nothing in the manual positively governs the non-full-shift shift dose: 3.3 now opens with "A full-shift survey", and no other rule names shift dose for other surveys.

## Hand witnesses

Single worker unless stated; results under reading (A).

| # | Input (shift; log; peaks) | Output (dose; twa; status) | Guess? |
|---|---|---|---|
| W1 | 480; `[[360, 85.0]]` (exactly 3/4, full) | 75 × 480/360 = 100; 85.0; action | no |
| W2 | 480; `[[359, 85.0]]` (non-full, legacy) | 74.79 × 480/359 = 100; 85.0; action | no |
| W3 | 600; `[[300, 88.0]]` (non-full) | 200 (projected to 480, not 600); 88.0; over | no |
| W4 | 720; `[[500, 85.0]]` (non-full, >= 480) | 104.166667 (unprojected); 85.2; over | no |
| W5 | 480; `[[120, 88.0], [120, 70.0]]` | 100; 85.0; action | **yes (F1; B gives 200 / 88.0 / over)** |
| W6 | 480; `[[240, 0.0], [240, 88.0]]` | 200 (sampled 240, legacy); 88.0; over | no |
| W7 | 90; `[[67, 85.0]]` → 100; 85.0; action. 90; `[[68, 85.0]]` → 18.75; 77.8; below | | no |
| W8 | 480; `[]`; peaks `[140.0]` | 0.0; null; over; impulse T; ceiling F | no |
| W9 | 480; `[[480, 80.0]]` → 31.498026; 80.0; below. `[[480, 82.0]]` → 50; 82.0; action | | no |
| W10 | `examples/press-shop-day.json` | P-0117 286.936916 / 89.6 / over (non-full 410/600 → legacy to 480); P-0122 234.718144 / 88.7; P-0130 370.172922 / 90.7; T-0041 46.102988 / 81.6 / over (impulse); T-0048 0.0 / null / below. PRESS 297.275994 → 89.7 over; TOOL2 23.051494 → 78.6 below | no |

## Part 2: Solver-path screen

**A) Pre-mortem.**
A strong solver diffs the five modules against HC-4. It fixes the constants (85/3, >= 80), the half-up rounding, the bands, `>= 140` for impulse, and sampled time over all readings. It rebuilds `groups.py` to average unrounded shift doses. It rebuilds `shift.py` around 2.5: a full-shift survey projects to the shift, otherwise the old `sampled == 0` / `< 480` / `× 480` branch is kept, because the instruction names that case almost verbatim. It then writes a reference from the manual plus its reading of the kept branch and fuzzes it. The fuzzing agrees with the patch by construction. The places it can go wrong:
- (i) Keeping the old counted-only `sampled` inside the legacy branch (F1, reading B).
- (ii) Following the "ten- and twelve-hour shifts" complaint and projecting non-full long shifts to the shift (F2/F3).
- (iii) Replacing `EIGHT_HOURS` in the legacy comparison with the shift.

Its own fuzzing cannot catch any of these, because its reference shares its reading. The explicit instruction sentence makes (ii) and (iii) unlikely for a careful solver. (i) is the real split.

**B) Scores** (5 = strongly resists solving):
- reference_unreachable: **2**. Closed form, but the reference must reproduce legacy semantics that sit only in code and are protected by the preservation clause.
- authority_incomplete_for_grading: **2**. F1 is a one-clause gap with a favoured reading.
- hidden_state_not_closed_form: **1**.
- restraint_traps: **3**. Three qualifying sites, all inside the rebuilt shift-dose/sampled-time aggregate: (a) the legacy 480 comparison and target kept for non-full surveys, via the 2.5 definition; (b) the legacy sampled-0 → 0.0 and sampled >= 480 → unprojected branches for non-full surveys; (c) 0.0 runs excluded from sampled time via the "reading" definition. Ceiling strictness, impulse, and the lack of flags on groups are written into their rules and score zero. None of these fails the 0/8 screen: the instruction explicitly names the non-full case, and no competing authority sentence exists. The narrative pull (F3) is from the requester, not the authority.
- fuzz_blind_spot: **3**. Every trap is a reading choice that self-fuzzing reproduces rather than detects.

**C) Verdict.**
- self_verification_resistance: **2.5**, rounded to **3**. Self-checks cannot validate the legacy-branch reading, but the instruction all but dictates it.
- prediction: **collapses** (weakly)
- confidence: about 0.6
- decisive_reason: the one real trap (keep the legacy shift-dose step below three quarters of the shift) is named almost verbatim in the instruction, so both strong solvers likely implement it. The main residual split is F1 (which sampled time the kept step divides by), and that should be closed in the text, not counted as difficulty.
