# Contract review r4: tbrain-3pl-warehouse-client-billing (reviewer C)

Packet read: `contract-review-packet-r4/instruction.md` and `environment/` only. I checked witnesses against an independent scratch reference (`ref4.py`, outside the repo), which has switches for the two restraint readings.

What is new in r4:
- A per-receipt `fee`, which 5.2 says "is the same on any day".
- `pallets` may be 0, and 2.1 now says "A receipt is an arrival of one pallet or more".
- Entries are on distinct dates.
- 5.3 bills only "its receipt and its dispatches", and the code already skips entries below 1.
- 4.5 now says "a lot with no billed week has a peak of nought".
- The instruction's symptoms now say "receipts and dispatches" instead of "movements", and its no-guard example is "pallet counts of nought or below".

## Status of r3 findings

| r3 | Status |
|---|---|
| F1: return rate (today's code versus in-force revision and working days) | **Closed.** 5.3 bills only "its receipt and its dispatches", so a return is not billed at all. There is no rate to choose, and the instruction's symptoms now name only receipts and dispatches. |
| F2: "no other ... credit" versus a negative return charge | **Closed.** No return is billed, so no credit arises, and that sentence now agrees with 5.3. |
| F3: return timing in on_hand | **Still present, as intended.** This is the legitimate restraint trap (see F-A below). Not a defect. |
| F4: on-hand above `pallets` from a same-day +/- pair | **Closed.** 1.4 now requires entries "on distinct dates". With one entry per date, the "on or before" sum is the "before" sum plus that day's entry, so a return -k on day d needs the "before" sum to be at least k. On-hand is then pallets - before + k, which is at most `pallets`. |
| F5: silent peak with no explicit "never nought" | **Closed by reversal.** 4.5 now governs positively: the peak is 0 with no billed week. Today's daily-maximum fallback becomes an outright bug. There is no silent peak any more. |
| F6: instruction's first-revision wording | **Closed.** The instruction now says "on or before the period's start and on or before the day each of the client's lots arrives", which matches 1.4. |

## Package defects (full list)

1. `lots.on_hand` subtracts every entry with `when <= day`. **Dispatches** (entries of 1 or more) should be subtracted only from the next day (2.1, 2.2). **Returns** (below 0) have no timing rule and keep today's `<=`, so they are on hand on the entry day. Zero entries make no difference either way.
2. `storage.week_starts` uses Mondays. It should use `received` + 7k (2.4).
3. `storage.storage` takes one tier from `week_number(end)`. It should use a per-week tier, not retroactive (4.2).
4. `rates.rates_for` uses `revisions[-1]`. It should use the revision in force on the week's first day, the receipt date or the dispatch date (3.1, 3.2). This covers the receipt `fee` too.
5. The receipt is billed at `"out"` with no fee. It should be `fee` once plus `pallets x in` (after-hours per pallet on a non-working day, fee unchanged), and only for a **receipt**, meaning `pallets >= 1` (2.1, 5.1, 5.2).
6. `Calendar.is_out_of_hours` is weekend-only. It should also cover holidays (2.3, 5.2).
7. `storage.peak` is a daily maximum. It should be the maximum on the first days of billed weeks, or 0 when there is none (4.5).
8. `surcharge_on` floors. It should round half-up on billed storage (1.3, 6.2).

Already correct and to be kept: dispatch x pallets; skipping entries below 1 in handling (5.3); `billed_storage` (4.4); amount and total (6.3); the section 7 layout.

## Part 1: findings

**F-A (no defect; legitimate trap): return timing.**
2.2 gives the next-day rule only to "a dispatched pallet", and 2.1 defines "A dispatch is an entry of one pallet or more". The timing of a return is therefore not governed and keeps today's `<=`. The natural global `<=` to `<` fix, prompted by the first symptom in the instruction, is wrong for returns.
Counterexample W6: received 06-01 with 10 pallets; +5 on 06-02; -3 on Mon 06-08, a week start. On-hand on 06-08 is 8 by the rule and 5 under a uniform `<`. Storage is 4200 versus 3900.
It is drawn in the authority's defined terms, and I found no competing positive sentence. Fine.

**F-B (no defect; legitimate trap): a zero-pallet arrival gets no receipt fee.**
2.1: "A receipt is an arrival of one pallet or more". 5.1: "A receipt dated within the period is billed the receipt fee (`fee`) once". The natural fix, `fee + pallets*in` inside `if start <= received <= end`, charges the fee to a 0-pallet lot.
Counterexample W7: `pallets` 0, received Wed 06-03, fee 1000. Handling is 0 by the rule and 1000 under the natural fix.
Today's retained calculation gives the same 0 (0 x rate, and today's code has no fee).

**F1 (polish): the no-guard example could be misread against F-B.**
The instruction says "Add no exception, clamp or guard for inputs the schedule does not provide for, such as pallet counts of nought or below". F-B needs a `pallets >= 1` test for the fee. That test is a condition written into the rule sentence (2.1), not a guard. A solver who over-reads the instruction might still drop the test.
The phrase "inputs the schedule does not provide for" is also odd: 1.4 does provide for 0-pallet lots and negative entries. It means "has no rule for".
Suggested wording: "... such as the timing of pallets taken back into stock".

**F2 (polish): 1.2 says "a handling rate is in cents per pallet moved", but `fee` is per receipt** (README, 5.1). 1.4 counts "four handling rates". Cosmetic.

**F3 (polish): the example job exercises neither trap.** BH-0921's -2 falls on Tue 06-16, which is not a week start, and there is no 0-pallet lot. That is acceptable, since visible examples need not cover every case, but note it for fuzz and test coverage.

**Checked, with no defect found:**
- Every range has a floor and a ceiling: `pallets` 0–1000, entries -1000..1000 on distinct dates with cumulative bounds, fee inside "every rate 0–100,000".
- Rounding has one site (1.3).
- Ordering and types are in section 7.
- The left-open list matches 1.4.
- There is no instruction-silent case that an authority sentence positively governs. The only silence left is return timing, and nothing competes with it.
- I found no ambiguity with a two-reading counterexample.

## Witnesses

One revision effective 2026-01-01, storage [[null,100]], fee=1000, in=10, out=20, after_hours=50, minimum 0, surcharge 0, period June 2026, unless noted. Fields: weeks / peak / storage / handling / surcharge / amount.

| # | Input | Expected |
|---|---|---|
| W1 | Received Mon 06-01, 10 pallets; +10 on Mon 06-08 | 2 / 10 / 2000 / 1000+100+200 = 1300 / 0 / 3300 |
| W2 | Period 06-01..06-28; received Wed 06-03, 1 pallet | 4 / 1 / 400 / 1010 / 0 / 1410 |
| W3 | Revisions 01-01 [[3,100],[2,200],[null,300]] and 06-20 [[3,1000],[2,2000],[null,3000]]; received 05-18, 1 pallet | 5 / 1 / 100+200+200+3000+3000 = 6500 / 0 / 0 / 6500 |
| W4 | Storage 0; revisions 01-01 (fee 1000, out 20) and 06-20 (fee 9999, out 40); holiday Fri 06-19; received 06-19, 5 pallets; +3 on Mon 06-22 | 2 / 5 / 0 / 1000 + 5x50 + 3x40 = 1370 / 0 / 1370 |
| W5 | Period 06-01..06-07; rate 400, minimum 1050, 5%; received 06-01, 1 pallet | 1 / 1 / 1050 / 1010 / 53 / 2113 |
| W6 | Received 06-01, 10 pallets; +5 on 06-02; -3 on Mon 06-08 | 5 / 10 / 10+8+8+8+8 = 4200 / 1000+100+100 = 1200 (the return is not billed) / 0 / 5400. Uniform `<`: 3900 / 5100. |
| W7 | Minimum 5000, 10%; received Wed 06-03, 0 pallets; a 0 entry on 06-10 | 0 / 0 / 0 / 0 / 0 / 0. Fee on a 0-pallet lot: handling 1000. |
| W8 | Minimum 5000; received 05-20, 10 pallets; +10 on Mon 06-01 | 0 / **0** (4.5; the old code gives 10) / 0 / 200 / 0 / 200 |
| W9 | Received Wed 05-27, 10 pallets; +4 on Tue 06-02 | 4 / 6 / 2400 / 80 / 0 / 2480 |
| Ex | `examples/small-job.json` | total **222454** on my reference; the shipped code gives 212614 |

No guesses were needed. Every witness follows from a governed rule or from the single, uncontested return-timing silence.

## Part 2: solver-path screen

**A) Pre-mortem.** A strong solver would map the symptoms to defects 2–8 and patch them quickly: anniversary weeks, per-week tier and revision, fee plus `in`, holidays, peak with 0, half-up. It would then write its own reference and diff-fuzz.

Where it goes wrong:
1. **`on_hand`.** The first symptom ("shipped out on the day a storage week begins escape that week") invites a global `<=` to `<`. Only a solver that stops to ask "when do *returned* pallets come back?", notices that 2.2 speaks only of dispatched pallets, and applies the keep-today's-calculation rule keeps `<=` for negatives. I would expect roughly half of strong solvers to miss this. It is also invisible to their own reference, because they encode the same reading.
2. **The fee.** A solver who adds the fee inside the existing "received in period" branch without re-reading 2.1's "one pallet or more" bills fees on 0-pallet lots. This is more likely to be caught, since the definition sits next to the dispatch one, and a solver writing a ≥1 test for dispatches tends to mirror it.

Self-verification: differential fuzzing against its own reference is blind to both. Only reading the definitions saves it.

**B) Scores** (5 = strongly resists)
- reference_unreachable: **2**. About 80 lines, fully derivable.
- authority_incomplete_for_grading: **1**. I found no ambiguity.
- hidden_state_not_closed_form: **1**.
- restraint_traps: **3**. Two legitimate sites count:
  1. Return timing: kept `<=` inside the `on_hand` aggregate that the day-of-dispatch repair forces the solver to rebuild. It is an unlabelled subtype (a negative entry) excluded only by the chain "dispatch = entry of one pallet or more".
  2. No fee for a 0-pallet arrival: inside the receipt-billing branch that the `in`/fee repair forces the solver to rebuild, excluded by "receipt = arrival of one pallet or more".

  The peak-0 rule counts zero, because the condition is written into the rule sentence.
- fuzz_blind_spot: **3**. Returns on a week-start day and 0-pallet lots inside the period are corners that self-fuzz reproduces with the solver's own reading.

**C)**
- self_verification_resistance: **3**
- prediction: **resists** (I expect at least one of two solvers to miss the return-timing restraint, the fee restraint, or both).
- confidence: medium-low. Both traps are one careful reading of 2.1 away, so a pair of very careful solvers could collapse it.
- decisive_reason: the contract is now clean, and the only thing between a strong solver and a full solve is noticing that 2.1 defines receipts and dispatches as "one pallet or more". That leaves same-day return timing (inside the `on_hand` fix everyone must make) and the fee on 0-pallet arrivals ungoverned or excluded. Self-tests cannot surface either.
