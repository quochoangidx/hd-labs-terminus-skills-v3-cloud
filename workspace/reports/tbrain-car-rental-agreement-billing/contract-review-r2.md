# Contract review r2 — tbrain-car-rental-agreement-billing

Diff vs r1: the instruction and code are unchanged. The manual changes are: 2.3 is reworded ("is charged for"), the old 2.4 (allowance days) is deleted, 2.5 and 2.6 are renumbered to 2.4 and 2.5, 3.1 now reads "day rate for each day it is charged for", and 3.2 now reads "150 miles for each day it is charged for".

## Status of r1 findings
1. **Sub-day allowance: CLOSED (with one residual, see N1).** 3.2 now ties the allowance to the days the rental is charged for, which is the same figure the time charge uses. For a sub-day rental that figure is silent, so the kept value is today's `days()` = ceil(len/1440) = 1, and the allowance is 150. RA-10442 → days 1, miles 80, time 3900, mileage 0, fuel 0, tax 322 (3900×0.0825=321.75), total 4222. The alternatives from r1 (allowance 0, or allowance 100) no longer have a sentence behind them: 3.2 governs every rental and fixes 150 per day.
2. **Negative fuel charge when fuel_in ≥ fuel_out: OPEN (unchanged, should-fix).** 3.3 still covers only refuelling rentals. Kept value: (out−in)×rate, which gives a credit and no fee. Example: fuel 2→6 at 700 gives −2800. This is derivable, but it runs against a strong instinct to clamp at 0.
3. **Sub-day days/time charge rest on the silence clause: CLOSED as a finding.** It is now the single silent figure, and the other rules hang off it consistently.
4–6 (polish): unchanged, still fine.

## New findings
- **N1 SHOULD-FIX: a "nought" reading of 2.3 for sub-day rentals.** 2.3 positively says what "A day rental is charged for". A reader can take this as the full definition of the days a rental is charged for, so a rental that is not a day rental is charged for no days. That gives time 0 and allowance 0. RA-10442 under this reading: days 0, time 0, mileage 2000, tax 165 (2000×0.0825=165.0), total 2165. The intended value is 4222. The absurdity (a free rental) and the instruction's silence sentence make the intended reading clearly more likely, but the manual never says the days of a non-day rental are left open. A single phrase would close this, e.g. in 2.2/2.3: "This manual does not say how many days a rental shorter than that is charged for."
- **N2 POLISH: renumbering.** The manual still claims "Rule numbers do not move between editions", but 2.5 and 2.6 moved to 2.4 and 2.5. The instruction cites only 1.3, so this is harmless. Either restore the numbering or drop the claim.
- I found no other sentence that now reads two ways. "each day it is charged for" is the same phrase in 3.1 and 3.2, so the time charge and the allowance cannot diverge.

## Figures left to today's code by the silence sentence
| Figure | Kept value | Uniquely derivable? | Witness | Could a sentence be read as governing it? |
|---|---|---|---|---|
| Days charged, sub-day rental (1–1439 min) | ceil(len/1440)=1 | Yes | 1-min rental, 100/500/2000, 0 mi, fuel 3→3 → days 1, time 100, mileage 0, fuel 0, tax 8, total 108 | Yes, weakly: the N1 nought reading gives days 0, total 0 |
| Fuel charge, fuel_in = fuel_out | 0 | Yes | RA-10442 fuel 5→5 → 0 | No. A reading of "no fuel charge" also gives 0, so the readings agree |
| Fuel charge, fuel_in > fuel_out | (out−in)×rate < 0, no fee | Yes | 2032-02-28T10:00→03-01T11:00, odo 999900→300, fuel 2→6, 5000/20/700 → 3, 400, 15000, 0, −2800, 1238, 13438 | Yes: a reader can take the absence of a 3.3 charge as "fuel charge is nought" (the non-refuelling rental has no fuel charge, so 4.2 adds 0). That gives total 16238. **This is the strongest remaining two-reading site.** |

Note on the last row: "Where the manual gives no rule ... keeps working the figure out the way it does today" versus "the rental has no fuel charge, so it is nought" is exactly the kind of nought reading that splits competent readers. Today's code computes the figure for every rental, which favours the negative value, but nothing in the manual names it. I would state in 3.3 or the instruction which applies, or accept it as a deliberate trap knowing that it fails the 0/8 screen.

## Witnesses (unchanged from r1 unless noted)
RA-10441 → 3, 435, 14700, 0, 2800, 1213, 18713. RA-10442 → 1, 80, 3900, 0, 0, 322, 4222 (now determined). 2031-12-31T23:30→2032-01-07T00:29, 0→1100, 8→0, 100000/0/0 → 6, 1100, 600000, 0, 1500, 49500, 651000. 1d59m, fuel 1→0, 121/0/0 → 1, 0, 121, 0, 1500, 10, 1631. Taxable 200 → tax 17.

## Departures of the shipped package from the manual (unchanged)
- Days are charged for every day begun, with no 59-minute grace (2.3).
- 100 miles a day instead of 150 (3.2).
- No odometer turnover (now 2.4).
- No 1,500-cent refuelling fee (3.3).
- Tax includes fuel and is floored instead of rounded half-up (4.1, 1.2).

## Part 2 — solver-path screen
A) The solver fixes the five departures. For sub-day rentals it now naturally keeps `days()` in both the time charge and the allowance (`150*days`), which matches the intended value, so the r1 trap is gone. The only remaining divergence is fuel for fuel_in > fuel_out. A solver that restructures to `if fuel_in < fuel_out: (…)+1500 else 0` fails. A solver that writes `(out-in)*rate + (1500 if short else 0)` passes. Its own reference shares whichever reading it chose, so self-tests cannot catch it.
B) reference_unreachable 2; authority_incomplete_for_grading 3 (the sub-day case is fixed, but N1 and the fuel nought reading remain); hidden_state_not_closed_form 1; restraint_traps 2 (fuel is the only site and it is borderline under 0/8; sub-day is no longer a trap); fuzz_blind_spot 2.
C) self_verification_resistance 2. Prediction: collapses. Confidence: medium-high. decisive_reason: the r2 rewording removed the sub-day trap, and every departure is listed in the instruction. What resistance remains comes from the fuel-credit reading, which is a contract ambiguity rather than legitimate difficulty.
