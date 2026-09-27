# Contract review r4 — tbrain-parcel-dim-weight-billing (blind)

Compared contract-packet-r4 with r3. The only change is the instruction's fuel clause, which now reads "on ground parcels the fuel line leaves out part … and drops fractions of a cent the rules round". The rules, code, README, driver and example are unchanged.

## Status
- **G1 CLOSED.** The instruction no longer describes a fuel defect for express parcels. Express fuel is silent in 3.3, so the only reading left is the kept step: floor(T*1425/10000), taken on the corrected transport charge only.
- **G2 SHOULD-FIX (a note for the solver and tests, not a contract ambiguity).** The fuel step has to branch on service. Keep an express-residential witness in the tests to pin two things: R is excluded from the express fuel base, and the fraction is dropped.
- F1–F3 stay closed. F4 is polish and unchanged: a box's dimensional weight is never a whole pound.

## New divergences
None found. I re-checked:
- the box threshold;
- rounding billable weight up from the unrounded figure;
- ground fuel rounded half-up in integer cents;
- express fuel truncated;
- integer output;
- parcel order;
- the input limits of rule 1.3.

## Silent figures and kept values
| Figure | Kept value |
|---|---|
| Non-box dimensional divisor | 166 |
| Residential surcharge, EXPRESS to a home | 450 |
| Fuel surcharge, EXPRESS | floor(T*1425/10000), residential surcharge excluded |

## Witnesses
| Input | billable | T | R | F | total |
|---|---|---|---|---|---|
| [18,12,10], 84, GROUND, z5, res | 16 | 2096 | 530 | 374 | 3000 |
| [14,10,1], 23, EXPRESS, z3, non-res | 3 | 315 | 0 | 44 | 359 |
| [10,10,10], 50, EXPRESS, z2, res | 8 | 760 | 450 | 108 | 1318 |
| [2,2,2], 260, GROUND, z2, res (fuel 427.5 → 428) | 26 | 2470 | 530 | 428 | 3428 |
| [1,1,1], 72, GROUND, z4, non-res (7.2 → 8) | 8 | 944 | 0 | 135 | 1079 |
| [1,2,83], 5, GROUND, z8, non-res | 1 | 190 | 0 | 27 | 217 |
