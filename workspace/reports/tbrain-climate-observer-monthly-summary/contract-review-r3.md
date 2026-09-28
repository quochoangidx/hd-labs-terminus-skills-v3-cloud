# Contract review r3: tbrain-climate-observer-monthly-summary (reviewer D)

Scope: `contract-review-packet-r3/instruction.md` and `environment/` only. Against r2, two things changed. The
handbook changed in 1.3, 1.5, 2.1, 2.4, 2.7-2.9, 3.4, 5.2 and section 6 `complete`. The instruction's fallback
sentence now reads "Wherever no rule applies to a reading or a figure, the summary keeps what the package does
with it today". The source, driver, README and example are unchanged. I checked the witnesses against my
scratchpad reference.

## Status of r2 findings

| r2 | Status | Why |
|---|---|---|
| F1' (should-fix): the fallback was worded for "figures", not for which day a reading is credited to | **Closed** | The fallback now covers "a reading". 3.3 reaches only "a day's precipitation" = "the catch of one observation day" (2.4). An accumulated amount is "the whole catch since the gauge was last emptied" (1.3), and 2.1 has the gauge emptied at each observation where it is read, so after an `A` the catch spans two or more observation days. No rule credits it, so the package's current treatment (its form day) is kept. The old 3.4 "Every reading is credited to one day" is gone, but the "a reading" fallback excludes the drop-it reading on its own. |
| F6 (polish): trace after `A` | **Closed** | 1.3 now says "The amount or trace … is an accumulated amount", and it counts as nought (1.2). |
| F7 (polish): two amounts landing on one day | **Closed / governed** | 5.1 "total of every amount credited to it". 5.2 is now phrased per amount and gives the same total. |

The restructure of 2.7-2.9 (gap count, well-observed month, standard means) is equivalent to r2's
"complete" definition. `complete` is true exactly when both lacking counts are ≤ 5.

## Part 1: contract review

### Package defects the repair must fix
1. **3.1/3.3 morning crediting** (`crediting.py`). At hour 0-11, a day's maximum and a day's precipitation (a
   single observation day's catch, including `T`) go to form day − 1. `next` lands on day N, and form day 1
   falls outside the month (3.4). The minimum stays on the form day (3.2). An accumulated amount stays on its
   form day.
2. **4.4 degree days** (`temperature.degree_days`). Each day's exact mean is rounded half-up to the whole degree,
   then HDD/CDD are totalled per day.
3. **4.3 / 2.9 monthly mean** (`temperature.monthly_mean`). For a well-observed month: half_up((mean_max +
   mean_min)/2), using the rounded 4.1 values. Otherwise the current daily-mean figure is kept, computed from the
   corrected crediting.
4. **4.5 inclusive thresholds** (`threshold_days`).
5. **5.3 inclusive 0.10 and 1.00** (`heavy_days`).
6. **4.2 latest day wins a tie** (`extreme`).
7. **5.4 latest day wins a tie** (`greatest_day`).
8. **1.2 / 5.1 trace counts as nought** (`entries.hundredths`, where T is 1 today).

### Kept values: does each have exactly one defensible answer?

- **Accumulated amount's day, including T and month-end `next`.** **Yes.**
  - The chain is 1.3 "whole catch since … last emptied" + 2.1 "reads and empties the gauge" + 2.4 "catch of one
    observation day". So 3.3 does not apply, and the instruction's "no rule applies to a reading" keeps the
    form-day crediting.
  - Dropping the amount is excluded by the same sentence: the package credits it today.
  - Crediting it by analogy with 3.3 has no textual hook now that 3.4's "every reading is credited" is gone.
  - What remains is expert physical instinct only. That is a trap, not an ambiguity.
- **`mean` of a month that is not well-observed.** **Yes.**
  - 2.9 gives such a month no standard means, so 4.3 does not apply.
  - Section 6 forbids null unless no day has a mean, and 1.4 rounds it to tenths.
  - That leaves today's figure, the half-up mean of the daily means.
- **`mean` null when no day has a mean.** **Yes.** Today's `monthly_mean` already returns `None` in that case,
  and section 6 says the same.
- **Amount entered after an `M` precipitation.** **Yes in substance, with one pedantic gap (F8).**

### Findings

**F8 (polish, bordering on should-fix): whether the observation after an `M` is a single-day catch.**
Citations:
- 2.1: at an observation "the observer … reads and empties the gauge".
- 1.2: "`M` when the observer has no reading".
- 2.4: "the catch of one observation day".

A literal reader can argue that at an `M` there was no reading, so the gauge was not emptied. The next amount is
then a two-day catch and, like an accumulated amount, stays on its form day. The intended reading, which I expect
and which is supported by 1.3 and 1.5 attaching accumulation only to `A` and keeping `A` and `M` separate, is that
it is an ordinary day's precipitation and shifts.

Counterexample W12: hour 7, form day 5 precip `M`, form day 6 `0.50`. The intended reading gives `greatest_day`
06-05. The literal reading gives 06-06, which is also what the package does today.

The instruction promises "days with no … precipitation reading", so this case is almost certainly in the tests.
The risk is that a solver who has just learned the `A` restraint over-applies it to `M`. The fix is one clause in
1.2 or 2.1: "an `M` observation still empties the gauge" or "only an amount entered after an `A` holds more than
one observation day".

**F9 (polish): "no rule applies to a reading" is literally false for an accumulated amount.**
Citation: "Wherever no rule applies to a reading or a figure, the summary keeps what the package does with it
today".

1.2, 1.5, 5.1 and 5.2 do apply to the accumulated amount. It is only its crediting that no rule reaches. Any
sensible reader applies the fallback to the unruled aspect. A pedant could say the fallback never fires and the
amount is uncredited, which gives `precip` 0.0 in W6. I don't count this as a real second reading: it would leave
5.1/5.2 with nothing to total. A wording tweak, "applies to a reading, or to what is done with it", would close it.

Other checks with no defect found:
- Hour boundaries.
- 3.2 minima.
- Rounding of negatives, half going to the higher value.
- Ranges have floors and ceilings.
- Station order.
- The null rules in section 6.
- JSON decimal exactness.
- The open classes (outside 1.5 and the others) match 1.5, and no handbook sentence governs them positively.

### Witnesses (checked against the scratchpad reference)

| # | Input (anything not listed is 60.0/40.0/0.00) | Expected | Guessed? |
|---|---|---|---|
| W1 | 2024-04, hour 7, form day 10 max 91.0, `next` 90.0/10.0/0.72 | highest 91.0 on 04-09; days_max_90 2; days_min_0 0; precip 0.72, greatest_day 04-30 | no |
| W2 | 2023-02, hour 17, every day 70.0/58.9 | heating_dd 28 (exact 64.45 → 64); mean 64.5 | no |
| W3c | 2024-01, hour 17, days 1-6 M/30.1, day 7 80.0/M | complete false; lacking_max 6; mean_max 60.8; mean_min 38.0; mean **50.0** | no |
| W4 | 2024-06, hour 18, base 50.0/20.0; d3 90.0/32.0, d6 32.0/0.0, d21 90.0/0.0 | days_max_90 2, days_max_32 1, days_min_32 30, days_min_0 2; highest 90.0 on 06-21; lowest 0.0 on 06-21 | no |
| W5 | 2024-06, hour 18, all T; d4 0.10, d11 1.00, d16 1.00 | precip 2.1; precip_days 3; _10 3; _100 2; greatest 1.0 on 06-16 | no |
| W6 | 2024-06, hour 7, d5-6 A, d7 0.50 | precip 0.5; precip_days 1; greatest 0.5 on **06-07** | no |
| W7 | 2024-06, hour 7, d29-30 A, `next` 0.40 | precip **0.0**, precip_days 0, greatest null. Hour 17 gives the same | no |
| W9 | 2024-06, hour 7, d6 A, d7 0.50 (accumulated), d8 0.30 | day 7 credited 0.80: precip 0.8; precip_days 1; _10 1; greatest 0.8 on 06-07 | no |
| W12 | 2024-06, hour 7, d5 precip M, d6 0.50 | greatest 0.5 on **06-05** | slight (F8) |
| W13 | 2024-06, hour 11, d4 A, d5 T (accumulated), d6 0.20 | precip 0.2; precip_days 1; greatest 0.2 on 06-05. Today: 0.21, 2 days, 06-06 | no |

## Part 2: solver-path screen

**A) Pre-mortem.** A strong solver maps the instruction's symptom list onto defects 1-8 and fixes them quickly.
Every one is named in a symptom sentence and has a clear handbook rule. It then writes a reference and fuzzes the
package against it.

The places it can go wrong:
- **Accumulated amounts at a morning station.** "An evening's rain turn up against the following day" invites
  shifting all precipitation. Keeping accumulated amounts on the form day requires following 1.3 "whole catch
  since last emptied" → 2.1 "empties the gauge" → 2.4 "catch of one observation day" and then applying the
  reading-level fallback. The r3 wording is less conspicuous than r2's "exactly one / two or more". The chain now
  runs through the physical description of the observation, which makes it easier to miss.
- **`mean` for a month that is not well-observed.** The solver must choose today's daily-mean figure over the 4.3
  average (49.4 vs 50.0 in W3c). Section 6's "null only …" rules out null.
- **Over-correction (F8).** Treating an amount after `M` as accumulated.
- **Double rounding** in degree days.

The solver's own fuzz cannot expose any of these.

**B) Scores** (5 = strongly resists)
- reference_unreachable: **2**. The reference is closed-form and small.
- authority_incomplete_for_grading: **1**. Every kept value has one answer. F8 and F9 are polish-level wording gaps.
- hidden_state_not_closed_form: **1**.
- restraint_traps: **3**. Two sites count, both inside aggregates the repair must rebuild, and both excluded only
  through a definition chain:
  - the accumulated-amount exclusion inside the rebuilt crediting (1.3/2.1/2.4 + fallback);
  - the non-well-observed mean inside the rebuilt `monthly_mean` (2.8/2.9 "standard means").

  Both pass the 0/8 screen: there is no competing positive enumeration in the authority, and the chains are
  explicit. The accumulated-amount site does face strong contrary instinct, but it now has an unambiguous textual
  answer.
- fuzz_blind_spot: **3**. Both restraints and the day-mean rounding are invisible to self-fuzzing.

**C) Verdict**
- self_verification_resistance: **3**
- prediction: **resists (narrowly).** A solve by both solvers needs both to catch the accumulated-amount exclusion,
  now hidden in the physical wording of 2.1/2.4, *and* the not-well-observed mean. I estimate roughly 0.5 per
  solver for the first and 0.7 for the second.
- confidence: medium-low
- decisive_reason: every kept value now has exactly one defensible answer. Resistance rests on two restraints
  reached by definition chains (catch/emptied, standard means) that run against natural fix instinct, and on a
  symptom list that invites over-correction. The only wording risk left is the `M`-then-amount case (F8), which
  would cut against the intended answer if a solver over-generalizes.
