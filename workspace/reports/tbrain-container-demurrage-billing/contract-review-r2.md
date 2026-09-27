# Contract review r2: tbrain-container-demurrage-billing (blind)

Files read: contract-packet-r2/instruction.md and environment/ only.
Diff against r1: rule 2.2 now opens with "Every container has free days." Nothing else changed.

## B1 re-examined: is there any warrant for 0?
I looked for text that could support 0 days or a charge of 0 for a container not on demurrage:
- Tariff preamble, "sets the demurrage charged on import containers left in the terminal after discharge": this states the scope. It gives no figure.
- 2.3, "A container whose dwell is longer than its free days is on demurrage": this defines the status. It says nothing about the figures when the status does not hold.
- 3.1, "Every container has demurrage days and a demurrage charge": this says the figures exist, but it gives no value for a container off demurrage.
- The README describes the fields only and gives no value.

No sentence gives 0. The instruction covers exactly this situation: "that step keeps working the figure out the way it does today, from the figures the tariff does define" (days = dwell − free, charge = days × rate), and "Add no exception, clamp or guard that the tariff does not give". A 0 could only come from outside commercial intuition, and adding it would be a clamp the text forbids. I withdraw **B1 as a divergence between honest readers**. It is now POLISH: the negative figures are intended, but they look odd to a billing reader. The instruction's second paragraph already carries the warrant.

## Remaining findings
- **S1 (TANK free days) is resolved in part.** 2.2 now says every container has free days, but it gives no number for a tank. The kept value is `FREE_DAYS` = 5, and it can be derived uniquely. The earlier alternative of "0 / none" is now ruled out. Nothing supports 3. It is now POLISH.
- **S2 is downgraded to POLISH.** For a container not on demurrage, the charge step keeps days × rate. The higher-rate rule in 3.1 applies only to a container on demurrage, so a solver who applies it unconditionally is departing from the text. That is a solver error, not a divergence between honest readers.
- **No BLOCKING or SHOULD-FIX findings remain.** Rounding, input limits and the output format are all clean (unchanged from r1).

## Silent figures and kept values
| Figure | Kept value |
|---|---|
| TANK free days | 5 |
| Demurrage days, dwell <= free | dwell − free (0 or negative) |
| Charge, not on demurrage | days × rate (0 or negative) |

## Witnesses (unchanged; only one reading now)
| # | Case | Input | dwell | free | days | charge |
|---|---|---|---|---|---|---|
| 1 | DRY, more than 4 days | 1402→1413, r 7500 | 12 | 5 | 7 | 75000 |
| 2 | REEFER | 1404→1409, r 12000 | 6 | 3 | 3 | 36000 |
| 3 | TANK | 100→110, r 1000 | 11 | 5 | 6 | 8000 |
| 4 | Picked up on discharge day (DRY) | 50→50, r 100 | 1 | 5 | -4 | -400 |
| 5 | Inside free time (DRY) | 1405→1407, r 7500 | 3 | 5 | -2 | -15000 |
| 6 | Exactly 4 days (REEFER) | 0→6, r 100000 | 7 | 3 | 4 | 400000 |

Example NQ-0611 total: 96000.
