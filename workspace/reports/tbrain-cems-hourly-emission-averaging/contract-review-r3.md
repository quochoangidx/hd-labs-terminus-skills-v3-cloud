# Contract review r3: tbrain-cems-hourly-emission-averaging

Reviewer A. I read only packet r3 (instruction.md + environment/) and diffed it against r2.

What changed between r2 and r3:
- instruction.md now says "in any quarter outside calibration hours", which closes r2 N1.
- `correction.py`: O2_CAP moved from 190 to 200, with an explicit branch: `o2 < 200` uses (210-ref)/(210-o2), otherwise (210-ref)/10.
- `substitute.py`: `last` is now updated from *every* operating hour, valid or not. A non-valid hour takes the previous operating hour's reported figures, or (0,0) if there is none.
- The procedure, README and driver are unchanged. The sample job was regenerated and still has no CAL records.

## Status of earlier findings
- r1-1 / non-firing constants: closed. Uniqueness is checked below.
- r1-2 CAL: closed (since r2).
- r1-3 non-lost substitute: still the restraint point. Its semantics changed (see U2).
- r2 N1: closed.
- r2 N2: open, polish. The sample job still has no CAL hour.
- r2 N3: holds.

## Uniqueness of the cases the procedure leaves unsettled

U1. **Non-firing valid hour** (oxygen average ≥ 190, not covered by 3.2/2.7). The unique value is today's `corrected(noxavg, o2avg, ref)`:
- The procedure determines the inputs noxavg, o2avg (3.1, valid readings only) and ref.
- The constants 210 and 200 are the package's own, and nothing else is procedure-determined.
- One value. The branch on `o2 < 200` is applied to the exact Fraction average, so there is no rounding ambiguity.

Witnesses, ref 30, nox average 100 (10.0 ppm), all four operating quarters OK:

| o2 avg | branch | value | nox |
|---|---|---|---|
| 190 | 180/20 | 900 | **900** |
| 192 | 180/18 | 1000 | **1000** |
| 195 | 180/15 | 1200 | **1200** |
| 199.5 (e.g. 199,200,199,200) | 180/10.5 | 1714.29 | **1714** |
| 199.75 (199,200,200,200) | 180/10.25 | 1756.10 | **1756** |
| 200 | cap, 180/10 | 1800 | **1800** |
| 205 | cap, 180/10 | 1800 | **1800** |

Control, firing just below the line: o2 avg 189.75 (189,190,190,190). This is a firing hour under 2.4, so 209 applies: 100*179/19.25 = **930** (929.87). The old formula would give 180/20.25, i.e. 889.

A solver that reads "the package's constants" as covering only 210 and drops the cap has no support for that in the text. The cap is plainly a package constant. **Unique.**

U2. **Substitute hour that is not lost.** Today's calculation takes the reported figures of the *previous operating hour*, whatever its kind. The previous hour's reported figures are procedure-determined when that hour is valid or lost, so they take the procedure's values. That gives one value.

Witness, ref 30, all quarters operating:
- H1 is valid with (1000, 119).
- H2 is all MNT, so it is lost.
- H3 is [OK, OK, MNT, OOC], a substitute hour that is not lost.
- H4 is valid with (2000, 239).

Result:
- H2 = ((1000+2000)/2, (119+239)/2) = **(1500, 179)**.
- H3 = H2's reported figures = **(1500, 179)**.
- A competing reading would give (1000, 119), either via "last *valid* hour" (the r2 semantics, or a solver reusing 4.2's wording) or via "today's un-fixed lost value carried". Neither follows the instruction's "inputs … the procedure determines take the procedure's values". So the value is unique, but this is now a sharper trap.

More cases:
- **Chain** H1 valid, H2 lost, H3 substitute, H4 substitute, H5 valid: H3 and H4 both take H2's figures, H2 being the interpolated lost hour.
- **At the start of the export:** H1 is a substitute hour that is not lost, H2 is valid (1000, 119).
  - H1 = **(0, 0)**, because no operating hour precedes it.
  - Note the asymmetry: a *lost* H1 would instead take (1000, 119) under 4.3.
  - One value, and nothing else gives a value there.
- **Lost hour at the start** (4.3 one-sided), then a substitute: H1 lost, H2 [OK, MNT], H3 valid (1000, 119). H1 = (1000, 119), then H2 = (1000, 119).
- **Across shut-down hours or days:** non-operating hours are skipped, so `last` carries across them. That is one value.

Result: every case the procedure leaves unsettled that I could enumerate has exactly one value implied by today's code, with inputs the procedure determines:
- a non-firing concentration;
- a substitute hour that is not lost, including a CAL hour with fewer than 2 valid readings;
- a substitute hour at the start of the export.

The mass rate of a non-firing hour is governed (3.3). Its rolling contribution is governed (6.1, via its reported concentration).

## New findings
- **N4, polish:** the value of a substitute hour that is not lost now depends on the reported figures of an interpolated lost hour, which requires lookahead. A solver must compute lost hours before the hours that follow them. That is natural if lost hours are filled in a second pass, but a single-pass rewrite gets it wrong. This is fair and unique, and it is a legitimate restraint site inside the rebuilt `fill`.
- **N5, polish:** the asymmetry at the start of the export ((0,0) for a substitute hour that is not lost, but the first valid hour's figures for a lost one) is correct under the contract but counter-intuitive. Graders should include it deliberately, not by accident.
- No blocking or should-fix findings.

## Other witnesses (from r2, still valid)
- W1: 1000/119, tons 0.
- W2: 2090/1194, tons 6.
- W3: 2 operating quarters, tons 3.
- W4: CAL hour with three OK readings gives 1165/657.
- W7: tie gives (1001, 101).
- W8: rolling exactly at the limit gives exceed false.
- W9: rolling weighted by hour gives 1000.
- W10: a CAL hour with 1 valid reading is a substitute. It now takes the previous *operating* hour's figures, not the previous valid hour's.

## Part 2: Solver-path screen (redone)

A) Pre-mortem. The solver rewrites validity, averages, the firing ratio, the mass rate on the measured average, mass × operating time, lost-hour interpolation, and the rolling average (operating-day window, weighted by hour, strictly above). The r3 package makes both traps sharper:
- (i) `corrected` now has an explicit two-branch structure with 210 in both. The natural fix is to replace it with the 209 firing ratio and delete the branches. That breaks every non-firing hour, a class the section 1 oxygen range of 0–205 reaches often.
- (ii) `fill` now chains through substitute hours. A solver must keep the chaining, feed it the *interpolated* lost values, and handle the lookahead. The likely failures are:
  - "carry the last valid hour" (the reading of 4.2);
  - interpolating every substitute hour;
  - a single pass that carries the pre-interpolation value.

Careful enumeration of the silent cases solves both. Self-written references mirror the solver's reading, and fuzzing catches nothing without an independent oracle.

B) Scores
- reference_unreachable: **2**.
- authority_incomplete_for_grading: **1**. The silent cases are unique, as shown above.
- hidden_state_not_closed_form: **1**.
- restraint_traps: **4**.
  - Two sites inside rebuilt aggregates: the non-firing branches in `corrected`, and the chaining through lost hours in `fill` plus the start-of-export (0,0).
  - Each has strong contrary instinct but passes the 0/8 screen: the authority's defined terms draw the line, and there is no competing positive rule.
- fuzz_blind_spot: **2**.

C) self_verification_resistance: **3–4**. Prediction: **resists**, confidence medium-low (~60%). Decisive reason: both natural rewrites (a single correction formula, a "fill from valid neighbours" pass) silently break cases the procedure leaves unsettled but today's code fixes uniquely, and the solver's own reference inherits the same reading.
