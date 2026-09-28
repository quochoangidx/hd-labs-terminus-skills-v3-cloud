# Contract review r2: tbrain-cems-hourly-emission-averaging

Reviewer A. I read only packet r2 (instruction.md + environment/) and diffed it against packet r1.

What changed between r1 and r2:
- DRP-4 1.4 now says "A CAL record always has a load of 1 MW or more, and an hour holding a CAL record holds no MNT or OOC record."
- DRP-4 has a new 2.7 defining the "firing ratio" of a *firing hour*.
- 3.2 now uses that firing ratio.
- The sample job was regenerated and now has no CAL records.
- instruction.md, README, driver and src are unchanged.

## Status of r1 findings

1. **Non-firing valid hour concentration: mostly closed, now polish.**
   - The 209 figure now lives only inside the defined term "firing ratio", which exists only for firing hours.
   - So a non-firing valid hour has no procedure-determined ratio or 209 input. The instruction's "package's own constants left at today's values" then clearly keeps `corrected()` with 210 and the cap at 190. Witness W5 = 900 is now grounded rather than guessed.
   - Residual risk: a solver might still read "209" as a physical constant the procedure "determines", but the text no longer supports that.
2. **CAL-hour validity: closed.**
   - A CAL quarter is always an operating quarter, so reading (a) is gone.
   - A CAL hour never holds MNT/OOC, so reading (b) is gone.
   - The rest of a CAL hour's quarters are OK or non-operating. So "two valid readings or more" is the only condition, and the averages come from the OK operating quarters.
   - Jobs that break the new sentence fall outside the section 1 limits, which the instruction leaves open.
3. **Non-lost substitute carry-forward: unchanged and still fair.** It is governed by the defined term "lost hour" and remains the task's main restraint point.
4–6. **Polish items:** unchanged and still fine.

## New findings

N1. **polish: the instruction and the new 1.4 sentence disagree slightly.**
- The instruction says jobs include "maintenance and out-of-control codes in any quarter, whether or not the unit was running".
- 1.4 now forbids MNT or OOC in any hour holding a CAL record.
- Read literally, "any quarter" includes the quarters of a CAL hour.
- The section 1 limits win, since the instruction scopes everything to "inside the limits of its section 1", so no output changes. Suggest adding "outside calibration hours" to the instruction, or leaving it as is.

N2. **polish: the example no longer shows a CAL hour.**
- The sample job has zero CAL records.
- A solver fuzzing against its own reference gets no worked CAL case, but the instruction lists calibration hours as in scope. This is not a defect, because the authority governs CAL completely.

N3. **polish: the 1.4 constraint is not needed for fairness in one direction.**
- A CAL hour with 1 valid reading plus the CAL quarter is a substitute hour. It is not lost, so it takes today's carry-forward.
- This is governed consistently: 2.3 fails, 2.5 fails, so the silence clause applies.
- This is a second restraint site in the same rebuilt `fill`. Worth knowing, not a defect.

No blocking or should-fix findings remain.

## Witnesses (r1 set still holds; W4 and W5 no longer guessed)

- W1 1000/119, tons 0.
- W2 2090/1194, tons 6.
- W3: the same hour with 2 operating quarters gives tons 3.
- W4: [op CAL, op OK(1000,30,4e6), op OK(1200,50,6e6), op OK(1100,40,5e6)] gives a valid hour.
  - The averages come from the three OK quarters: 1100/40/5e6.
  - nox = 196900/169 = **1165**, lb **657**.
- W5: non-firing 100/195/1e6, ref 30 gives nox **900**, lb 12.
- W6: carry-forward (1000,119); lost hour (1500,179).
- W7: tie gives (1001,101).
- W8: rolling at the limit 1000 gives exceed false.
- W9: rolling weighted by hour gives 1000.
- W10 (new): CAL hour [op CAL, op OK(1000,30,1e6), non-op OK, non-op OK], ref 30.
  - It has only 1 valid reading, so it is not valid. It is not lost either, so it is a substitute hour.
  - It takes the previous valid hour's figures, or (0,0) if there is none.
  - Operating quarters = 2, which affects mass.

## Part 2: Solver-path screen (redone)

A) Pre-mortem. The solver rewrites the same five places as in r1. The CAL rule is now mechanical.
- The r1 ambiguity that could make the task resist for defect reasons is gone. What resists now is restraint:
  - (i) interpolating non-lost substitute hours (including the W10-type 1-valid CAL hour) inside the rebuilt `fill`;
  - (ii) replacing 210 with 209, or dropping the cap, for non-firing valid hours inside the rebuilt `corrected`.
- The new 2.7 wording makes (ii) *easier* to catch: "firing ratio of a firing hour" invites the question "and a non-firing hour?".
- A careful solver that lists the silent cases catches both. A less careful one misses (i), because (i) is the obvious "fix" of the complaint "hours the monitor lost are filled with whatever the last good hour said". It over-applies interpolation.
- Self-written references share the same blind spots.

B) Scores
- reference_unreachable: **2**.
- authority_incomplete_for_grading: **1**. Only polish remains.
- hidden_state_not_closed_form: **1**.
- restraint_traps: **3**.
  - The carry-forward and the non-firing constants/cap sit in the rebuilt aggregates.
  - The 1-valid CAL case adds weight to the carry-forward trap but is the same site.
  - The non-firing trap is now signposted by a defined term, so it is slightly weaker.
- fuzz_blind_spot: **2**.

C) self_verification_resistance: **3**. Prediction: **collapses, marginally**. Confidence: low (~50–55% collapse). Decisive reason: the contract is now clean and both traps are reachable by reading the silence paragraph against the defined terms "lost hour" and "firing ratio", so two Opus 5-class solvers that enumerate silent cases would both likely pass. Resistance now depends only on whether a solver over-applies the lost-hour interpolation.
