# Contract review r1: tbrain-sales-commission-statement

Scope: `contract-review-packet-r1/instruction.md` and `environment/` only (plan, README, example, `src/commission/*`, driver, Dockerfile).

## What the plan changes in the code (my reading)

| Site | Today | Plan |
|---|---|---|
| bookings (3.2) | sum of order **values** | sum of rounded rep's shares (`rep_share`) |
| commission (4.1/4.2) | whole bookings at the single band reached, floored | marginal 800/1200/1600 bp bands, each rounded half-up |
| clawback, reversal (>=50,000) | age > 90 gives 0, else 800 bp | age > 120 gives 0, else 800 bp |
| clawback, courtesy credit (<50,000) | age > 90 gives 0, else 800 bp | no rule sets the amount, so today's calculation stays (90 days, 800 bp) |
| bonus, new-logo (first, value >=250,000) | share < 10,000 gives 0, else 300 bp | 300 bp of share, no floor |
| bonus, trial first order (<250,000) | share < 10,000 gives 0, else 300 bp | no rule sets the amount, so today's calculation stays (floor 10,000) |
| recovery (7.3) | `min(owed, total)` | `min(owed, total - draw)` |
| minimum payment (7.4) | 10,000 | 25,000 |

The traps come from `figures.py` sharing constants: `small_cents` feeds both `bonus_floor` (keep 10,000) and `minimum_payment` (becomes 25,000), and `window_days` feeds `clawback_age` for both reversals (becomes 120) and courtesy credits (keep 90).

## Part 1: contract findings

1. **should-fix: courtesy-credit age limit, 90 or 120.** Instruction: "keeps the exact calculation today's code makes, with every constant of the package at its value today; of that calculation's inputs, only the ones the plan itself sets may move." Plan 5.1 sets a 120-day age limit, but only for reversals. A reader who treats "the clawback age limit" as an input the plan sets will move it for courtesy lines too. Counterexample: a credit of 30,000 cents at split 100, raised in the quarter at age 100. Reading A (package constant stays at 90) gives 0. Reading B (the plan-set limit moves) gives 2,400. I lean towards A, because "every constant ... at its value today" is the more specific clause. Still, the "inputs ... may move" clause has no clear referent in any preserved calculation here, and it invites reading B. Fix: say which inputs are meant (for example, "the rep's share and the dates"), or delete the clause.

2. **should-fix: "new-logo bonus" wording and trial-order flavour work against the preservation ruling.** README: "`bonus`: the new-logo bonus". Plan 1.4: "a trial order: a few units bought to try the product before any real commitment." Both push an expert towards zeroing bonus lines on first orders under 250,000. The authority (6.2, "Every first order ... carries one bonus line", with no amount given for non-new-logo lines) plus the preservation paragraph say to keep today's 300 bp with the 10,000 floor. Counterexample: a first order with value 200,000 at split 100. The plan-plus-preservation reading gives bonus 6,000. The "new-logo bonus only" reading gives 0. The authority does decide this, but the competing label in the README is a contrary expert instinct written into the package's own docs. Rename the key description to "the first-order bonus" or similar.

3. **polish: whether the thresholds apply to the value or to the share.** Plan 2.3 says "a credit note of 50,000 cents or more" and 2.4 says "a customer's first order of 250,000 cents or more". Most readers will take the amount credited and the order value (1.4 and 1.5 name those fields), but bookings, bonus and clawback all work on shares. Counterexample: value 300,000 at split 3. The value reading makes it new-logo, so the bonus is 270. The share reading (9,000) makes it a trial order under the 10,000 floor, so the bonus is 0. Reversal case: amount 60,000 at split 50, age 100. The amount reading gives 2,400. The share reading makes it a courtesy credit past 90 days, so it gives 0. Fix: add "(its value)" and "(the amount credited)".

4. **polish: plan 1.6 contradicts 1.5 and the example.** 1.6 says "Every order a rep books ... falls between 45 days before the first day of the rep's quarter and 45 days after". 1.5 and the instruction allow a credit note's order to be booked up to 365 days before the credit note was raised. The example's credit note order was booked 2027-01-28 for 2027-Q2, which is 63 days before the quarter. Under a literal reading, credit notes on old orders fall outside section 1 and so are "left entirely open". This does not change a correct implementation, because no guard is allowed, but it muddies which ages the graded range covers (the true range is 0 to about 365 days). Fix: limit 1.6 to the orders in the rep's order list.

5. **polish: 5.2 and 6.2 "reach" the line but not its amount.** The instruction's test is whether "a figure ... that no rule of the plan reaches". 5.2 and 6.2 reach every clawback and bonus line by saying the line exists. A literal reader could argue the line is therefore reached, and that the plan leaves the amount of a courtesy or trial line undefined rather than preserved. The intended reading is clear enough (amount unset, so today's calculation stays), but the defined term the preservation test uses ("reaches") is not tied to "sets the amount".

6. **Checked and clean:**
   - Rounding authority: 1.1 says half-up, per share, with two-step rounding for share-of-share. Per-band rounding is in 4.2.
   - Ordering is given as job order.
   - Output keys and integer values are listed.
   - Every input range has a floor and a ceiling (the instruction repeats section 1).
   - Totals below nought are governed by 7.2, because the draw is at least 0.
   - "Total exactly on the draw" goes to 7.3.
   - A due exactly on 25,000 is paid ("25,000 cents or more").
   - Half-cent ties cannot occur for the 800, 1,200 or 1,600 bp bands or the clawback, because 8x, 12x and 16x can never end in 50 mod 100. They can occur for split shares (101 at 50 gives 51) and for the 300 bp bonus (share 250,050 gives 7,502).

## Grounded witnesses (hand-derived)

Unless a witness says otherwise, the rep has quarter 2027-Q2, draw 0, owed 0, carried 0, no credit notes, and orders dated inside the quarter.

1. **Example rep NE-0417.**
   - Result: bookings 6,135,000; commission 496,200; bonus 56,700; clawback 24,800; total 528,100; recovered 0; owed 0; paid 528,100; carried 0.
   - Bookings: 2,480,000 + 1,890,000 + 1,765,000. The 07-02 order is excluded.
   - Commission: 480,000 + 16,200.
   - Clawback: the credit note is 94 days old and a reversal, so 800 bp of 310,000 gives 24,800. Today's code gives 0.
2. **Example rep SW-0082.**
   - Result: bookings 2,430,000; commission 194,400; bonus 0; clawback 0; total 194,400; recovered 0; owed 230,600; paid 300,000; carried 0.
   - Owed: 125,000 + (300,000 - 194,400).
3. **Trial first order.** Input: quota 1,000,000, order [200000, 100, true]. Result: bookings 200,000; commission 16,000; bonus 6,000 (preserved); total 22,000; paid 0; carried 22,000. *Guess risk: finding 2.*
4. **New-logo order with a small split.** Input: quota 1,000,000, order [250000, 3, true]. Result: bookings 7,500; commission 600; bonus 225 (today 0); total 825; paid 0; carried 825.
5. **Half-up bonus.** Input: order [250050, 100, true], quota 10,000,000. Result: bonus 7,502; commission 20,004.
6. **Band split and rounding.** Input: quota 100,001, bookings 100,007 from one order at split 100, not first. Result: commission 8,000 + 1 = 8,001. Today's code gives 12,000.
7. **Three bands.** Input: quota 100,000, bookings 250,000. Result: commission 8,000 + 12,000 + 8,000 = 28,000.
8. **Clawback age boundaries.**
   - Reversal 50,000, split 100, age 120: 4,000.
   - The same reversal at age 121: 0.
   - Courtesy credit 30,000, age 100: 0. *Guessed (reading A of finding 1).*
   - Courtesy credit 30,000, age 60: 2,400.
9. **Partial recovery.** Input: quota 10,000,000, draw 300,000, owed 125,000, one order 4,375,000. Result: total 350,000; recovered 50,000; owed 75,000; paid 300,000; carried 0. Today's code gives recovered 125,000 and paid 225,000.
10. **Minimum payment and negative total.**
    - Carried in 24,999, nothing else: total 24,999; paid 0; carried 24,999.
    - Draw 0 and a reversal of 1,000,000 at age 10 as the only item: clawback 80,000; total -80,000; paid 0; owed 80,000; recovered 0; carried 0.

## Part 2: solver-path screen

**A) Pre-mortem.** A strong solver reads the plan against `figures.USES` and sees a mismatch per rule: bookings on value, a single band with floor rounding, the 90-day window, the 10,000 minimum, and recovery against the whole total. It writes a reference with marginal bands and fuzzes against it.

The quick fix edits `FIGURES` (`window_days` to 120, `small_cents` to 25,000). That breaks courtesy credits aged 91 to 120 and trial bonuses with a share between 10,000 and 24,999. The instruction's "every constant of the package at its value today" plus "Add no exception" is a loud tell, though. A careful solver splits the uses by type (reversal or courtesy, new-logo or trial) and keeps the old figures on the unreached branches.

The remaining failure modes:
- zeroing trial bonuses, because of the README's "new-logo bonus" label and the flavour in 1.4;
- moving the courtesy window to 120 under the "inputs the plan sets may move" clause.

Self-fuzzing against its own reference cannot catch either one, because both are reading errors.

**B) Scores (5 = strongly resists solving)**

| Axis | Score | Reason |
|---|---|---|
| reference_unreachable | 2 | The whole reference can be derived from the plan plus the old code. |
| authority_incomplete_for_grading | 2 | The 90-vs-120 fork (finding 1) and the value-vs-share wording (finding 3) are the only live ambiguities. |
| hidden_state_not_closed_form | 1 | |
| restraint_traps | 3 | Two valid sites: (a) trial first-order bonus lines, a bare unlabelled subtype excluded only by the 2.4 chain inside the bonus aggregate the solver rebuilds, with the 10,000 floor tied to the shared `small_cents`; (b) courtesy credit lines, an unlabelled subtype via 2.3 inside the rebuilt clawback aggregate, with the 90-day window tied to the shared `window_days`. Site (a) carries a contrary cue (README label), and site (b) is partly a contract defect (finding 1), so neither is a clean point. |
| fuzz_blind_spot | 3 | |

**C) Verdict**

- self_verification_resistance: 2
- prediction: collapses
- confidence: medium (about 60%)
- decisive_reason: The instruction names the shared-constant mechanism outright ("every constant of the package at its value today"), and the eight `USES` entries map one-to-one onto plan rules, so a careful Opus/GPT-class solver will decouple `bonus_floor`/`minimum_payment` and the reversal/courtesy windows. The only real resistance is the ambiguous 90-vs-120 courtesy fork, which is a defect, not difficulty.
