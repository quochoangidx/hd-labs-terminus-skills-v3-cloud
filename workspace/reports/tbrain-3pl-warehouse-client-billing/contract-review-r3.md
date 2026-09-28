# Contract review r3: tbrain-3pl-warehouse-client-billing (reviewer C)

Packet read: `contract-review-packet-r3/instruction.md` and `environment/` only. I checked witnesses against an independent scratch reference (`ref3.py`, outside the repo), which has switches for each contested reading.

What is new in r3:
- Signed `dispatches` entries. An entry below nought is a return into stock, and 2.1 defines "a dispatch" as only "an entry of one pallet or more".
- 3.2 and 5.2 are narrowed from "movement" to "a receipt or a dispatch".
- 2.5 and 2.6 are removed. The surcharge is now on *billed* storage, and 1.3 no longer says "Nothing else is rounded".
- Receipts are billed at `out` (a new seeded bug). Dispatch x pallets is already correct in the code.
- The instruction adds: "Add no exception, clamp or guard for inputs the schedule does not provide for, such as entries of nought or below and lots that have no billed week in the period."

## Status of r2 findings

| r2 | Status |
|---|---|
| F1: minimum-fee surcharge rounding (1.3 versus 2.5/2.6) | **Closed.** 6.2 now takes "`surcharge_percent` of its billed storage, rounded as 1.3 says", with no silence. A minimum-fee lot gets a half-up surcharge on the minimum (W5 = 53). |
| F2: silent peak computed with today's versus corrected on_hand | **Still open as polish, and now compounded.** The silent peak survives, since 4.5 over an empty set has no rule, but the explicit 2.6 "never taken as nought" is gone. The only barrier left is the instruction's "no ... guard for ... lots that have no billed week". On-hand itself is now partly silent (returns, see F3), so "carried out on the values the schedule does define" has a mixed on_hand underneath it. See F5. |
| F3: instruction looser than 1.4 on effective dates | **Mostly closed.** The instruction now says "the first taking effect before any of the client's lots arrive". It still omits "and on or before the period's start" and says "before" where 1.4 says "on or before". Polish only (F6). |

## Package defects (full list)

1. `lots.on_hand` subtracts every entry with `when <= day`. **Dispatches** (entries of 1 or more) should be subtracted only from the next day (2.1, 2.2). **Returns and zero entries** have no timing rule, so they keep today's `<=` (silence plus the instruction). A uniform `<` is wrong for returns.
2. `storage.week_starts` uses Mondays. It should use receipt + 7k (2.4).
3. `storage.storage` uses one tier from `week_number(end)`. It should use a per-week tier (4.2).
4. `rates.rates_for` uses `revisions[-1]`. It should use the revision in force on the week's first day, the receipt date or the dispatch date (3.1, 3.2). Returns keep today's, which is contested (F1).
5. `handling` bills the receipt at `"out"`. It should be `"in"` (5.1).
6. `Calendar.is_out_of_hours` is weekend-only. It should also cover holidays for receipts and dispatches (2.3, 5.2). Returns keep today's, which is contested (F1).
7. `storage.peak` is a daily maximum. It should be the maximum on-hand on the first days of billed weeks (4.5). A lot with no billed weeks is silent and keeps the daily maximum.
8. `surcharge_on` floors. It should round half-up on billed storage (1.3, 6.2).

Already correct and to be left alone: dispatch x pallets, `billed_storage` (4.4), amount and total (6.3), the section 7 layout.

## Part 1: findings

**F1 (blocking): a return entry's handling rate: today's `revisions[-1]` and weekend-only, or the in-force revision and working days?**
Citations:
- 3.2: "The rates of a receipt or a dispatch are those of the revision in force on its date."
- 5.2: "A receipt or a dispatch dated on a day that is not a working day ..."
- Instruction: "that value keeps the calculation the package makes for it today, carried out on the values the schedule does define".
- Instruction symptoms: "movements on public holidays are billed at the weekday rate, weeks and movements from before the mid-June rate card were billed at the new rates".

Reading A (the apparent design, given how carefully 3.2 and 5.2 were narrowed): a return is neither a receipt nor a dispatch, so its rate is silent and keeps today's `rates_for(client)` (latest revision) and `is_out_of_hours` (weekends only).

Reading B has two parts:
- *"Carried out on the values the schedule does define."* Today's code calls its lookup "The client's revision in force", and "revision in force on a day" is a schedule-defined value (3.1). Likewise "out of hours" is the schedule's "not a working day" (2.3). So the retained calculation `N x rate(revision in force, working day?)` uses the corrected values.
- The instruction calls holiday and pre-revision **movements** bugs. A return is a movement in the schedule's own vocabulary (1.1 "the time of day of a movement", 1.2 "per pallet moved").

Counterexamples (single out=20, after_hours=50 unless noted; lot received Mon 06-01 with 10 pallets; 5 dispatched Tue 06-02; June period; storage 0):
- **W7:** return -3 on Fri 06-19, a holiday. A: -3x20, handling 140. B: -3x50, handling 50.
- **W8:** revisions 01-01 (out 20) and 06-15 (out 40); return -3 on Wed 06-10. A: -3x40 (latest), handling 80. B: -3x20 (in force), handling 140.

The instruction invites returns on holidays and around revisions ("some of nought and some below nought", "on every day of the week and on holidays", "rate cards revised ... six times"), so these combinations will be graded.

Fix: have the authority say positively how a return is billed, or say that the *rate choice* of an entry that is neither a receipt nor a dispatch is outside the schedule. Also reword the instruction's symptom sentences from "movements" to "receipts and dispatches".

**F2 (should-fix): the closing sentence "This schedule gives no other charge, credit or waiver" competes with the negative handling for returns.**
Reading A: silence means today's `pallets * rate` applies with N < 0, so the return is a credit. The instruction's "no ... guard for ... entries of nought or below" backs this. Reading B: 5.1 and 5.2 bill only receipts and dispatches, and the schedule "gives no other ... credit", so a return is billed nothing.
Counterexample W6: a return of -3 on a working day at out=20 gives handling 140 under A and 200 under B.
The instruction's no-guard sentence pushes strongly towards A, so this is should-fix, not blocking. Still, the authority carries a sentence that on its face governs the case. Fix: "... no other charge, credit or waiver for receipts and dispatches", or drop the sentence.

**F3 (no defect; this is the legitimate trap): return timing in on_hand.**
2.2 gives the next-day rule only for "a dispatched pallet", and 2.1 defines a dispatch as "an entry of one pallet or more". A return's timing therefore has no rule, and today's `<=` applies: returned pallets are on hand on the entry day itself. The natural global `<=` to `<` fix is wrong for returns.
Counterexample W6: a return of -3 on the week-start 06-08. On-hand that day is 8 by the rule, 5 under a uniform `<`. Storage is 4200 versus 3900.
It is drawn with the authority's defined terms, so it is fine as a trap.

**F4 (polish, but confirm the oracle agrees): 1.4 lets on-hand exceed the pallets received.**
"For every date, the lot's entries dated before it, and its entries dated on or before it, each add up to between nought and the pallets it received" does not stop a same-day +5 / -3 on the receipt date. Under the mixed timing, on-hand on that day is 10 - 0 + 3 = **13** (W10: peak 13 with 10 pallets received). The rule is determinate, but make sure the oracle and the fuzz generator produce and accept it. Per-date netting (a plausible alternative instinct, giving +2, a dispatch, so 10) is ruled out only by 2.1's per-entry definition.

**F5 (polish): the silent peak has lost its explicit "never nought".**
4.5 over no billed weeks is silent. The instruction's "no ... guard for ... lots that have no billed week" is the only thing that rules out `max(..., default=0)`. It is adequate, but the r2 2.6 wording was stronger.
W9: received 05-20 with 10 pallets, all dispatched Mon 06-01, June period. No billed weeks; the peak is the daily maximum with the (mixed) on_hand = 10, whereas the `default=0` instinct gives 0.

**F6 (polish): the instruction's first-revision wording is a little loose** ("before any of the client's lots arrive" versus 1.4's "on or before ... and on or before the period's start").

**Checked, with no defect found:**
- Every numeric range in 1.4 has a floor and a ceiling (entries now -1000..1000, plus the cumulative constraint).
- Rounding has one site. Ordering and types are specified.
- The left-open list matches 1.4 ("entries or rate cards that clause 1.4 does not allow").
- Zero entries are inert under every reading (0 x rate, no on-hand change).

## Witnesses

One revision effective 2026-01-01, storage [[null,100]], in=10, out=20, after_hours=50, minimum 0, surcharge 0, period June 2026, unless noted. Fields: weeks / peak / storage / handling / surcharge / amount.

| # | Input | Expected |
|---|---|---|
| W1 | Received Mon 06-01, 10 pallets; +10 on Mon 06-08 | 2 / 10 / 2000 / 100+200=300 / 0 / 2300 |
| W2 | Period 06-01..06-28; received Wed 06-03, 1 pallet | 4 / 1 / 400 / 10 / 0 / 410 |
| W3 | Revisions 01-01 [[3,100],[2,200],[null,300]] and 06-20 [[3,1000],[2,2000],[null,3000]]; received 05-18, 1 pallet | 5 / 1 / 100+200+200+3000+3000 = 6500 / 0 / 0 / 6500 |
| W4 | Storage 0; holiday Fri 06-19; received Tue 06-02, 5 pallets; +3 on 06-19 | 5 / 5 / 0 / 5x10 + 3x50 = 200 / 0 / 200 |
| W5 | Period 06-01..06-07; rate 400, minimum 1050, 5%; received 06-01, 1 pallet | 1 / 1 / 1050 / 10 / 53 / 1113 |
| W6 | Received 06-01, 10 pallets; +5 on 06-02; -3 on Mon 06-08 | 5 / 10 / 10+8+8+8+8 = 4200 / 100+100-60 = 140 / 0 / 4340. Uniform `<`: storage 3900. F2-B: handling 200. |
| W7 | Storage 0; as W6 but -3 on Fri 06-19 (holiday) | 5 / 10 / 0 / **140 (A, guess)** or 50 (B) / 0 / same as handling |
| W8 | Storage 0; revisions 01-01 (out 20) and 06-15 (out 40); as W6 but -3 on Wed 06-10 | 5 / 10 / 0 / **80 (A, guess)** or 140 (B) / 0 |
| W9 | Received 05-20, 10 pallets; +10 on Mon 06-01 | 0 / **10** (silent, daily maximum) / 0 / 200 / 0 / 200 |
| W10 | Storage 0; received 06-01, 10 pallets; +5 and -3 both on 06-01 | 5 / **13** / 0 / 100+100-60 = 140 / 0 / 140 |
| Ex | `examples/small-job.json` (BH-0921 now has -2 on Tue 06-16, not a week start) | total **217454** on my reference under both F1 readings (F2-B gives 218154). The shipped code gives 211914. The example exercises neither F1 nor the return-timing trap. |

Guesses: W7 and W8 (F1), and the credit sign in W6/W7/W8/W10 (F2, where I took A).

## Part 2: solver-path screen

**A) Pre-mortem.** A strong solver would map the eight symptoms to defects 1–8 and fix them in minutes: anniversary weeks, per-week tier and revision, `in` for receipts, holidays, half-up, peak. It would then write its own reference and diff-fuzz.

The decisive part is the signed-entry cluster, where three things can go wrong:
- **Timing.** Changing `<=` to `<` in `on_hand` looks like the obvious fix for "shipped out on the day a storage week begins". Only a solver that notices 2.1's "a dispatch is an entry of one pallet or more" keeps same-day for returns.
- **Rate.** Most solvers fix `rates_for(client, day)` and `is_out_of_hours` centrally, and returns then pick up the in-force revision and holidays (reading B). Only a solver that carefully follows "a receipt or a dispatch" keeps today's rates for returns, and even then "carried out on the values the schedule does define" gives it grounds to switch.
- **Credit.** A solver that reads "no other ... credit" may zero out returns. The instruction's "no guard" line argues against it.

Self-verification cannot catch any of these, because the solver's own reference encodes the same reading. Fuzzing with returns on week starts or holidays only shows agreement with itself.

**B) Scores** (5 = strongly resists)
- reference_unreachable: **2**. About 80 lines, fully derivable except the contested choices.
- authority_incomplete_for_grading: **2**. This is a defect score: F1 is blocking and F2 is should-fix.
- hidden_state_not_closed_form: **1**.
- restraint_traps: **3**. Two legitimate sites count:
  1. Return timing: kept `<=` inside the `on_hand` aggregate the solver must rebuild, excluded only through the domain-word chain "dispatch = entry of one or more".
  2. The silent peak inside the rebuilt `peak`.

  The return rate and calendar, and the return credit sign, are not counted: they fail the 0/8 screen, because competing instruction and authority sentences exist (F1, F2).
- fuzz_blind_spot: **3**. Returns on week starts, holidays, or before a revision, and same-day +/- pairs, are sparse corners. A solver's self-fuzz mirrors its own reading.

**C)**
- self_verification_resistance: **3**
- prediction: **resists** (I expect at least one of two solvers to miss something). A meaningful share of that comes from F1/F2 (defects). With F1/F2 fixed, the legitimate return-timing trap alone is roughly a coin flip per solver.
- confidence: medium-low
- decisive_reason: the governed fixes are routine, and the outcome turns on the signed-entry cluster. Its timing sub-trap is a fair, definition-anchored restraint, but its rate, calendar and credit-sign sub-cases rest on silences that the instruction's own "movements" symptoms and "values the schedule does define" clause, plus the schedule's "no other ... credit", pull the other way.
