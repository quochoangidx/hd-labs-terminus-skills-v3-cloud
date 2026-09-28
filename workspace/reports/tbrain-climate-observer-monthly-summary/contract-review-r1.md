# Contract review r1: tbrain-climate-observer-monthly-summary (reviewer D)

Scope: `instruction.md` and `environment/` only (Dockerfile, README, handbook, `src/coopsum/*`,
`tools/coopsum_run.py`, `examples/two-stations.json`). I checked the witnesses against a small reference I
wrote in a scratch directory from the handbook. For the accumulated-amount case I ran it both ways, R1 and
R2, as described in F1.

## Part 1: contract review

### What the package gets wrong today (all are named in the instruction's symptom list)

1. Morning crediting. Today every max and every precipitation amount goes to its form day. Under 3.1 and 3.3,
   a morning (hour 0-11) max or precipitation amount goes to the day before. That includes `next`, which then
   lands on day N, and form day 1, which then falls outside the month.
2. Degree days. Today the package sums (max+min) and rounds once, at the end. Under 4.4 each day's
   *unrounded* mean is rounded half-up to the whole degree, and the per-day results are totalled.
3. Monthly mean. Today it is the mean of the daily means. Under 4.3 it is half_up((mean_max + mean_min)/2),
   using the 4.1 values after they are rounded, and it applies to complete months only.
4. Thresholds. Today `>`/`<`. Section 4.5 needs `>=`/`<=`, and so does 5.3 for 0.10 and 1.00.
5. Ties. Today the first day wins. Sections 4.2 and 5.4 need the latest day, for highest, lowest and greatest.
6. Traces. Today a trace counts as 1 hundredth. Section 1.2 makes it nought.

### Findings

**F1 (blocking): crediting of an accumulated amount has three defensible readings.**
Citations:
- 2.4: "A day's precipitation is the precipitation of one observation day, as entered at the observation that ends it."
- 1.3: "The amount the observer enters at the next observation at which the gauge is read is an accumulated amount: all the precipitation that fell since the gauge was last read."
- 1.3 also says: "the form enters `A` for that day's precipitation".
- The instruction: "Every rule of the handbook applies to exactly the readings, days and months that its own defined terms describe".

An accumulated amount is by definition not "the precipitation of *one* observation day". So:
- R1 (the natural expert reading): it is still the day's precipitation entered at that observation, and 3.3 shifts it
  to the day before at a morning station.
- R2 (the strict defined-terms reading plus "keeps the figure the package works out today"): 3.3 does not reach it.
  It stays on its form day, as the current `credit_precipitation` puts it, even at a morning station.
- R3 (also strict): nothing in section 3 credits it, and 5.1/5.2 total only *credited* precipitation. It
  drops out of `precip`, `precip_days` and `greatest` completely. This makes "keep today's figure" inapplicable,
  because 5.2 is a rule that does apply to `precip`.

Counterexample W6: hour 7, 2024-06, form days 5-6 = `A`, form day 7 = `"0.50"`, everything else `0.00`.
R1 gives `greatest_day` 2024-06-06. R2 gives 2024-06-07. R3 gives `precip` 0.0, `precip_days` 0 and `greatest` null.

Counterexample W7, the month-end case the instruction calls out ("at the end of a month as well as within it"):
hour 7, days 29-30 = `A`, `next.precip` = `"0.40"`.
R1 gives `precip` 0.4, `precip_days` 1 and `greatest_day` 2024-06-30. R2 and R3 give 0.0, 0 and null.

The instruction lists unread-gauge runs among the tested inputs, so this case is graded. The handbook needs one
sentence saying which day an accumulated amount is credited to, and whether it counts toward 5.3/5.4.
Otherwise the result depends on which reading the grader happens to take.

**F2 (should-fix): the null clause for `highest`/`lowest` in section 6 is joint where it should apply to each key separately.**
Citation: "`highest`, `highest_day`, `lowest`, `lowest_day`: … `null` for a month with no maximum, or no minimum, credited."
- Reading A: the highest pair is null when there is no max, and the lowest pair is null when there is no min.
- Reading B: all four keys are null when either is absent.

Counterexample: every `max` is `M` and the mins are present. Reading A gives `lowest` = the real value.
Reading B gives null. Section 4.2 defines each extreme on its own, which supports A, but section 6 should say "respectively".

**F3 (should-fix): the section 6 `mean` entry has no null or incomplete clause, and the only authority is outside the handbook.**
Citations:
- Section 6: "`mean`: the month's mean temperature (4.3)."
- 4.3: "A complete month's mean temperature …".
- The instruction: "Wherever no rule applies, the summary keeps the figure the package works out today".

For an incomplete month the only authority is the instruction's keep-today sentence, which gives the mean of the
daily means over days that have both readings, rounded. Rival readings are null (the NCDC practice) or applying
4.3 anyway. Counterexample W3c: 2024-01, hour 17, all days 60.0/40.0, except days 1-6 are max `M`/min 30.1 and
day 7 is 80.0/`M`.
- Keep-today gives `mean` 50.0.
- Applying 4.3 gives 49.4.
- Null gives null.

The instruction does close this, so it is not a defect. But it is the handbook's own "No other figure is rounded"
(1.4) that sits oddly with a kept figure that *is* rounded. See F4.

**F4 (polish): section 1.4's "No other figure is rounded" contradicts the kept incomplete-month mean.**
The kept figure is today's `half_up` to tenths. A strict reader could print the unrounded average instead.
Counterexample: an incomplete month whose daily-mean average is 50.04 prints 50.0 under the keep-today reading and
50.04 under the 1.4 reading. The instruction's wording ("keeps the figure the package works out today") favours
50.0. A clause saying so would close it.

**F5 (polish): "a JSON number equal to the figure in hundredths" is exact only when the value comes from an integer.**
A solver who totals floats gets 0.1+0.2 = 0.30000000000000004 and fails exact comparison. The contract implies
decimal equality, and a float-summing reader would still claim to meet it. The current int-then-`/100` path is safe.
Stating that the number must equal the decimal figure after parsing would help.

**F6 (not a defect, a legitimate trap): day-mean rounding for degree days is fully governed.**
Section 2.5 does not round the day mean, and 1.4 forbids rounding it, so 4.4 rounds the exact (max+min)/2
straight to the whole degree. A solver who first rounds to tenths gets it wrong. Counterexample W2: 70.0/58.9
gives an exact mean of 64.45, which rounds to 64, so HDD is 1 per day. Rounding to 64.5 first gives 65 and HDD 0.

Other checks with no defect found:
- The hour boundary is explicit: 0 through 11 is morning, and midnight and noon are both covered.
- Minima go to the form day at every hour (3.2).
- `next` crediting follows from 2.1, 3.1 and 3.4.
- Rounding of negatives is explicit, half going to the higher value.
- Every numeric range has a floor and a ceiling (1.5 and the instruction).
- Station order is explicit.
- The instruction's silent classes (outside 1.5, bad `days` length, malformed entries, non-forms) match 1.5's
  "for no others". No handbook sentence positively governs any of them.

### Witnesses (checked against my reference)

| # | Input (anything not listed is 60.0/40.0/0.00) | Expected output | Guessed? |
|---|---|---|---|
| W1 | 2024-04, hour 7, form day 10 max 91.0, `next` = 90.0/10.0/0.72 | highest 91.0 on 2024-04-09; days_max_90 2; precip 0.72; greatest_day 2024-04-30; days_min_0 0 (next min out of month); lacking_max 0 | no |
| W1b | same, hour 17 | highest_day 2024-04-10; days_max_90 1; precip 0.0; greatest null | no |
| W2 | 2023-02, hour 17, every day 70.0/58.9 | heating_dd 28, cooling_dd 0, mean 64.5 (today: heating_dd 15) | no |
| W3 | 2024-01, hour 17, days 1-3 M/30.1, days 4-6 80.0/M | complete true; mean_max 62.1, mean_min 38.9, mean 50.5 (today 50.0) | no |
| W3c | incomplete variant from F3 | complete false, lacking_max 6, mean 50.0 | yes (instruction keep-today, F3/F4) |
| W4 | 2024-06, hour 18, base 50.0/20.0; d3 90.0/32.0, d6 32.0/0.0, d21 90.0/0.0 | days_max_90 2, days_max_32 1, days_min_32 30, days_min_0 2; highest 90.0 on 06-21; lowest 0.0 on 06-21 | no |
| W5 | 2024-06, hour 18, all T; d4 0.10, d11 1.00, d16 1.00 | precip 2.1; precip_days 3; _10 3; _100 2; greatest 1.0 on 06-16 | no |
| W6 | 2024-06, hour 7, d5-6 A, d7 0.50 | R1: greatest_day 06-06; R2: 06-07; R3: precip 0.0, greatest null | **yes (F1)** |
| W7 | 2024-06, hour 7, d29-30 A, next 0.40 | R1: precip 0.4, greatest_day 06-30; R2/R3: 0.0, null | **yes (F1)** |
| W8b | 2099-02, hour 17, mins -11.0 except day 1 -9.6 | mean_min -10.9 (-10.95 rounds up); lowest -11.0 on 02-28 | no |

## Part 2: solver-path screen

**A) Pre-mortem.** A strong solver reads the handbook and maps each symptom sentence in the instruction to one
function. The list lines up one-to-one with the bugs: morning shift, degree days, monthly mean, inclusive
thresholds, latest ties, traces as nought. It rewrites `crediting.py` with an hour<=11 shift for max and precip,
reuses `half_up`, and fixes the comparisons. It then writes its own reference from the handbook and fuzzes the
package against it. Every governed bug falls within an hour.

The places it can still go wrong:
- **Double rounding in the day mean (F6).** Moderate risk, but a careful solver catches it by reading 1.4.
- **Incomplete-month `mean`.** It may print null or apply 4.3 despite the keep-today sentence.
- **Accumulated amounts (F1).** It will almost certainly take R1 and shift them with the rest of the precipitation.
  If the grader expects R2 or R3, both solvers fail on a contract defect rather than on real difficulty.

Its self-fuzz cannot catch any of these, because the reference shares the solver's reading.

**B) Scores** (5 = strongly resists)
- reference_unreachable: **2**. The reference is roughly 60 lines written straight from the handbook.
- authority_incomplete_for_grading: **1** for legitimate resistance. F1 is a defect, not a point, and must be fixed.
- hidden_state_not_closed_form: **1**. Everything is closed-form per day and per month.
- restraint_traps: **1**.
  - The incomplete-month mean counts zero, because its condition ("A complete month's …") is written into the rule sentence.
  - The R2/R3 accumulated-amount restraint fails the 0/8 screen: 1.3's "that day's precipitation" works against
    the definitional chain, and expert instinct runs strongly the other way. So it is a contract defect, not a point.
- fuzz_blind_spot: **2**. Day-mean double rounding is the only governed blind spot, and fuzzing with random tenths
  hits .x5 means often enough to expose it once someone rereads 1.4.

**C) Verdict**
- self_verification_resistance: **2**
- prediction: **collapses**, if the grader expects R1 for accumulated amounts. If it expects R2 or R3, both
  solvers fail, but only because of a contract defect.
- confidence: medium
- decisive_reason: every governed bug is named in the instruction's symptom list and has a one-sentence authority
  in the handbook. The only thing that could make solvers fail is the unresolved crediting of accumulated amounts,
  which is ambiguity rather than difficulty.
