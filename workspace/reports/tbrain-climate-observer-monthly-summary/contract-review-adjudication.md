
## r1 adjudication (builder D, redesign 1/1, snapshot 931e61c6)

| Finding | Builder | Orchestrator | Repair |
|---|---|---|---|
| F1 blocking: accumulated amount R1/R2/R3 | accept | uphold | 1.3 no longer says "that day's precipitation" (`A` "in place of an amount"; the accumulated amount "holds the precipitation of every observation day since the gauge was last read, two or more of them"). 2.4 now defines a day's precipitation as "an amount or a `T` that holds the precipitation of exactly one observation day". 3.4 adds "Every reading is credited to one day", and 2.1 defines a reading as "a temperature, an amount or a `T` that the form enters". 5.1 now reads "the total of every amount credited to it". So R1 is out (3.3 moves only a day's precipitation), R3 is out (the amount is credited to one day and 5.1 totals every credited amount), and R2 follows (the day is unruled, so the package's form day stands). W6: greatest_day 06-07. W7: precip 0.0, greatest null. No sentence names the case. |
| F2 should-fix: joint null clause | accept | uphold | Section 6: "`highest` and `highest_day` are `null` for a month with no maximum credited, and `lowest` and `lowest_day` for a month with no minimum credited." |
| F3 should-fix: incomplete-month `mean` | accept | uphold | The bound moves out of the rule sentence. New 2.8: "A month's standard means are its mean maximum and its mean minimum (4.1), when the month is complete for temperature." 4.3: "A month's mean temperature is the average of its two standard means, to tenths." Section 6: "`mean`: … a temperature to tenths; `null` only for a month in which no day has a mean temperature (2.5)". Null for an incomplete month with paired days is excluded, 4.3 does not reach such a month (it has no standard means), and today's figure stands. |
| F4 polish: 1.4 vs kept rounding | accept | uphold | 1.4 now reads "A figure that this part or the summary (section 6) gives to tenths …". Section 6 gives `mean` to tenths, so the kept figure is rounded half up, which the package already does. |
| F5 polish: exact JSON numbers | accept | uphold | Section 6: the number "whose decimal value is the figure in tenths/hundredths … the figure is exact in tenths or hundredths and is written as that decimal". |
| F6: degree-day rounding is fair | agree | uphold | none |

Model semantics are unchanged: the model already took R2 and today's incomplete-month mean. Only comments, the Oracle's comments, `fix.patch` (regenerated) and the `solve.sh` table changed. The instruction is unchanged.

## Strengthening (the one allowed; after skeleton cycle-2 2/2 and contract r2; snapshot 85d0cab5)

Cycle-2 result: both runs quoted 1.3 "two or more", 2.4 "exactly one" and 3.4 "every reading is credited to one day" and kept T1. Both kept T2 through the 2.8 definition. The aim now is one quiet hop per trap, still with one answer.

| Item | Change |
|---|---|
| T1 1.3 | "…an accumulated amount: it holds the precipitation of every observation day since the gauge was last read, two or more of them." → "The amount or trace the observer enters when the gauge is next read is an accumulated amount: the whole catch since the gauge was last emptied." (This also closes F6: a `T` after `A` is covered.) |
| T1 2.1 | Adds ": the observer reads and resets the thermometers, and reads and empties the gauge." Drops "A reading is a temperature, an amount or a `T` that the form enters." |
| T1 2.4 | "an amount or a `T` that holds the precipitation of exactly one observation day, the one that ends at…" → "A day's precipitation is the catch of one observation day, entered at the observation that ends it." |
| T1 3.4 | "Every reading is credited to one day." is removed. |
| T1 5.2 | "the total of its days' credited precipitation" → "the total of every amount credited to one of its days". 5.1 stays "the total of every amount credited to it". |
| Reach rule (instruction, closes F1') | "Wherever no rule applies, the summary keeps the figure the package works out today, computed from…" → "Wherever no rule applies to a reading or a figure, the summary keeps what the package does with it today, worked out from…". Now the crediting of a reading is covered in so many words. |
| T2 2.7-2.9 | "2.7 complete for temperature … no more than five …" and "2.8 standard means … when the month is complete for temperature" are replaced by: "2.7 A month's gap count is the larger of the number of its days that lack a maximum and the number of its days that lack a minimum." / "2.8 A well-observed month is a month whose gap count is five or fewer." / "2.9 A month's standard means are the mean maximum and the mean minimum (4.1) of a well-observed month." 4.3 is unchanged ("A month's mean temperature is the average of its two standard means, to tenths."). Section 6 `complete`: "`true` for a well-observed month (2.8)". The word "complete" is left only in the key name. |
| F7 | No change (governed by 5.1's sum). |

T1 chain: 3.3 moves a day's precipitation, which is the catch of one observation day (2.4). The gauge is emptied at each observation (2.1), and an accumulated amount is the whole catch since it was last emptied (1.3), which spans the unread observation days as well. So 3.3 does not reach it, and the reach rule keeps the package's crediting (its form day). 5.1/5.2 total every credited amount, which excludes R3. `receipts/witnesses-w6-w10.json` (model): W6 0.5 on 06-07, W7 0.0 with null, W9 0.8 on 06-07, W10 0.0 with null. Each has one answer.

T2 chain: 4.3 → 2.9 standard means → 2.8 well-observed → 2.7 gap count → 2.6 lacking days. A month with a gap count of six or more has no standard means, so 4.3 does not reach it. Section 6 gives `mean` null only when no day has a mean temperature. The package's mean of daily means stands.

Model and Oracle semantics are unchanged; only comments changed. Departures are unchanged.

## r3 adjudication (builder D, phase 2; snapshot 80a54e90)

| Finding | Builder | Repair |
|---|---|---|
| F8 (polish, bordering should-fix): an amount after an `M` | accept | 2.1 now reads "…reads and empties the gauge, which is emptied even when its reading is lost and the form gives `M`." W12 (hour 7, day 5 `M`, day 6 0.50) has one answer: greatest_day 06-05. The witness is test_rule_3_3_morning_precipitation_on_the_day_before, and sweep mutant c12-lost-reading-starts-accumulation is killed on it. |
| F9 (polish): the reach rule's subject | accept | The instruction now reads "Wherever no rule applies to a reading, to what is done with it, or to a figure, the summary keeps what the package does with it today…" |

Also in this phase, the README line "`summarize(form)` returns the month's summary" became "the package the driver runs" (C1: no promise that no test grades). The T1 and T2 chains are unchanged.
