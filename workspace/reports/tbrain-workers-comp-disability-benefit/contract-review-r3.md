# Contract review r3: tbrain-workers-comp-disability-benefit (reviewer E)

Scope: `contract-review-packet-r3/instruction.md` and `environment/` only. `diff -r` against r2 shows three changes:

1. Instruction paragraph 2 has a new preservation sentence: "Whatever the package works out, or does with an item, that no rule of the manual reaches stays exactly the calculation today's code makes, with the package's own constants at the values they have today; only those inputs of that calculation that the manual itself settles take their manual values."
2. The README `tpd_weeks` line now reads "the number of weeks in the partial earnings".
3. Manual 1.1 no longer has the half-up clause. It now reads "rounded to the nearest cent".

The code, the manual's other sections, the driver and the sample are unchanged.

## Part 1: Findings

**No blocking and no should-fix findings.**

**P1 (polish). Manual 1.1 has no tie rule, and none is needed.**
- **Citation:** "the result is rounded to the nearest cent."
- **The governed divisions** are /13 (3.3), x2/3 (3.4, 5.1) and x paid/7 (4.3). Their fractional parts are k/13, k/3 and k/7, none of which can equal 1/2.
- **The preserved division** is the legacy 3/5 for weeks earning under 1,000 cents. Its fractional parts are k/5, which cannot equal 1/2 either.

So there is no counterexample: no input within section 1 produces a tie. I note it only as a trap for future edits. If a divisor of 2, 4 and so on is ever added, the tie rule must come back.

**P2 (polish). The constants clause names "the package's own constants", but `RATE_FRACTION` is one shared constant used by two governed sites and one silent site.**
The instruction is now unambiguous: the silent site keeps `(3, 5)`. The rate and partial-disability-week sites take the manual's two thirds, because the manual itself settles them in 3.4 and 5.1. A solver must therefore split the constant.
- **Wrong edit:** set `RATE_FRACTION = (2,3)` globally. W4 then gives tpd 198,668 and total 293,907.
- **Correct:** tpd 185,401 and total 280,640.

This is a restraint trap with an explicit authority sentence, not an ambiguity. I list it as polish only because the trap is now signposted strongly enough that most careful solvers will catch it.

### Rechecks

**r2 F1 (the fraction for weeks under 1,000 cents): closed.**
- The benefit for such a week is something "no rule of the manual reaches". 2.8 excludes the week from partial disability, and 5.1 prices only weeks of partial disability.
- It therefore "stays exactly the calculation today's code makes": `min(half_up(loss x RATE_FRACTION), rate)`.
- The constant stays "at the values they have today", which is (3,5).
- Its inputs take manual values: the average weekly wage (3.3), the rate (3.4/3.5), and the wage loss (2.7, which the manual defines for any week).
- The two-thirds reading is now contradicted in the instruction's own words. **W4: tpd 185401 is the unique answer.**

**r2 F2 (README vs 6.1 on `tpd_weeks`): closed.**
The README now matches 6.1: `tpd_weeks = len(earnings)`. In W2 it is 3 and in W7 it is 1, and each is unique.

**r2 F3 (what the preservation clause covers on the wage path): closed.**
- "does with an item" covers crediting a correction line to a week. That is the item-level act the manual leaves unspecified: 3.2 says only that the line counts toward "one payroll week".
- It keeps today's calculation, `week_ending(paid day)`.
- The base-period total is still reached by 3.2, so the reading that keeps all of today's crediting has no footing.
- Shifting corrections like a week's pay has no textual support, because 2.2 and 3.1 limit the shift to "a week's pay", which means 2,000 cents or more. **W3: aww 100000 is the unique answer.**

**r2 F4 (half-up never exercised):** moot now that the tie clause is gone (see P1).

**r1 F1–F4:** all remain closed or moot, as reported in r2.

### Does every value have exactly one defensible answer?

**Yes.** For every claim within section 1:
- **Governed by the manual:** `aww`, `rate`, `waiting_days`, `retro_days`, `ttd_days`, `ttd`, `tpd_weeks`, and the benefit of each week of partial disability.
- **Governed by the preservation sentence**, which pins both the calculation and its constant:
  - which week a correction line counts toward
  - the benefit of each week earning under 1,000 cents
- `total` is the sum of the parts.

I found no case where two careful readings give different outputs.

## Package defects (legacy vs manual)

| # | Site | Fix | Section |
|---|---|---|---|
| D1 | `payroll.credit_lines` | A line of 2,000 cents or more counts toward `week_ending(paid) - 7 days`. A correction under 2,000 keeps `week_ending(paid)`. | 2.2, 3.1; 3.2 plus the preservation sentence |
| D2 | `payroll.average_weekly_wage` | Base wages / 13, rounded to the nearest cent. Today's code divides by the count of paid weeks, which raises ZeroDivisionError when there are no base lines. | 3.3, 1.1 |
| D3 | `rates.RATE_FRACTION (3,5)` | Two thirds for the weekly rate and for partial-disability weeks. Weeks under 1,000 cents keep 3/5. | 3.4, 5.1; preservation sentence |
| D4 | `rates.row_in_force` | Use the row in force on the date of injury. | 2.4, 3.4 |
| D5 | `rates.weekly_rate` | When the average weekly wage is below the minimum, the rate is the average weekly wage itself; today's code clamps it up to the minimum. | 3.5 |
| D6 | `disability.WAITING_DAYS 7` | 3 | 2.6 |
| D7 | `disability.period_days` | Add 1: both ends count. | 2.5 |
| D8 | `disability.total_disability` | `rate * paid / 7`, rounded to the nearest cent, not floored. | 1.1, 4.3 |

Already correct in today's code: the partial cap at the rate (5.1), and `tpd_weeks = len(earnings)` (6.1).

## Witnesses

These are unchanged from r2. The r3 edits change no arithmetic, and each witness is now unique.

| # | Expected |
|---|---|
| W1 (sample) | aww 106879, rate 71253, waiting 3, retro 3, ttd_days 29, ttd 295191, tpd_weeks 2, tpd 73506, total 368697 |
| W2 (no wage lines; earnings 0, 999, 1000) | aww 0, rate 0, waiting 1, ttd 0, tpd_weeks 3, tpd 0, total 0 |
| W3 (correction crediting at the base-period edges) | aww 100000, rate 66667, waiting 3, ttd_days 1, ttd 9524, total 9524 |
| W4 (earnings 0, 999, 1000, 100000) | aww 100000, rate 66667, ttd_days 10, ttd 95239, tpd_weeks 4, tpd 185401, total 280640 |
| W5 (rate at the maximum, partial benefit capped) | aww 400000, rate 148900, tpd_weeks 2, tpd 297800, total 297800 |
| W6a / W6b (older row vs the day row 2 takes effect) | rate 35500 / 36000, ttd 71000 / 72000 |
| W7 (corrections only) | aww 269, rate 269, waiting 2, tpd_weeks 1, tpd 0, total 0 |

## Part 2: Solver-path screen

**Pre-mortem.** A strong solver fixes D2 and D4–D8 immediately. It then has to hold two lines:
- **D1:** shift only lines of 2,000 cents or more. 2.2 defines "a week's pay" by amount, so this is well signposted.
- **D3:** the new sentence names "the package's own constants at the values they have today", which all but tells the solver that `RATE_FRACTION` must stay 3/5 at the silent site.

The likely failure is a solver that edits the shared constant first and never revisits `partial.py`. Its own reference would share that slip, so self-fuzzing would not catch it. A careful Opus 5-class solver that reads paragraph 2 closely will catch it.

**Scores (1 = easy to solve, 5 = strongly resists)**

| Measure | Score | Note |
|---|---|---|
| reference_unreachable | 2 | |
| authority_incomplete_for_grading | 1 | No remaining two-answer values |
| hidden_state_not_closed_form | 1 | |
| restraint_traps | 2 | Two sites inside rebuilt code: correction crediting in `credit_lines`, and the shared-constant split in the partial/rate aggregate. Both are now backed by explicit authority, which weakens them. |
| fuzz_blind_spot | 3 | Self-fuzzing shares the solver's reading. Grader jobs hit both sites on many claims. |

- self_verification_resistance: **2**
- prediction: **collapses**
- confidence: 0.6
- decisive_reason: Every value now has a single textual answer, and the only traps (the 2,000-cent crediting threshold and keeping 3/5 at the silent site) are named almost directly by 2.2 and the new constants clause, so a careful solver who reads paragraph 2 closely will solve both.
