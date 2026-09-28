# Contract review r2: tbrain-climate-observer-monthly-summary (reviewer D)

Scope: `contract-review-packet-r2/instruction.md` and `environment/` only. Compared with r1, only
`docs/observer-handbook.md` changed. The instruction, README, driver, example, Dockerfile and `src/` are all
byte-identical. I checked the witnesses against a scratch reference I wrote from the handbook.

## Status of r1 findings

| r1 | Status | Why |
|---|---|---|
| F1 (blocking): which day an accumulated amount is credited to | **Closed as blocking.** A residual should-fix remains (F1' below). | 1.3 now says an accumulated amount holds the precipitation of "two or more" observation days. 2.4 says a day's precipitation holds "exactly one". So 3.3 does not reach an accumulated amount. 3.4 "Every reading is credited to one day" rules out R3 (dropping it). The instruction's keep-today sentence then leaves it on its form day, which is R2. |
| F2 (should-fix): joint null clause for highest/lowest | **Closed.** | Section 6 now gives the null condition for each pair separately. |
| F3 (should-fix): `mean` for an incomplete month | **Closed.** | 2.8 limits the "standard means" to complete months, so 4.3 applies only there. Section 6 says "`null` only for a month in which no day has a mean temperature". That leaves the instruction's keep-today figure (the mean of the daily means) as the only authority. |
| F4 (polish): 1.4 "No other figure is rounded" against the rounded kept figure | **Closed.** | 1.4 now covers figures "the summary (section 6) gives to tenths", and section 6 gives `mean` as "a temperature to tenths". |
| F5 (polish): float exactness | **Closed.** | Section 6 now requires the JSON number "whose decimal value is the figure", with examples. |

## Part 1: contract review

### Package defects the repair must fix

1. **3.1/3.3 morning crediting.** At hour 0-11, a day's maximum and a day's precipitation go to form day − 1.
   `next` then lands on day N, and form day 1 falls outside the month (3.4). The package credits everything to
   the form day (`crediting.py`). The fix covers single-day amounts and T only. An accumulated amount stays on
   its form day (see F1').
2. **4.4 degree days.** Each day's exact mean is rounded half-up to the whole degree, and HDD/CDD are totalled per
   day. The package sums (max+min) and rounds once (`temperature.degree_days`).
3. **4.3 / 2.8 monthly mean.** For a complete month: half_up((mean_max + mean_min) / 2), using the rounded 4.1
   values. The package averages the daily means. For an incomplete month the package's current figure has to be
   **kept**, but computed from the corrected crediting.
4. **4.5 thresholds.** `>= 90.0`, `<= 32.0`, `<= 32.0`, `<= 0.0`. The package uses strict comparisons
   (`threshold_days`).
5. **5.3 thresholds.** `>= 0.10`, `>= 1.00`. The package uses `>` (`heavy_days`).
6. **4.2 ties.** The latest day wins, for highest and for lowest. The package keeps the first (`extreme`).
7. **5.4 ties.** The latest day wins. The package keeps the first (`greatest_day`).
8. **1.2 / 5.1 traces.** A trace counts as nought, and 5.1 totals only "every amount". The package counts T as
   1 hundredth (`entries.hundredths`).

### Findings

**F1' (should-fix): the accumulated-amount answer is reachable, but only through a fallback the instruction words
for "figures", not for crediting days.**
Citations:
- 2.4: "an amount or a `T` that holds the precipitation of exactly one observation day"
- 1.3: "it holds the precipitation of every observation day since the gauge was last read, two or more of them"
- 3.4: "Every reading is credited to one day."
- The instruction: "Wherever no rule applies, the summary keeps the figure the package works out today".

3.4 promises that an accumulated amount is credited to *some* day but never says which. The day comes out only
if the solver reads "the figure the package works out today" as reaching the crediting day, not just a summary
value. A competing reader applies 3.3 to it "by analogy", since 3.4 makes it a credited reading and 3.3 is the only
precipitation crediting rule. That reading is R1, and it is also the strong expert instinct: the observation day
ends at the morning observation, so the rain belongs to the day before.

Counterexamples:
- **W6:** hour 7, form days 5-6 `A`, form day 7 `0.50`. R2 gives `greatest_day` 06-07. R1 gives 06-06.
- **W7:** hour 7, days 29-30 `A`, `next` `0.40`. R2 gives `precip` 0.0 and `greatest` null. R1 gives 0.4 on 06-30.

I rate it should-fix rather than blocking. The definition chain (1.3 → 2.4 → 3.3 scope) plus the instruction's
"to nothing beyond them" does point one way. The fix: one handbook sentence stating that an accumulated amount is
credited to its form day at every hour, or equivalently a clause in 3.3 excluding it. That turns the trap from
inferred into stated, and it does not reduce its difficulty for a solver who skims.

**F6 (polish): trace after `A`.**
1.5 lets an `A` be followed by `T`. 1.3 speaks only of "the amount" at the next reading, so it is unclear whether a
`T` there is an accumulated amount. Either way it is not a day's precipitation, and 5.1 totals only amounts, so no
output changes (W10). No action needed. I note it only because a solver may spend time on it.

**F7 (polish): collision on one credited day is resolved by 5.1.**
At a morning station an accumulated amount (kept on form day d) and the next single-day amount (shifted from d+1
to d) land on the same day. 5.1 "total of every amount" makes the result a sum (W9). This is governed and not a
defect. Worth knowing for graders: a crediting rewrite that assigns instead of adding loses rain.

Other checks with no defect found:
- Hour boundaries: 0-11 is morning, and noon and midnight are explicit.
- Minima go to the form day at every hour (3.2).
- Rounding of negatives is explicit, half going to the higher value.
- Every numeric range has a floor and a ceiling.
- Station order is explicit.
- The instruction's silent classes (outside 1.5, bad `days` length, malformed entries, non-forms) match 1.5's
  "for no others". No handbook sentence governs any of them.
- Day-mean rounding for degree days is still unambiguous. No rule gives the day mean to tenths, so it goes exact
  straight to the whole degree.

### Witnesses (checked against my reference; R2 is the r2 contract reading)

| # | Input (anything not listed is 60.0/40.0/0.00) | Expected output | Guessed? |
|---|---|---|---|
| W1 | 2024-04, hour 7, form day 10 max 91.0, `next` 90.0/10.0/0.72 | highest 91.0 on 04-09; days_max_90 2; days_min_0 0; precip 0.72; greatest_day 04-30 | no |
| W2 | 2023-02, hour 17, every day 70.0/58.9 | heating_dd 28 (exact 64.45 → 64); mean 64.5; today 15 | no |
| W3c | 2024-01, hour 17, days 1-6 M/30.1, day 7 80.0/M | complete false; lacking_max 6; mean_max 60.8; mean_min 38.0; mean **50.0** (keep-today), not 49.4, not null | no (now governed by 2.8 + section 6 + instruction) |
| W4 | 2024-06, hour 18, base 50.0/20.0; d3 90.0/32.0, d6 32.0/0.0, d21 90.0/0.0 | days_max_90 2, days_max_32 1, days_min_32 30, days_min_0 2; highest 90.0 on 06-21; lowest 0.0 on 06-21 | no |
| W5 | 2024-06, hour 18, all T; d4 0.10, d11 1.00, d16 1.00 | precip 2.1; precip_days 3; _10 3; _100 2; greatest 1.0 on 06-16 | no |
| W6 | 2024-06, hour 7, d5-6 A, d7 0.50 | precip 0.5; precip_days 1; greatest 0.5 on **06-07** (the natural fix gives 06-06) | slight (F1') |
| W7 | 2024-06, hour 7, d29-30 A, `next` 0.40 | precip **0.0**, precip_days 0, greatest null. Hour 17 gives the same | slight (F1') |
| W8b | 2099-02, hour 17, mins -11.0 except day 1 -9.6 | mean_min -10.9 (-10.95 rounds up); lowest -11.0 on 02-28 | no |
| W9 | 2024-06, hour 7, d6 A, d7 0.50 (acc.), d8 0.30 | day 7 credited 0.80: precip 0.8; precip_days 1; _10 1; greatest 0.8 on 06-07 (R1 gives 2 days, greatest 0.5 on 06-06) | slight (F1') |
| W10 | 2024-06, hour 0, d1-2 A, d3 T | precip 0.0; precip_days 0; greatest null (today 0.01 / 1 day) | no |

Unlike r1, W6, W7 and W9 all have one answer now (R2). The only uncertainty left is the F1' wording.

## Part 2: solver-path screen

**A) Pre-mortem.** A strong solver maps the instruction's symptom list onto defects 1-8. All of them are named
("morning … turn up against the following day", degree days, "off … by a tenth or two", the exact thresholds,
"matched later", traces). It fixes them in about an hour, reusing `half_up`. It then writes a reference from the
handbook and fuzzes against it.

The two places it plausibly goes wrong:
- **Accumulated amounts at morning stations.** The symptom sentence invites shifting *all* precipitation. Only a
  solver who reads 2.4's "exactly one" against 1.3's "two or more", and who takes the instruction's "to nothing
  beyond them" literally, keeps them on the form day. This trap needs no single-case recall; it needs literalism
  against physics. I expect a careful Opus 5 or GPT-5.6-class solver to notice it about half the time. The
  rewritten 2.4 and 1.3 are conspicuous: they are the only places the handbook stresses "exactly one" and "two or
  more".
- **Incomplete-month `mean`.** Section 6 now forbids null, so a solver has to choose a figure. Some will apply
  4.3's average to non-standard means (49.4 in W3c) instead of keeping the daily-mean figure.

Double rounding in degree days is a smaller risk. Self-fuzzing catches none of these, because the reference
shares the solver's reading.

**B) Scores** (5 = strongly resists)
- reference_unreachable: **2**. The reference is small and closed-form, written from the handbook.
- authority_incomplete_for_grading: **1**. Residual F1' is a wording defect to fix, not a point.
- hidden_state_not_closed_form: **1**.
- restraint_traps: **3**. Two sites count:
  - Accumulated amounts are excluded from 3.3 only through the definition chain 1.3 → 2.4. This sits inside the
    crediting aggregate the repair forces the solver to rebuild, and it covers within-month and month-end cases
    (W6/W7/W9).
  - The incomplete-month `mean` is excluded from 4.3 through the defined term "standard means" (2.8), and must keep
    today's figure inside `monthly_mean`, which the repair also rebuilds.

  The first sits against strong expert instinct. It passes the 0/8 screen only because the chain is now explicit
  and there is no competing positive enumeration. If F1' is not fixed, a grader could fairly call it a defect.
- fuzz_blind_spot: **3**. Both traps and the day-mean double rounding are invisible to a solver fuzzing against its
  own reference. Only rereading the handbook finds them.

**C) Verdict**
- self_verification_resistance: **3**
- prediction: **borderline, leaning resists.** Both solvers fully solve it only if both catch the
  accumulated-amount exclusion *and* the incomplete-month keep-today. I estimate each at about 0.5-0.7 per solver.
- confidence: low-medium
- decisive_reason: every other defect is named in the symptom list and falls quickly. Whether two solvers both
  clear the task depends almost entirely on the accumulated-amount restraint, which is now authority-determined but
  runs against physical intuition. It rests on an instruction fallback worded for "figures" rather than crediting
  days (F1').
