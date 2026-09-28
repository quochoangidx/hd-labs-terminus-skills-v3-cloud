# Contract review r1: tbrain-parking-garage-fees (blind)

Scope: I read only `contract-packet-r1/instruction.md` and `environment/`.

## Verdict
There are no BLOCKING divergences. Every figure comes out unique once the instruction's own sentences are applied.

## Reference semantics (derived)
- stay = exit - entry; hours = ceil(stay/60) (GT-2 2.1, shipped already matches)
- grace = stay <= 15 (2.2)
- rate CAR 300 / VAN 450 / MOTO 150 (3.1)
- fee = 0 if grace else hours*rate (3.2)
- CAR/VAN: fee = min(fee, 2400*ceil(stay/1440)) (3.3); MOTO has no cap
- due = fee - 200 if validated else fee (silent, kept; this can be negative)
- total = sum(due) (silent, kept)
- `hours` is still ceil(stay/60) during grace. Grace zeroes only the fee.

## Findings
1. SHOULD-FIX: a validated ticket in its grace period gives a negative `due`.
   - Car, stay 10, validated. Reader A keeps the credit: fee 0, due -200. Reader B floors it: due 0.
   - "Add no exception, clamp or guard" settles this as -200, so it is not blocking. Some solvers may still read it as a bug. The same goes for a validated MOTO with fee 150, which gives due -50.
   - Fix: none needed. The instruction could optionally add "an amount due may be below zero".
2. POLISH: the tariff never mentions validation.
   - A reader might think "the tariff governs, so there is no credit", which gives due = fee.
   - "keeps working the figure out the way it does today, from the figures the tariff does define" settles it: the credit stays and is taken from the new (capped, grace-zeroed) fee.
3. POLISH: the order of cap and credit.
   - The cap in 3.3 bounds the *parking fee* (README `fee`), and the credit is applied afterwards (as shipped, due is derived from fee). Unique.
4. POLISH: `hours` during grace.
   - One reader might print 0. But 2.1 defines charged hours independently of 2.2, and 3.2 only zeroes the fee. Unique: a 15-minute stay gives hours 1.
5. The day count in 3.3, "24 hours ... that have begun", is ceil(stay/1440).
   - Stay 0 gives cap 0, which is harmless because the fee is already 0. Stay 1440 gives 1 period and 1441 gives 2. Consistent with the wording of 2.1. No gap.
6. Input limits and output format.
   - The limits are inclusive, and duplicates and out-of-range values are left open.
   - Everything is integer arithmetic, so there is no float risk as long as solvers avoid `/`. `math.ceil(stay/60)` is exact in this range anyway.
   - The output is built by the fixed driver's `json.dump`, and the key order in `line()` does not matter for per-key comparison. No gaps.

## Witnesses
| Session | stay | hours | fee | due |
|---|---|---|---|---|
| CAR, grace (10 min), validated | 10 | 1 | 0 | -200 |
| VAN, 61 min, unvalidated | 61 | 2 | 900 | 900 |
| CAR, 1440 min | 1440 | 24 | min(7200, 2400) = 2400 | 2400 |
| CAR, 1441 min | 1441 | 25 | min(7500, 4800) = 4800 | 4800 |
| MOTO, 4320 min (3 days) | 4320 | 72 | 10800 (no cap) | 10800 |
| MOTO, 30 min, validated | 30 | 1 | 150 | -50 |

For comparison, the shipped outputs are: grace car 300/100, van 600, 24h car 7200, 24h1m car 7500, moto 10800, validated moto 150/-50.

## Silent figures and their kept values
- Validation credit: 200 cents, subtracted from fee for every validated session, with no floor and no dependence on vehicle.
- Amount due: fee - credit or fee.
- Total: the sum of due, which can be reduced by negative lines.
- Statement shape and order: as shipped.
