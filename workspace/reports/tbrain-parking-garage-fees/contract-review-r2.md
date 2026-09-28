# Contract review r2: tbrain-parking-garage-fees (blind)

Scope: I read only `contract-packet-r2/`. The diff against r1 is limited to tariff rule 2.2, the instruction's grace symptom and example T00413 (validated changed to false).

## Verdict
There are no BLOCKING divergences, and the r2 changes introduce none.

## Reference semantics (r2)
- stay = exit - entry; hours = ceil(stay/60) for every vehicle, including grace stays
- grace applies to a CAR or VAN with stay <= 15; a MOTO never has a grace period
- rate CAR 300 / VAN 450 / MOTO 150
- fee = 0 if grace, otherwise hours*rate. A MOTO stay of 1-15 minutes gives 1*150 = 150, and a stay of 0 gives 0.
- CAR/VAN: fee = min(fee, 2400*ceil(stay/1440)); MOTO has no cap
- due = fee - 200 if validated, otherwise fee (silent, kept, can be negative); total = sum(due)

## Checks on the r2 changes
1. **MOTO with a stay of 15 minutes or less.**
   - Rule 2.2 now leaves motorcycles out explicitly, and 3.2's "any other session" charges them.
   - The instruction symptom ("cars and vans") matches the rule. There is no textual hint that motorcycles keep a grace period.
   - The only possible misread is a solver keeping an unscoped check such as `stay <= 15`. That is a solver bug, not an ambiguity. Unique.
2. **MOTO stay 0.** hours 0, fee 0. Unique.
3. **Example change.** The example no longer shows a negative due. Negative dues are still reachable in billed files: a validated car or van in grace gives -200, and a validated MOTO with fee 150 gives -50.
   - SHOULD-FIX (carried from r1, unchanged): "Add no exception, clamp or guard" settles these values. Optionally add "an amount due may be below zero" so solvers do not add a floor at 0.
4. **Other r1 POLISH items still hold.** The validation credit is silent and kept. The credit is applied after the daily maximum. Hours are still reported during grace. The daily maximum counts begun 24-hour periods as ceil(stay/1440).
5. **Limits and output format.** Unchanged, and there are no gaps.

## Witnesses (r2)
| Session | stay | hours | fee | due |
|---|---|---|---|---|
| CAR, grace (10 min), validated | 10 | 1 | 0 | -200 |
| VAN, 61 min | 61 | 2 | 900 | 900 |
| CAR, 1440 min | 1440 | 24 | 2400 | 2400 |
| CAR, 1441 min | 1441 | 25 | 4800 | 4800 |
| MOTO, 4320 min (3 days) | 4320 | 72 | 10800 | 10800 |
| MOTO, 30 min, validated | 30 | 1 | 150 | -50 |
| (new) MOTO, 10 min, validated | 10 | 1 | 150 | -50 |
| Example T00413 VAN, 12 min, unvalidated | 12 | 1 | 0 | 0 |

The r2 example statement is: T00412 CAR 130 min gives 3 h, fee 900, due 900. T00413 gives 1 h, 0, 0. T00417 MOTO 1860 min gives 31 h, 4650, 4650. Total 5550.

## Silent figures and their kept values
- Validation credit: 200 cents, subtracted for every validated session, with no floor and no dependence on vehicle.
- Amount due: fee - credit, or fee.
- Total: the sum of due.
- Statement shape and order: as shipped.
