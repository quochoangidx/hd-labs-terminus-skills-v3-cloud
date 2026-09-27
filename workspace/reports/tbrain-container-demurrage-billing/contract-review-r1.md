# Contract review r1: tbrain-container-demurrage-billing (blind)

Files read: instruction.md, environment/ only.

## Findings

### B1 BLOCKING: `days` and `charge` for a container NOT on demurrage
Tariff 2.3 defines demurrage days only for a container "on demurrage" (dwell > free). 3.1 says "Every container has demurrage days and a demurrage charge", but it gives the charge only for a container on demurrage. So for dwell <= free, the tariff is silent and the shipped value is kept: `days = dwell - free` (negative) and `charge = days * rate` (negative). The total goes down.
- Reader A (literal "keep today's behaviour, add no clamp"): negative days and negative charge.
- Reader B ("every container has demurrage days" and "not on demurrage" implies 0): days 0, charge 0.
- Counterexample: DRY, discharged 1405, picked_up 1407, rate 7500. Dwell 3, free 5. A gives days -2, charge -15000. B gives days 0, charge 0. The totals differ too.
- The shipped example already contains this case (CAIU2200417). The instruction also asks for "inside their free time" and "on the discharge day" cases, so every hidden file probably hits it.
- Minimal fix: give the answer in the tariff. Either add "a container not on demurrage has 0 demurrage days and a charge of 0" (clean contract), or add a sentence to the instruction confirming that negative figures stay. The first is strongly preferred, because a negative charge is commercially absurd and graders may themselves disagree.

### S1 SHOULD-FIX: TANK free days
2.2 names dry and reefer only. The kept value is 5 (`FREE_DAYS`, same for every type), and it can be derived uniquely. But a reader could treat tank as "no free time" (0), or treat tank like reefer (special equipment). Counterexample: TANK 100→110, rate 1000. Kept: free 5, days 6, charge 8000. Alt (free 0): days 11, charge 18000. Fix: this is probably the intended silent figure, so keep it, but make sure nothing hints otherwise. One optional line would help: "the tariff sets no free time for other types."

### S2 SHOULD-FIX: whether the tier applies to the negative/zero branch
If B1 is kept as negative, the new tier formula `min(d,4)*r + 2*max(d-4,0)*r` and the kept `d*r` agree for d <= 0. So there is no divergence, but only by coincidence. A reader who writes `4*r + 2*(d-4)*r` unconditionally gets a different answer for negative d (d=-2: -8r vs -2r). Resolving B1 removes this issue.

### P1 POLISH
- "Its demurrage days are its dwell less its free days" together with 3.1 "first 4 ... after the fourth" is unambiguous, and there is no rounding (all integers). No order-of-operations problem.
- Dwell == free: "longer than" means not on demurrage. Both readings give 0 there, so it is safe.
- Output: key order inside objects is irrelevant if the comparison is JSON-parsed. The instruction says "compared exactly as JSON integer or string", which is fine. The driver dumps with default separators and the driver stays unchanged, so it is fine.
- Input limits are complete (types, days, span 0–120, rate, count, id). Rates up to 1e5 × about 236 days × 200 containers fit in Python ints, so there is no overflow issue.

## Silent figures and kept values
| Figure | Kept value |
|---|---|
| TANK free days | 5 |
| Demurrage days when dwell <= free | dwell - free (can be negative, no clamp) |
| Charge when not on demurrage | days × rate (negative or 0) |
| Total | plain sum, including negatives (3.2 governs the sum itself) |

## Witnesses (literal reading; the B1 alternative in brackets)
Dwell = picked_up - discharged + 1. The charge is r per day for days 1–4 and 2r per day after that.

| # | Case | Input | dwell | free | days | charge |
|---|---|---|---|---|---|---|
| 1 | DRY, >4 demurrage days | 1402→1413, r 7500 | 12 | 5 | 7 | 4·7500+3·15000 = 75000 |
| 2 | REEFER | 1404→1409, r 12000 | 6 | 3 | 3 | 36000 |
| 3 | TANK | 100→110, r 1000 | 11 | 5 | 6 | 4000+4000 = 8000 |
| 4 | picked up on discharge day (DRY) | 50→50, r 100 | 1 | 5 | -4 [0] | -400 [0] |
| 5 | inside free time (DRY) | 1405→1407, r 7500 | 3 | 5 | -2 [0] | -15000 [0] |
| 6 | exactly 4 demurrage days (REEFER) | 0→6, r 100000 | 7 | 3 | 4 | 400000 |

Example file NQ-0611 total: 75000 + 36000 - 15000 = 96000 [B1 alt: 111000].
