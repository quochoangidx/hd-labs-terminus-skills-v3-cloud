# Contract review r2: tbrain-3pl-warehouse-client-billing (reviewer C)

Packet read: `contract-review-packet-r2/instruction.md` and `environment/` (Dockerfile, README, billing-schedule.md, driver, 6 package modules, small-job.json). Nothing else opened. I checked the witnesses against an independent scratch reference (`ref2.py`, outside the repo).

## Status of r1 findings

| r1 | Status | Why |
|---|---|---|
| F1 open-lot discount (3 readings) | **Closed** as worded (discount and open/closed status removed). **The same shape reappears** as r2 F1 below (a silenced 6.2 figure versus the 1.3 rounding sentence). | |
| F2 scope of the 3.1 silence | **Closed** | 1.4 now requires "A client's first revision takes effect on or before the receipt date of each of its lots and on or before the period's start". A revision is therefore always in force for every week start (at or after receipt) and every movement (at or after receipt). 3.1 no longer has a silence sentence. |
| F3 distinct dispatch dates | **Closed** | 2.1: "Several dispatches may share a date." |
| F4 unnamed discount-base bug | **Closed / moot** | The symptoms now name the peak and the surcharge cent. The surcharge base issue (minimum fee is not a storage charge) is again visible only through 2.5/6.2, but under the author's apparent reading the base does not change the output. See F1. |

## Package defects (full list)

1. `lots.on_hand` counts dispatches with `when <= day`. It should be `<`: a pallet is still on hand on its dispatch day (2.2).
2. `storage.week_starts` uses calendar Mondays. It should use receipt date + 7k (2.4).
3. `storage.storage` takes one tier for every week, from `week_number(end)`. It should be the tier of each billed week's own number, not retroactive (4.2).
4. `rates.rates_for` always uses `revisions[-1]`. It should use the revision in force on the week's first day or the movement date (3.1, 3.2). Used in both storage and handling.
5. `handling` bills a dispatch at `rate x 1`. It should be `rate x pallets dispatched` (5.1).
6. `Calendar.is_out_of_hours` treats only weekends as out of hours. Holidays are also not working days (2.3, 5.2).
7. `storage.peak` takes the daily maximum over the period. It should be the largest on-hand count on the first days of billed weeks (4.5). A lot with **no billed weeks** has no such figure, so 2.6 makes it silent and it keeps today's daily maximum, computed with the corrected on_hand.
8. `surcharge_on` floors. On a storage charge it should round half-up (1.3, 6.2). A **minimum-fee lot** has no storage charge (2.5), so its surcharge is silent under 2.6 and, on the apparent intended reading, keeps today's floor of billed storage x pct. See F1.

These are unchanged and correct: `billed_storage` (4.4), the amount (6.3), the total (6.3), and ordering and types (7). A lot with no billed weeks gets surcharge 0 under both readings (0 x pct), so that silence has no effect on output.

## Part 1: findings

**F1 (blocking): the minimum-fee surcharge is silenced by 2.5/2.6, but 1.3 positively governs "an energy surcharge".**
Citations:
- 2.5: "a minimum fee is not a storage charge"
- 6.2: "`surcharge_percent` of its storage charge, rounded as 1.3 says"
- 2.6: "that clause gives no rule for the value it defines"
- 1.3: "The one figure that can fall between two whole cents is an energy surcharge (6.2). It is rounded to the nearest cent, and an exact half cent is rounded up. Nothing else is rounded."

Reading A (the apparent design): 6.2 is silent for a minimum-fee lot, so the surcharge keeps today's `billed_storage * pct // 100`, which is floored. Reading B: 1.3 is a free-standing rule about every energy surcharge and "nothing else is rounded", so the silenced value is still rounded half-up. Only the choice of base falls back to today's code. The screen's own test is "does any sentence in the authority positively govern a case the instruction calls silent?" Here 1.3 does, arguably, and the natural expert instinct (fix the rounding helper once, for every surcharge) points the same way as B.

Counterexample (W7): minimum 1050, surcharge 5%, a lot billed one week at 400. Billed storage is 1050. A gives surcharge 52 (amount 1112); B gives 53 (amount 1113).

The instruction advertises "surcharges from none to half on storage that leaves a half cent or more". A grader using A therefore fails B-readers on a routine share of jobs. This is the same B/B' split as r1 F1.

Fix: either write 1.3 as "An energy surcharge that 6.2 gives is rounded ...", with an explicit note that where 6.2 gives no rule, 1.3 does not apply either, or drop the silence and let minimum-fee lots pay a half-up surcharge on the minimum.

**F2 (polish): "today's calculation" for a silent peak could be read with today's `on_hand`.**
The instruction says "carried out on the values the schedule does define", and on-hand is defined in 2.2, so the corrected on_hand is the reading the text supports. A solver who keeps the old `peak()` function but forgets that it calls the old helper would differ. Counterexample W9: received 2026-05-20, 10 pallets, all dispatched Mon 06-01, June period. The corrected on_hand gives peak 10; the old helper gives 0. This is covered by the text, so no change is needed. It is just a likely failure point.

**F3 (polish): the instruction's rate-card range sentence is looser than the new 1.4.**
The instruction says "effective dates anywhere in the 400 days before the period ends". 1.4 now also pins the first revision to on or before every receipt and the period start, and the instruction's open list covers "rate cards that clause 1.4 does not allow". The two are consistent, but a solver skimming only the instruction might still write a guard for "no revision in force". Harmless.

**Checked, with no defect found:**
- Every numeric range has both a floor and a ceiling. New in r2: minimum 0–1,000,000 and surcharge 0–50.
- Rounding has one authority (1.3). Tier and anniversary conventions are stated. Ordering, JSON types and field list are in section 7.
- 2.6's "including the largest or smallest of figures it has none of ... never taken as nought" draws the peak silence in defined terms, so the natural `max(..., default=0)` is ruled out in writing.
- I found no other sentence that positively governs an instruction-silent case besides F1.

## Witnesses

One revision effective 2026-01-01, storage [[null,100]], in=10, out=20, after_hours=50, minimum 0, surcharge 0, period June 2026, unless noted. Fields: weeks / peak / storage / handling / surcharge / amount.

| # | Input | Expected |
|---|---|---|
| W1 | Received Mon 06-01, 10 pallets; all dispatched Mon 06-08 | 2 / 10 / 2000 / 300 / 0 / 2300 |
| W2 | Period 06-01..06-28; received Wed 06-03, 1 pallet | 4 / 1 / 400 / 10 / 0 / 410 (old Monday code: 3 weeks) |
| W3 | Tiers [[3,100],[2,200],[null,300]]; received 05-18, 1 pallet | 5 / 1 / 1100 (weeks #3..#7 = 100+200+200+300+300) / 0 / 0 / 1100 |
| W4 | Storage 0; holiday Fri 06-19; received 06-19, 5 pallets; two dispatches Mon 06-22 of 1 and 2 | 2 / 5 / 0 / 5x50 + 3x20 = 310 / 0 / 310 |
| W5 | Revisions 01-01 (100, out 20) and 06-10 (1000, out 40); received 06-01, 2 pallets; dispatched Fri 06-12, 2 | 2 / 2 / 400 / 20 + 80 = 100 / 0 / 500 |
| W6 | Period 06-01..06-07; storage 1050, 5%; received 06-01, 1 pallet | 1 / 1 / 1050 / 10 / 53 (52.5 rounded up) / 1113 |
| W7 | As W6 but rate 400 and minimum 1050 | 1 / 1 / 1050 / 10 / **52 (reading A, guess)** or 53 (B) / 1112 or 1113 |
| W8 | Received Wed 05-27, 10 pallets; 4 dispatched Tue 06-02 | 4 / **6** (old daily-max code: 10) / 2400 / 80 / 0 / 2480 |
| W9 | Minimum 5000, 10%; received 05-20, 10 pallets; all dispatched Mon 06-01 | 0 / **10** (silent, so daily max with corrected on_hand) / 0 / 200 / 0 / 200 |
| W10 | Period 06-02..06-02; minimum 5000, 10%; received Mon 06-01, 7 pallets; 3 dispatched 06-01 | 0 / 4 / 0 / 0 / 0 / 0 |
| Ex | `examples/small-job.json` | total 214954 on my reference (the shipped code gives 189724). The example never exercises F1: BH-0934 is a minimum-fee lot but BLUEHARBOR's surcharge is 0%. |

Guesses: W7 depends on F1. For W9 and W10 I took the silent peak as the daily maximum using the corrected on_hand, which is what the text supports (F2).

## Part 2: solver-path screen

**A) Pre-mortem.** A strong solver would read the one-page schedule and six small modules and map the eight symptoms to fixes 1–8 above. Each is a few lines. It would write an independent reference from the schedule and diff-fuzz it over the 1.4 envelope, which is plain date arithmetic with no hidden state, so it converges fast.

Two restraint sites decide the outcome:
- **Peak for lots with no billed weeks.** The natural rewrite `max(first-day on-hand)` raises an error or defaults to 0. 2.6 names this exact case ("largest ... of figures it has none of ... never taken as nought"), so a careful solver will keep the daily-max fallback. A hasty one writes `default=0` and fails whenever a lot is on hand in the period with no billed week, which is common with short periods and lots dispatched early in a week.
- **Minimum-fee surcharge.** Most solvers will replace the floor with half-up in `surcharge_on` for every lot. That is reading B, and it fails if the grader follows A. Some will follow the 2.5, 2.6 and "keeps today's calculation" chain and keep the floor.

The solver's own tests carry its own reading, so self-checks cannot detect either choice.

**B) Scores** (5 = strongly resists)
- reference_unreachable: **2**. The reference is about 70 lines and fully derivable, apart from the F1 choice.
- authority_incomplete_for_grading: **2**. This is a defect score: F1 is blocking and everything else is complete.
- hidden_state_not_closed_form: **1**.
- restraint_traps: **3**. One legitimate site counts: the silent peak. It sits inside the `peak` aggregate that the repair forces the solver to rebuild, and it is reached through the 2.4 to 4.5 to 2.6 definitional chain with a strong contrary instinct (`default=0`) that 2.6 explicitly forbids. The minimum-fee surcharge floor would be a second site, but it fails the screen because 1.3 is a competing positive rule, so it is a defect, not a point.
- fuzz_blind_spot: **2**. Differential fuzzing is blind only at the reading-dependent sites (silent peak, minimum-fee surcharge).

**C)**
- self_verification_resistance: **3**
- prediction: **resists (at least one of two solvers fails)**, but most of that resistance comes from F1 (the ambiguous minimum-fee rounding). With F1 fixed I would expect **collapses** unless a solver falls into the silent-peak `default=0` trap.
- confidence: medium-low
- decisive_reason: the governed fixes are all short and closed-form. What remains is the well-drawn silent-peak trap, which is legitimate, and the minimum-fee surcharge rounding, which is a contract defect because 1.3 positively governs every energy surcharge while 2.5/2.6 silence this one.
