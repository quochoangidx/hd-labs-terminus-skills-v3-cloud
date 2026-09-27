# Contract review r1 — tbrain-parcel-dim-weight-billing (blind)

Scope: only contract-packet-r1/instruction.md and environment/.

## Findings

### F1 SHOULD-FIX (near-blocking): express + residential surcharge
Rule 3.2 only says a GROUND home parcel carries 530. It does not say that express home parcels carry none. The shipped code charges 450 to every residential parcel.
- Reader A (silence, so keep today's value): EXPRESS, residential → 450.
- Reader B (3.2 read as exhaustive, "only ground home parcels carry one"): → 0.
Counterexample: sides [10,10,10], weight 50, EXPRESS, zone 2, residential true. Billable ceil(1000/139=7.19)=8, T=760.
A: R=450, F=round_half_up(1210*0.1425=172.425)=172, total 1382. B: R=0, F=108.3→108, total 868.
The instruction's "ground deliveries to homes are short" leans toward A, but that is only a hint.
Fix: add a sentence to the instruction (not the rules) such as "the rules set no residential surcharge for an express parcel". Or have 3.2 say explicitly that ground only is covered.

### F2 SHOULD-FIX: dimensional divisor for a non-box
Rule 2.2 defines dimensional weight for every parcel through "its dimensional divisor" but gives only the box's (139). Reading the instruction's "keeps working it out the way it does today" gives 166 for a non-box. A reader could instead decide that a non-box has no dimensional weight, so billable = ceil(actual).
Counterexample: sides [1,108,108], weight 10, GROUND, zone 2, non-res. A: 11664/166=70.27 → 71, T=6745, F=961.16→961, total 7706. B: billable 1, T=95, F=13.54→14, total 109.
Fix: make it clearer that 2.2 applies to every parcel and only the non-box divisor is silent. For example: "2.2 ... Every parcel has a dimensional weight; the dimensional divisor of a box is 139."

### F3 POLISH: parsing the fuel base
"14.25 per cent of its transport charge plus its residential surcharge" could be read as 0.1425*T + R. The instruction line "leaves out part of what it should be taken on" settles it as 0.1425*(T+R). Adding "of the sum of" in 3.3 would make that explicit.

### F4 POLISH: whole-pound dim weight for a box cannot occur
139 is prime and greater than 108, so a box volume is never a multiple of 139. The instruction's "dimensional weights land exactly on a whole pound" can only be hit by non-boxes (divisor 166, e.g. [1,2,83]) or by actual weights. This does not cause divergence. It only matters to the test author.

No other divergences found:
- Box threshold (>= 2, inclusive) is clear.
- Ceil on the exact Fraction is clear, and 1.2 says unrounded.
- Half-up on integer cents is exact: (x*1425+5000)//10000.
- Output types are ints (math.ceil and int arithmetic).
- Order is preserved.
- Zone rates are unchanged.
- Rule 1.3 domain has no gaps (weight >= 1, so billable >= 1).

## Silent figures and kept values
| Figure | Kept value |
|---|---|
| Non-box dimensional divisor | 166 (dim = volume/166, exact) |
| Residential surcharge, EXPRESS home | 450 |
| Residential surcharge, non-home | 0 (not really silent: 3.2 gives none) |

Governed and changed: box divisor 139; ceil billable; ground home 530; fuel base T+R; fuel rounding half-up.

## Witnesses (fixed contract, A readings)
| # | Covers | Input | billable | T | R | F | total |
|---|---|---|---|---|---|---|---|
| 1 | box, ground residential | [18,12,10], 84, GROUND, z5, res | 2160/139=15.54→16 | 2096 | 530 | 2626*.1425=374.205→374 | 3000 |
| 2 | non-box | [14,10,1], 23, EXPRESS, z3, non-res | max(2.3, 140/166)→3 | 315 | 0 | 44.8875→45 | 360 |
| 3 | express residential | [10,10,10], 50, EXPRESS, z2, res | 7.19→8 | 760 | 450 | 172.425→172 | 1382 |
| 4 | fuel half-up | [2,2,2], 260, GROUND, z2, res | 26 (whole, stays) | 2470 | 530 | 3000*.1425=427.5→428 | 3428 |
| 5 | ceil billable (7.2 lb) | [1,1,1], 72, GROUND, z4, non-res | 8 | 944 | 0 | 134.52→135 | 1079 |
| 6 | non-box dim exactly whole | [1,2,83], 5, GROUND, z8, non-res | 166/166=1→1 | 190 | 0 | 27.075→27 | 217 |

A manifest of 1+2 (the example) totals 3360. Shipped code gives 1+2 = [13 lb, 1703+450+242=2395] + [2 lb, 210+0+29=239].
Half-up condition: (T+R) ≡ 200 (mod 400).
