# Contract review r1: tbrain-hotel-folio-charges (blind)

Scope: this review read only instruction.md and environment/ (README, rules FC-3, the src/folio code, the driver and the example).

## Verdict
There are no BLOCKING divergences. The instruction's sentences already settle every candidate I found.

## Governed vs silent
- Room charge (2.1): governed. room = rate * (nights - nights//7).
- City tax (2.2): governed. 250 * min(nights, 14).
- Occupancy tax (2.3): governed. The rule is 13.5% of the new room charge, rounded half-up. The shipped `to_cents` uses Python `round(Fraction)`, which rounds half to even, so the rounding has to change for this figure.
- Service fee (2.4): SILENT on the amount and on rounding. It keeps today's value: 3.5% of the room charge, rounded half to even through `to_cents`. The base is the new rule-2.1 room charge ("from the figures the rules do define").
- Totals (2.5): governed. These are plain integer sums.

## Candidate divergences
1. SHOULD-FIX (wording risk, not a divergence): a solver might change `to_cents` globally to half-up. That would also change the service fee.
   - Counterexample: 1 night at 1100. Kept fee 38 vs 39. Total 1537 vs 1538.
   - The instruction settles this ("keeps working the figure out the way it does today"), so it is not a divergence. A reader could still see "Every folio carries a service fee" and assume the rules round it like 2.3.
   - Minimal fix: none required. Optionally, the README could name the service fee as a figure the package works out.
2. SHOULD-FIX (wording risk): a solver might compute the service fee on the old base (nights*rate).
   - Counterexample: 7 nights at 14500. Fee on the new base is 3045; on the old base it is 3552.5, which rounds to 3552.
   - The instruction's "from the figures the rules do define" settles this. No fix needed.
3. POLISH: rule 1.1 says "exact, unrounded amounts". A reader might wonder whether the occupancy tax is rounded per folio or on the file total. Rule 2.3 says "a stay's", which settles it.
4. Input limits: fully specified (count 1-200, unique ids, id charset, nights 1-60, rate 1000-150000). Out-of-limit inputs are declared open. No gap.
5. Output format: fixed by the unmodifiable driver (`json.dump` defaults) and by the README key list. Integers stay integers because `to_cents` returns an int. No gap.
6. Kept values: each silent figure is uniquely derivable from the code. Only the service fee is silent, and there is only one way to derive it.

## Witness stays (verified by script)
| stay | room | occ tax | city | fee | total |
|---|---|---|---|---|---|
| 1 n @22000 | 22000 | 2970 | 250 | 770 | 25990 |
| 7 n @14500 | 87000 | 11745 | 1750 | 3045 | 103540 |
| 15 n @18900 | 245700 | 33170 (33169.5 up) | 3500 | 8600 (8599.5, half-even; odd lower cent) | 290970 |
| 1 n @1100 (occ half cent) | 1100 | 149 (148.5 up) | 250 | 38 (38.5, even lower cent stays) | 1537 |
| 1 n @1300 (fee half, odd lower cent) | 1300 | 176 (175.5 up) | 250 | 46 (45.5 to even 46) | 1772 |
| 14 n @1000 (extra) | 12000 | 1620 | 3500 | 420 | 17540 |

A half cent occurs for both the occupancy tax and the service fee exactly when room ≡ 100 (mod 200). So a half-cent occupancy tax always comes with a half-cent service fee, and a verifier can tell the two rounding modes apart only when the fee's lower cent is even (for example room 1100).

## Silent figures and kept values
- service_fee = round_half_even(room_charge_FC3 * 3.5 / 100)
