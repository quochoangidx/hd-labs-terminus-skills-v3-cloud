# Contract review r2: tbrain-workers-comp-disability-benefit (reviewer E)

Scope: `contract-review-packet-r2/instruction.md` and `environment/` only. The driver is byte-identical to r1. I checked the witnesses with a scratch reference kept outside the repo.

## Changes since r1

- **Wage lines.** Every wage line is now paid on a Friday. A "week's pay" is now defined by amount: any line of 2,000 cents or more (2.2). Lines below that are "small corrections" (1.4).
- **Crediting.** 3.2 now says "Every wage line counts toward one payroll week."
- **Average weekly wage.** It is now always base wages divided by thirteen (3.3). The full-time/part-time split is gone, and a claim may have no wage lines at all.
- **Partial weeks.** A week of partial disability is now a week with earnings of 1,000 cents or more (2.8). 5.1 prices only those weeks, while 5.2 says every week in the partial earnings has a benefit.
- **Statement.** 6.1 now reports "the number of weeks in its partial earnings".
- **Legacy code.** The partial cap at the weekly rate is already in the legacy code.

## Package defects (legacy vs manual)

| # | Site | Legacy | Manual | Section |
|---|---|---|---|---|
| D1 | `payroll.credit_lines` | Every line goes to the week that holds the day it was paid. | A week's pay (a line of 2,000 cents or more) goes to the week before the Friday it was paid. Lines under 2,000 are not governed, so they keep the legacy week. | 2.2, 3.1 (3.2 plus the silence clause for corrections) |
| D2 | `payroll.average_weekly_wage` | Divides by the number of distinct paid weeks. This raises ZeroDivisionError when no line is in the base period. | Divides by 13, rounding half up. | 3.3, 1.1 |
| D3 | `rates.RATE_FRACTION = (3,5)` | 3/5 | Two thirds for the weekly rate and for weeks of partial disability. | 3.4, 5.1 |
| D4 | `rates.row_in_force` | Uses the newest row. | Uses the row in force on the date of injury. | 2.4, 3.4 |
| D5 | `rates.weekly_rate` | Raises the rate to the minimum when the average weekly wage is below it. | The rate is the average weekly wage itself. | 3.5 |
| D6 | `disability.WAITING_DAYS = 7` | 7 | 3 | 2.6 |
| D7 | `disability.period_days` | Leaves out one end of each period. | Counts both ends. | 2.5 |
| D8 | `disability.total_disability` | `// 7` rounds down. | Round to the nearest cent, half up. | 1.1, 4.3 |

Legacy behaviour that stays correct or is preserved:
- The partial cap `min(benefit, rate)` matches 5.1.
- `tpd_weeks = len(earnings)` matches 6.1.
- Weeks earning under 1,000 cents keep the legacy benefit `min(round(3/5 x loss), rate)` through the silence clause. See F1.

## Part 1: Findings

**F1 (blocking). The fraction for weeks earning under 1,000 cents has two defensible answers.**
- **Why the manual does not decide it:**
  - 5.2 says "Every week in a claim's partial earnings has a benefit".
  - 5.1 prices only "A week of partial disability", which 2.8 limits to earnings of 1,000 cents or more.
  - So the benefit for a week earning under 1,000 cents is a figure no rule covers. The instruction says such a figure "keeps coming out the way today's code works it out, from the manual's own figures wherever those feed into it".
- **The two readings:**
  - (a) Today's code multiplies by the literal constant `RATE_FRACTION = (3,5)`, fed with the manual's average weekly wage, wage loss and weekly rate. This gives `min(round(3/5 x loss), rate)`.
  - (b) `RATE_FRACTION` is commented in the code as "Share of the average weekly wage paid as the weekly rate". The manual fixes that share at "two thirds" and says so explicitly: "Some neighbouring states pay 60 per cent; this state pays two thirds". A reasonable engineer reads the share as a manual figure that feeds into the legacy computation, which gives `min(round(2/3 x loss), rate)`. This is also the natural edit: change the shared constant once.
- **Why the wording does not settle it:** nothing in the contract says a multiplier is or is not a "figure". The one place the manual uses the word (1.1, "A figure that no rule multiplies...") leans toward amounts, but only weakly.
- **Counterexample (W4):** average weekly wage 100,000, rate 66,667, earnings of 0, 999, 1,000 and 100,000.
  - (a) gives tpd 185,401.
  - (b) gives tpd 198,668.
  - The instruction says this class ("partial weeks earning nothing, a few dollars") is in every job, so the divergence is on many claims.
- **Screen verdict:** the domain word "two thirds" competes directly, the code comment points at (b), and expert instinct says "this state pays two thirds". This fails the 0/8 screen, so I count it as a contract defect, not a restraint point.
- **Fix:** name the legacy multiplier as the figure to keep, for example "for such a week the package keeps today's share of the wage loss", or give the week a manual rule.

**F2 (should-fix). The README key description contradicts manual 6.1 on `tpd_weeks`.**
- The README says `tpd_weeks`: "the number of weeks of partial disability". Under 2.8 that means only weeks earning 1,000 cents or more.
- Manual 6.1 says "the number of weeks in its partial earnings", which means every week listed.
- The manual wins ("Where the statement package and this manual disagree, the manual is right"). But the instruction also tells the agent to emit "exactly the keys the README lists", so the agent reads the README as the output contract.
- **Counterexample (W2):** earnings of 0, 999 and 1,000. 6.1 gives 3, the README gives 1.
- **Fix:** align the README text with 6.1.

**F3 (should-fix). How much the silence clause covers is unclear in the wage path.**
- The instruction scopes preservation to "a figure for which no rule of the manual covers the case in hand".
- For a correction line, 3.2 says it "counts toward one payroll week" but never says which. What is uncovered is a week assignment, not a statement figure.
- **The three readings:**
  - (a) The per-line reading: keep the legacy week for correction lines only. This is my intended reading.
  - (b) The whole figure: base-period wages are "a figure" whose case is not fully covered, so the entire legacy crediting is kept, unshifted weekly pay included.
  - (c) Over-extension: shift corrections like a week's pay.
- (c) has no textual support, because 3.1 and 2.2 limit the shift to "a week's pay", which is a defined term. Reading (b) is strained but literal.
- **Counterexample (W3):**
  - (a) gives average weekly wage 100,000.
  - (c) gives 100,154.
  - (b) moves every weekly line in time, and the result depends on the edge lines.
- **Fix:** add one sentence, for example "the week a correction counts toward stays as today's code assigns it".

**F4 (polish). The half-up rule is never exercised at a real half.**
The divisors are 13, 3, 5 and 7, so no quotient can end in exactly one half cent. The "exact half cent is rounded up" clause is harmless but never tested. This is not a defect.

**Checked and clean:**
- **Ranges:** every numeric range has both a floor and a ceiling. The ranges are 0–120 lines, 1–500,000 per line, periods of 1–12 and under 400 days, and earnings of 0–104 weeks and 0–500,000.
- **The 2,000-cent threshold:** it labels a week's pay by a condition written into the definition. This is determinate: exactly 2,000 is a week's pay and 1,999 is a correction.
- **The 1,000-cent threshold:** determinate in the same way. Earnings of exactly 1,000 make a week of partial disability.
- **A claim with no wage lines:** the average weekly wage is 0/13 = 0, and since 0 is below the minimum, the rate is 0 under 3.5. This is governed, and it retires the legacy divide-by-zero.
- **Boundaries** are stated explicitly:
  - average weekly wage equal to the minimum ("below")
  - earnings equal to the average weekly wage ("reach")
  - exactly 14 disability days
  - a one-day period
  - an injury on the day a row takes effect
- **Order and keys** are pinned by the instruction and the README.

**Does every value have exactly one defensible answer? No.**
- The `tpd` (and therefore `total`) contribution of weeks earning under 1,000 cents is split between 3/5 and 2/3 (F1).
- `tpd_weeks` has a README/manual conflict (F2). The manual resolves it, but the README remains a trap for the output key.
- Every other value (`aww`, `rate`, the day counts, `ttd`, and `tpd` from partial-disability weeks) has one answer, provided F3 is read per line.

## r1 findings: are they closed?

- **r1 F1 (non-Friday crediting): partly closed.** All lines are on Fridays now, and 3.2 "Every wage line counts toward one payroll week" removes the exclusion reading. The legacy-vs-shift choice for corrections remains. Under the defined term "week's pay" it now has one textual answer (legacy), so what is left is a restraint trap, not an ambiguity. The scope wording is still loose (new F3).
- **r1 F2 (part-time divisor): closed.** 3.3 always divides by 13.
- **r1 F3 (precedence sentence): closed on the whole-claim reading.** The new sentence says "every other figure of the same claim still follows the manual". The "figure" granularity issue is new F3.
- **r1 F4 (full-time count): moot.** The full-time concept is gone.
- **New issues:** F1 (blocking) and F2 are new in r2.

## Witnesses

All use the sample rates `[{2024-07-01, max 142100, min 35500}, {2025-07-01, max 148900, min 37200}]`.

| # | Input | Expected (per my reading) | Guess / alternative |
|---|---|---|---|
| W1 | Sample job: 13 week's-pay lines paid Fri 2024-12-20 to 2025-03-14 fall in the base, plus a 37-cent correction on Fri 01-24 (legacy week 01-26, in base). Disability 03-13..04-06 and 04-21..04-24. Earnings of 42,000 and 61,500. | aww 106879, rate 71253, waiting 3, retro 3, ttd_days 29, ttd 295191, tpd_weeks 2, tpd 73506, total 368697 | None. Shifting the correction also lands in base. |
| W2 | No wage lines. Injury 2025-03-12, one-day period 03-13. Earnings of 0, 999 and 1,000. | aww 0, rate 0, waiting 1, retro 0, ttd_days 0, ttd 0, tpd_weeks 3, tpd 0, total 0 | README reading gives tpd_weeks 1 (F2). |
| W3 | 13 lines of 100,000 paying the base weeks, plus a 1,999 correction on Fri 03-14 (injury week, so out), a 1-cent correction on Fri 2024-12-13 (first base week, so in), and a 2,000 week's pay on Fri 2024-12-13 (pays week 12-08, so out). Injury 2025-03-12, disability 03-12..03-15. | aww 100000, rate 66667, waiting 3, retro 0, ttd_days 1, ttd 9524, tpd_weeks 0, tpd 0, total 9524 | Shifting everything gives aww 100154, rate 66769, ttd 9538 (F3c). |
| W4 | 13 lines of 100,000. Injury 03-12, disability 03-13..03-25 (13 days). Earnings of 0, 999, 1,000 and 100,000. | aww 100000, rate 66667, waiting 3, retro 0, ttd_days 10, ttd 95239, tpd_weeks 4, tpd 185401 (60000 + 59401 + 66000 + 0), total 280640 | 2/3 for every week gives tpd 198668 and total 293907 (F1). |
| W5 | 13 lines of 400,000. Injury 2025-08-06 (row 2), one-day period. Earnings of 0 and 1,000. | aww 400000, rate 148900, waiting 1, ttd 0, tpd_weeks 2, tpd 297800 (both capped at the rate), total 297800 | None. The cap makes the fraction irrelevant here. |
| W6a | 13 lines of 36,000. Injury Mon 2025-06-30 (older row). Periods 07-01..07-07 and 07-10..07-16 (14 days). | aww 36000, rate 35500, waiting 3, retro 3, ttd_days 14, ttd 71000, total 71000 | None |
| W6b | Same as W6a, but injury 2025-07-01 (the day row 2 takes effect). | aww 36000, rate 36000 (3.5: below 37,200), ttd 72000, total 72000 | None |
| W7 | Only correction lines: 1,500 on Fri 03-07 and 1,999 on Fri 02-28, both counting in base. Injury 03-12, disability 03-13..03-14. Earnings of 500. | aww 269, rate 269, waiting 2, ttd 0, tpd_weeks 1, tpd 0, total 0 | README reading gives tpd_weeks 0. |

## Part 2: Solver-path screen

**A) Pre-mortem.** A strong solver maps the symptom paragraph to D1–D8. The easy fixes are D4–D8 and D2. The two decision points are:
- **D1:** it must shift only lines of 2,000 cents or more. An unconditional shift is the natural edit, but 2.2 names the threshold, so a careful reader gets it right. This is a real restraint site inside a function the fix forces it to rebuild.
- **D3:** it must fix the fraction for the rate and for partial-disability weeks while leaving 3/5 for weeks under 1,000 cents. The natural edit, `RATE_FRACTION = (2,3)` globally, silently changes those weeks too.

Whether that second outcome counts as "wrong" depends on F1. A solver that reads "the manual's own figures" as including the two-thirds share will defend 2/3 in good faith. Its own reference and fuzzing share its reading, so self-checks pass. It may also emit `tpd_weeks` per the README (F2).

**B) Scores (1 = easy to solve, 5 = strongly resists)**
- reference_unreachable: **2**. Everything is closed-form and short.
- authority_incomplete_for_grading: **4**. F1 is a genuine two-answer value on a heavily tested class, and F2 adds a README/manual conflict on a key. This is a defect, not difficulty.
- hidden_state_not_closed_form: **1**
- restraint_traps: **2**
  - The correction-crediting site in `credit_lines` counts: it sits in a rebuilt function and rests on a defined-term chain.
  - The 3/5 site for weeks under 1,000 cents does not count. It fails the screen because of the competing "this state pays two thirds" sentence and the code comment (F1).
  - The partial cap and the 3.5 branch are written into rule sentences and count zero.
- fuzz_blind_spot: **3**. Interpretive errors are invisible to self-fuzzing, but grader jobs hit them on many claims.

**C)**
- self_verification_resistance: **3**
- prediction: **resists** as graded, but mainly through the F1 ambiguity, not legitimate difficulty. Once F1 and F2 are fixed, I expect it to **collapse**: the only remaining trap is the 2,000-cent threshold, which is spelled out in 2.2.
- confidence: 0.6
- decisive_reason: The main thing likely to split solvers is whether the two-thirds share counts as one of "the manual's own figures" for weeks under 1,000 cents, and that is a wording ambiguity, not earned difficulty.
