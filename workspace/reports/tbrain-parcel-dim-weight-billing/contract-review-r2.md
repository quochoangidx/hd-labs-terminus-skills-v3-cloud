# Contract review r2 — tbrain-parcel-dim-weight-billing (blind)

Compared contract-packet-r2 with r1. The only changes are rules 2.2, 3.2 and 3.3 in docs/parcel-billing-rules.md. instruction.md, the code, the README, the driver and the example are unchanged.

## Status of r1 findings
- **F1 CLOSED.** 3.2 now says every home parcel carries a surcharge and gives only the ground amount. An express home parcel therefore carries one, of an amount the rules leave silent, so it keeps today's 450. The "express home = 0" reading is ruled out.
- **F2 CLOSED.** 2.2 now says "Every parcel has a dimensional weight", so a non-box has one, with the divisor left silent. It keeps today's 166.
- **F3 CLOSED.** 3.3 now reads "of the sum of its transport charge and its residential surcharge".
- **F4 (POLISH, notes for the test author)**, unchanged. A box's dimensional weight is never a whole pound (139 is prime and larger than 108). Whole-pound cases come from non-boxes or actual weights.

## New divergences
None found. Checked:
- Box threshold of 2 inches, inclusive.
- Billable rounds up from the exact fraction, and a whole number stays (1.2 says figures are worked from unrounded figures).
- Half-up fuel on integer cents.
- Integer output.
- Parcel order.
- Rule 1.3 limits (weight at least 1, so billable is at least 1).
- 3.2's "not going to a home carries none" matches today's 0.

Minor wording point (POLISH, not divergent): 3.3's line is now longer than the other lines in the document. It is cosmetic.

## Silent figures and kept values
| Figure | Kept value |
|---|---|
| Dimensional divisor of a non-box (a side < 2) | 166 |
| Residential surcharge, EXPRESS to a home | 450 |

## Witnesses (unchanged from r1, all under the single reading)
| Input | billable | T | R | F | total |
|---|---|---|---|---|---|
| [18,12,10], 84, GROUND, z5, res (box, ground home) | 16 | 2096 | 530 | 374 | 3000 |
| [14,10,1], 23, EXPRESS, z3, non-res (non-box) | 3 | 315 | 0 | 45 | 360 |
| [10,10,10], 50, EXPRESS, z2, res (express home) | 8 | 760 | 450 | 172 | 1382 |
| [2,2,2], 260, GROUND, z2, res (fuel 427.5 → 428) | 26 | 2470 | 530 | 428 | 3428 |
| [1,1,1], 72, GROUND, z4, non-res (7.2 → 8) | 8 | 944 | 0 | 135 | 1079 |
| [1,2,83], 5, GROUND, z8, non-res (non-box dimensional weight exactly 1) | 1 | 190 | 0 | 27 | 217 |
