# Contract review r2: tbrain-hotel-folio-charges (blind)

Scope: this review read only contract-packet-r2 (instruction.md and environment/). Compared with r1, three things changed:
- rule 2.2 now names a rate threshold of 5,000;
- the instruction's city-tax symptom now applies only to rooms of 5,000 cents a night and over;
- `city_tax()` now returns 0 when the rate is below 3000, and nights*200 otherwise.

## Verdict
There is one BLOCKING finding (B1) and one SHOULD-FIX finding (S1). Everything settled in r1 is unchanged: the room charge, the occupancy tax rounding half-up, and the service fee kept at half-even on the new room charge.

## Governed vs silent
- City tax at rates of 5,000 or more: governed. 250 * min(nights, 14).
- City tax at rates below 5,000: amount SILENT. Rule 2.2 only says "Every stay carries a city tax". The kept value is today's step: 0 if rate < 3000, otherwise 200 * nights, with no cap.
- Service fee: SILENT, as in r1. Kept value: round_half_even(room_FC3 * 3.5 / 100).
- Room charge, occupancy tax and totals: governed, as in r1.

## Findings

### B1 BLOCKING: does the 14-night stop reach stays under 5,000?
Rule 2.2 reads "The city tax of a stay at a nightly rate of 5,000 cents or more is 250 cents for each of its nights, up to 14 nights; no city tax is charged for any night after the fourteenth."

The clause after the semicolon is an independent clause with no rate qualifier. The two readings are:
- Reader A: the clause applies to every stay. A rate-4000 stay keeps 200 per night but stops at 14 nights, which caps the kept figure.
- Reader B: the clause belongs to the 5,000+ sentence. The rate-4000 stay keeps 200 * nights uncapped. The instruction's symptom ("on rooms of 5,000 ... never stops") and "Add no exception, clamp or guard" support this reading.

Counterexample: 15 nights at 4000. Reader A gets city tax 2800 and total 63640. Reader B gets city tax 3000 and total 63840. Every stay of 15 or more nights at a rate from 3000 to 4999 diverges; at 60 nights the city tax is 2800 vs 12000.

Minimal fix: put the stop inside the qualified sentence. For example: "...is 250 cents for each of its nights up to the fourteenth, and nothing for any later night." Alternatively, say explicitly that the stop applies to every stay; then state which one the oracle uses.

### S1 SHOULD-FIX: does "Every stay carries a city tax" forbid the kept 0?
Kept today, a rate below 3000 gives a city tax of 0. A reader may treat a zero tax as "not carrying" one. That reader removes the branch and charges 200 * nights.

Counterexample: 1 night at 1100. The kept reading gives city tax 0 and total 1287. The other reading gives 200 and 1487.

The instruction's "keeps working the figure out the way it does today" and "Add no exception, clamp or guard" point to keeping the 0. The r1 service-fee sentence has the same shape and caused no trouble. Still, the new sentence invites a reading that the tax is always positive.

Minimal fix: drop "Every stay carries a city tax." Or reword it to make clear the rules only guarantee the key exists, not that the tax is non-zero.

### Other checks
- The boundaries are unambiguous: 5,000 is inclusive ("or more"), 3000 is inclusive by the code (`<` 3000 gives 0), and the rate limits include 1000–2999, so the zero branch is reachable.
- The kept figure uses stay nights, not paid nights. This follows from today's code and "from the figures the rules do define" (nights and rate). It is unique.
- The occupancy-tax witnesses at 1100 and 1300 now also exercise the zero city-tax branch. Their totals change from r1.
- There are no new gaps in the input limits or the output format.

## Witness stays (verified by script)
| stay | room | occ | city | fee | total |
|---|---|---|---|---|---|
| 1 n @22000 | 22000 | 2970 | 250 | 770 | 25990 |
| 7 n @14500 | 87000 | 11745 | 1750 | 3045 | 103540 |
| 15 n @18900 | 245700 | 33170 (half up) | 3500 | 8600 (8599.5, odd lower cent to even) | 290970 |
| 1 n @1100 (occ half cent; fee half, even lower cent) | 1100 | 149 | 0 | 38 | 1287 |
| 1 n @1300 (fee half, odd lower cent) | 1300 | 176 | 0 | 46 | 1522 |
| 15 n @4000 (B1 witness, reader B) | 52000 | 7020 | 3000 | 1820 | 63840 |
| 1 n @2999 / @3000 / @4999 / @5000 | 2999/3000/4999/5000 | 405/405/675/675 | 0/200/200/250 | 105/105/175/175 | 3509/3710/6049/6100 |

## Silent figures and kept values
- city_tax for rate < 3000: 0
- city_tax for 3000 <= rate < 5000: 200 * nights (all nights, including free ones; uncapped under reader B, see B1)
- service_fee: round_half_even(room_FC3 * 7 / 200)
