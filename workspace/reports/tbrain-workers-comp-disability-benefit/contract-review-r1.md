# Contract review r1: tbrain-workers-comp-disability-benefit (reviewer E)

Scope: I read only `instruction.md` and `environment/` (Dockerfile, .dockerignore, README, manual TD-7, driver, `src/tdbenefit/*`, sample job). I built the witnesses below with a small hand reference in a scratch directory outside the repo.

## Defects visible to the agent (legacy vs manual)

In the legacy code I found these departures from the manual. Each one is governed by an explicit manual sentence.

1. `RATE_FRACTION = (3, 5)`, but 3.4 and 5.1 say two thirds.
2. `row_in_force` returns the newest row, but 2.5 and 3.4 call for the row in force on the date of injury.
3. When AWW < min the code clamps up to the minimum, but 3.5 says rate = AWW.
4. `WAITING_DAYS = 7`, but 2.7 sets 3.
5. `period_days` leaves out one end of each period, but 2.6 counts both ends.
6. `rate * paid // 7` floors, but 1.1 and 4.3 round half up.
7. There is no full-time /13 branch, but 3.3 requires one.
8. Friday lines are credited to the week they were paid in, but 2.2 and 3.1 credit them to the week before.
9. The partial benefit has no cap at the weekly rate, but 5.1 caps it.

Each of these has a clear authority sentence.

## Part 1: Findings

**F1 (should-fix). Non-Friday lines are placed in a week only through the silence clause, and a second reading is plausible.**
The manual never says which week a pay-outside-the-payroll line counts toward. 3.1 covers only "A week's pay counts toward the payroll week whose work it pays", and 2.2 limits "a week's pay" to the payroll's line. Yet 3.2 totals "the wage lines that count toward the weeks of the base period", which implies that every line counts toward some week. Three readings follow:
- (a) Silence clause: keep today's calendar week, so the line counts toward the week that holds the day it was paid. I think this is the intended reading.
- (b) Literal manual-only: nothing makes a bonus count toward any week, so it is excluded.
- (c) Natural "fix everything" rewrite: `week_ending(day) - WEEK` for every line, the same shift as payroll.

Counterexample (the sample job): the Wed 2025-01-22 line of 25,000.
- (a) AWW = 1,414,391/13 = **108,799**.
- (b) AWW = 1,389,391/13 = **106,876**.

Second counterexample (W5 below): a Saturday 2024-12-14 line of 13 cents and a Monday 2025-03-10 line of 1,000, with injury 2025-03-12.
- (a) AWW = 100,001.
- (c) The Saturday line drops out, the Monday line enters, and AWW = 100,077.

The instruction's precedence sentence does make (a) the governing answer. It would help to add one sentence to the instruction or the manual confirming that the governed/silent line runs along the defined term "week's pay". Otherwise (b) stays a defensible literal reading.

**F2 (should-fix). The part-time divisor is legacy, and a competing figure sits next to it.**
Part-time AWW is silent, because 3.3 defines only the full-time AWW. Today's code divides base wages by `len({week for week,_ in in_base})`, which counts weeks with *any* credited line, bonus-only weeks included. A solver rebuilding `average_weekly_wage` for 3.3 has to compute "weeks with a week's pay" (2.4) anyway, and will be tempted to reuse that count as the divisor, reading it as "using the manual's own figures". The instruction's phrase "using the manual's own figures wherever those feed into it" does not settle whether the divisor is a manual figure.

Counterexample W2: injury 2025-03-12. Friday lines on 02-28, 03-07 and 03-14 of 40,000 each, plus a Wed 2025-02-05 bonus of 5,000.
- Legacy divisor 4: AWW = **31,250**, and since that is below the min of 35,500, rate = **31,250** under 3.5.
- Week's-pay divisor 3: AWW = **41,667**, rate = **35,500**.

This is the main restraint site. I would add a clarifying clause, or accept it as a trap: the definitional chain (3.3 is limited to full-time, and the divisor belongs to the legacy computation) is present.

**F3 (polish). The precedence sentence in the instruction is hard to parse.**
The sentence is "for such an input this comes ahead of everything else in this paragraph, and every other step the input passes through follows the manual". "Input" is used to mean a computation step inside a claim, not a claim. A reader could take it to mean that a part-time claim is computed entirely the legacy way: the 3/5 fraction, the newest row, the 7-day wait.

Counterexample: W2 under whole-claim legacy gives rate = max(ratio 3/5 of 31,250 = 18,750, newest-row min 37,200) = 37,200, against 31,250 under the step-wise reading. The second clause does rule this out, but "an input that none of the manual's rules speaks to" would be clearer if it said "a figure" or "a step".

**F4 (polish). The full-time count is left implicit when a base week holds only a bonus.**
2.4 counts weeks that have a "week's pay", so bonus-only weeks do not count toward the 10. That follows from the defined terms and is determinate. W6 shows 10 one-cent Friday weeks plus a 500,000 bonus, which gives full-time and /13 = 38,462. If one Friday is removed, it becomes part-time with the legacy divisor 10 (9 pay weeks plus the bonus week), not 9. This is fine as written, and I list it only as the boundary a grader should cover.

**Checked and clean:**
- **Numeric ranges:** every one has a floor and a ceiling (1.3–1.6, dates 2016–2035).
- **Rounding:** covered by 1.1. Exact half cents cannot arise from /3 or /7; they can from /13 or /n, and there 1.1 says half up.
- **Rounding order:** `min(round(2/3·loss), rate)` and rounding after the cap give the same result, because the rate is an integer.
- **Output:** order and keys are pinned by the README and the instruction.
- **Boundaries:**
  - Retro at exactly 14 days (4.1): 3 retro days, 14 paid.
  - AWW equal to the minimum: 3.5 says "below", and both routes give the minimum.
  - Partial earnings equal to AWW: 2.8 says "reach", so the loss is 0.
- **Silence clause vs manual text:** I found no manual sentence that positively governs a case the instruction calls silent. The silent sites (non-Friday crediting and the part-time AWW) are marked out with the defined terms "week's pay" and "full-time worker".

## Witnesses (computed by hand from the manual, checked with a scratch reference)

All use rates `[{2024-07-01, max 142100, min 35500}, {2025-07-01, max 148900, min 37200}]`.

| # | Input sketch | Expected statement | Guess? |
|---|---|---|---|
| W1 | Sample job (injury Wed 2025-03-12; 13 Friday lines in base after the shift; the Wed 01-22 bonus of 25,000 in base; disability 03-13..04-06 plus 04-21..04-24; earnings 42,000 and 61,500) | aww 108799, rate 72533, waiting 3, retro 3, ttd_days 29, ttd 300494, tpd_weeks 2, tpd 76066, total 376560 | Bonus crediting relies on F1 reading (a) |
| W2 | Part-time: Fridays 02-28, 03-07, 03-14 of 40,000 each, bonus Wed 02-05 of 5,000; injury 2025-03-12; one-day period 03-13..03-13 | aww 31250, rate 31250 (3.5), waiting 1, retro 0, ttd_days 0, ttd 0, tpd 0, total 0 | Divisor relies on F2 (legacy 4) |
| W3 | 13 Friday lines of 400,000; injury 2025-08-06 (row 2); disability 08-07..08-19 (13 days); earnings week 2025-09-07 = 0 | aww 400000, rate 148900 (max), waiting 3, retro 0, ttd_days 10, ttd 212714, tpd_weeks 1, tpd 148900 (5.1 cap), total 361614 | No |
| W4a | 13 Friday lines of 36,000; injury Mon 2025-06-30 (older row); disability 07-01..07-07 plus 07-10..07-16 (14 days) | aww 36000, rate 35500 (min of row 1), waiting 3, retro 3, ttd_days 14, ttd 71000, total 71000 | No |
| W4b | Same, but injury 2025-07-01 (the row 2 effective day) | aww 36000, rate 36000 (3.5, below 37,200), ttd 72000, total 72000 | No |
| W5 | 13 Fridays of 100,000 in base (including Fri 03-14 paying the last base week), plus Fri 03-21 of 100,000 (pays the injury week, excluded), Sat 2024-12-14 of 13 (first base week), Mon 03-10 of 1,000 (injury week); injury 03-12; disability 03-12..03-15; earnings 100,001 and 200,000 | aww 100001, rate 66667, waiting 3, retro 0, ttd_days 1, ttd 9524, tpd_weeks 2, tpd 0, total 9524 | Sat/Mon crediting relies on F1 (a) |
| W6 | 10 Friday lines of 1 cent (the last 10 base weeks) plus Wed 2025-01-22 of 500,000; injury 03-12; disability 03-13..03-14; earnings week 03-23 = 1 | aww 38462 (full-time /13), rate 35500, waiting 2, retro 0, ttd_days 0, ttd 0, tpd 25641, total 25641 | No |

## Part 2: Solver-path screen

**A) Pre-mortem.** A strong solver reads the short manual and lines up each symptom sentence in the instruction with the nine legacy defects listed above. Each is a one-line fix: the fraction, row selection, the 3.5 branch, the waiting days, +1 on days, the half-up TTD, the /13 branch, the Friday shift, and the partial cap. It then writes a small reference that mirrors its own reading and fuzzes the package against it, which catches only slips, not misreadings. It could go wrong in two places:
- It writes the Friday shift as an unconditional `week_ending(day) - WEEK`, so bonuses move a week (F1 reading c).
- It rebuilds `average_weekly_wage` and divides part-timers by weeks with a week's pay instead of by weeks with any line (F2).

Both mistakes live inside functions the repair forces it to touch. However, the instruction explicitly says silent cases keep today's behaviour, and the minimal edit (`if day.weekday() == 4: shift`, adding the full-time branch in front of the existing divisor) keeps both automatically. A careful Opus 5 or GPT-5.6-class solver will usually take the minimal edit.

**B) Scores (1 = easy to solve, 5 = strongly resists)**
- reference_unreachable: **2**. The whole authority is closed-form and short, and a solver writes an exact reference quickly.
- authority_incomplete_for_grading: **2**. The silent sites resolve through the precedence clause. F1 and F2 are defensible second readings, not holes, but they should be tightened.
- hidden_state_not_closed_form: **1**. Nothing is hidden, and every figure is arithmetic on the job.
- restraint_traps: **2**. There are two counted sites:
  - Non-Friday crediting, inside `credit_lines`, which the Friday fix forces the solver to rebuild.
  - The part-time divisor, inside the AWW aggregate, which the 3.3 branch forces it to rebuild.

  Both rest on defined-term chains ("week's pay" and "full-time worker"). The 3.5 branch and the 5.1 cap are written into their rule sentences and count zero. The legacy code sits right there as a hint, which weakens both traps.
- fuzz_blind_spot: **3**. The grader's jobs exercise bonus lines and part-timers heavily, so a misreading would fail many claims. The solver's self-fuzz cannot expose it, because its reference shares its reading.

**C)**
- self_verification_resistance: **2**
- prediction: **collapses** (both of two solvers fully solve)
- confidence: 0.65
- decisive_reason: The instruction lists every governed bug as a symptom, each fix is a one-sentence manual rule, and the two restraint sites are kept by the minimal edit that a careful solver makes by default.
