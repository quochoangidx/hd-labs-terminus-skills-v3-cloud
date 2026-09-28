# Contract review r3: tbrain-hotel-folio-charges (blind)

Scope: this review read only contract-packet-r3. The only change from r2 is rule 2.2, which now reads: "The city tax of a stay at a nightly rate of 5,000 cents or more is 250 cents for each of its first 14 nights and nothing for any later night." The instruction, the code, the README and the driver are identical to r2.

## Verdict
There are no BLOCKING findings. B1 and S1 from r2 are resolved.
- B1 (does the 14-night stop apply below 5,000?) is resolved. The stop now sits inside the sentence qualified by the 5,000-cent threshold, so it cannot reach cheaper rooms.
- S1 ("Every stay carries a city tax" vs the kept 0) is resolved, because the sentence is gone. The `city_tax` key is still required for every folio by the README.

## Governed vs silent
- Room charge (2.1): rate * (nights - nights//7).
- City tax at rates of 5,000 or more (2.2): 250 * min(nights, 14). "Each of its first 14 nights" counts calendar nights, including the free 7th and 14th, so it is not tied to the paid nights of 2.1.
- Occupancy tax (2.3): round_half_up(room * 27 / 200).
- Totals (2.5): integer sums.
- SILENT: the city tax below 5,000 and the service fee (kept values below).

## Remaining notes
- POLISH (no divergence): a reader might wonder whether the city tax is also free on the free nights of 2.1. Rule 2.2 says "each of its first 14 nights", and 2.1 frees only the room charge, so no competent reader diverges. No fix needed.
- r1 SHOULD-FIX items (global half-up rounding, and the service fee on the old base) are still settled by the instruction's sentences.
- The boundaries are unambiguous: 5,000 is inclusive by the rules, and 3,000 is inclusive by the code. There are no gaps in the input limits or the output format.

## Witness stays (verified by script; same as r2)
| stay | room | occ | city | fee | total |
|---|---|---|---|---|---|
| 1 n @22000 | 22000 | 2970 | 250 | 770 | 25990 |
| 7 n @14500 | 87000 | 11745 | 1750 | 3045 | 103540 |
| 15 n @18900 | 245700 | 33170 (33169.5 up) | 3500 | 8600 (8599.5, odd lower cent to even) | 290970 |
| 1 n @1100 (occ half cent; fee half, even lower cent) | 1100 | 149 | 0 | 38 | 1287 |
| 1 n @1300 (fee half, odd lower cent) | 1300 | 176 | 0 | 46 | 1522 |
| 15 n @4000 (kept, uncapped) | 52000 | 7020 | 3000 | 1820 | 63840 |
| 1 n @2999 / @3000 / @4999 / @5000 | 2999/3000/4999/5000 | 405/405/675/675 | 0/200/200/250 | 105/105/175/175 | 3509/3710/6049/6100 |

## Silent figures and kept values
- city_tax, rate < 3000: 0
- city_tax, 3000 <= rate < 5000: 200 * nights (all nights, uncapped)
- service_fee: round_half_even(room_FC3 * 7 / 200)
