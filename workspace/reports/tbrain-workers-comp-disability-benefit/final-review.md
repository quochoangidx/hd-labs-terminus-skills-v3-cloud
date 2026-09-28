# Final review: tbrain-workers-comp-disability-benefit (reviewer E)

Snapshot reviewed: `workspace/tasks/tbrain-workers-comp-disability-benefit/`, covering instruction.md, task.toml, environment/, solution/ and tests/.
- `instruction.md` and `environment/` are byte-identical to the r3 contract packet (`diff -r` is clean). The r3 contract review therefore stands: every value has exactly one defensible answer.
- I did all scratch work in my session scratchpad. No task file was modified.

## Verdict: accept-with-fixes

The contract, the reference and the harness are sound:
- The oracle scores 1 and the unfixed package scores 0 (23/23 vs 2/23 tests).
- My independently written reference reproduces every sealed expectation, including both differentials.

Two wrong implementations of the preserved step for weeks under 1,000 cents still score 1 (F1), and some graded jobs sit outside what manual 1.4 describes (F2). Both fixes belong in `solution/jobgen.py` followed by a reseal. Nothing requires a change to instruction.md or environment/.

## What I ran

1. I built `environment/` and `tests/` locally. I applied `solution/solve.sh` in the environment image, copied `/app` into a fresh container of the verifier image with `--network none`, and ran `tests/test.sh`.
   - **Oracle:** 23 passed, reward 1.
   - **Unfixed package:** 21 failed, reward 0.
2. I wrote a scratch reference with 19 single-edit mutants and checked each against every sealed family, using the same comparison and differential assertions as the verifier.
   - The baseline matches every sealed file.
   - 17 of the 19 mutants are rejected by at least one family. They are:
     - a threshold of more than 2,000 instead of 2,000 or more
     - shifting every line, corrections included
     - dropping corrections
     - flooring the average weekly wage
     - dividing by the paid weeks
     - row selection strictly before the injury date
     - the newest row
     - flooring the rate
     - applying 3.5 through two thirds of the wage instead of the wage itself
     - clamping up to the minimum
     - retroactive days only from more than 14 days
     - flooring the total-disability amount
     - a partial-week threshold of more than 1,000
     - two thirds for every week
     - flooring the partial benefit
     - removing the partial cap
     - paying nothing for low weeks
   - The two survivors are F1.
3. I confirmed both survivors on the real package through the real verifier: each scores **reward 1**.

## Findings

### Tests, solution and task.toml (fix here)

**F1 (should-fix). The kept step for weeks under 1,000 cents is only half tested: its cap and its rounding are never checked.**
- **Citation:** instruction ¶2, "stays exactly the calculation today's code makes". Today's code is `min(ratio_of(loss, (3,5)), rate)`, and `ratio_of` rounds half up.
- **Mutant A: the cap is dropped for low weeks.** This is a natural restructure when the solver splits the branch:

  ```python
  total += min(benefit, rate) if earned >= PARTIAL_WEEK_FROM else benefit
  ```

  Result: **23/23, reward 1.**
- **Mutant B: the low-week share is floored.**

  ```python
  wage_loss(aww, earned) * 3 // 5
  ```

  Result: **23/23, reward 1.**
- **Why A survives:** every low-week job uses the OPEN table with a maximum of 400,000. `low_partial_weeks` and the differential say outright that "the cap does not bind", and for an uncapped rate 3/5 of the loss is always below 2/3 of the average weekly wage. The generated and limits families carry no low weeks by design.
- **Why B survives:** all 7 low weeks in `low_partial_weeks` happen to have 3 x loss mod 5 in {0, 1, 2}. The differential compares a difference of exactly 597 cents (earnings of 0 vs 995), which cancels any rounding.
- **Failing input for A:** table max 70,000; 13 week's-pay lines of 200,000, giving aww 200,000 and rate 70,000; one partial week earning 0. The contract gives tpd 70,000; mutant A gives 120,000.
- **Failing input for B:** aww 100,001, week earning 0. The contract gives 60,001 (60,000.6 rounded half up); mutant B gives 60,000.
- **Fix, in `jobgen.families()` and then `seal.py`:** add to `low_partial_weeks` one claim against a table whose maximum binds, for example max 70,000 with weekly wages of at least 150,000 and earnings [0, 500]. Also add at least one low week whose 3 x loss mod 5 is 3 or 4. The existing trap-input gating accepts both.

**F2 (should-fix). Some graded jobs pay several week's-pay lines on one payday, which manual 1.4 does not describe.**
- **Citation:** 1.4, "The payroll pays a week's wages in one line on the payday after the week ends". Corrections are the only lines the manual lets share a payday.
- **Affected claims:**

  | Family | Claims affected | Cause |
  |---|---|---|
  | `average_weekly_wage` | 5 of 5 | `wages.append(payday_line(weeks[-1], g.pay()))` adds a second week's pay for the last paid week |
  | `weeks_pay_threshold` | 2 of 4 | The two "last"-edge claims have the edge line of 2,000 plus the regular base[-1] line on the same payday |
  | `limits_claims` | 1 of 6 | The 120-line claim is 120 identical lines of 500,000 spread over 13 paydays, about nine per week |

- **Contract-valid alternative wrongly at risk:** an implementation that relies on 1.4, taking one week's pay per paid week or collapsing identical register rows, fails these families. That reliance is arguably an added guard, so the risk is low. But the instruction's list of open inputs does not cover these jobs either, so the tests grade inputs the authority never describes.
- **Fix, in jobgen:**
  - `average_weekly_wage`: make the second line on a payday a mid-base correction under 2,000 cents; corrections off the base-period edges are trap-free.
  - "last"-edge claims in `weeks_pay_threshold`: use `weeks=base[:-1]`.
  - The 120-line claim: reach 120 lines with at most one week's pay per payday plus corrections on mid-base paydays. Keep one 500,000 line to hold the top figure.

  Then reseal.

**F3 (polish). task.toml prose overstates the low-week coverage.**
`verification_explanation` says the low weeks sit in their own test and that "Fourteen wrong submissions each fail their own test". That is true for the two over-repairs named there, but not for F1's mutants. Update the sentence once F1 is fixed, and add both mutants to the listed mutant set. The rest of the prose matches the code and patch: the defect list, the two kept behaviours, the harness description, and the limits reached.

**F4 (polish). The rounding of `aww` has no dedicated named test.**
1.1 applied to the /13 in 3.3 is witnessed only incidentally. My floored-aww mutant fails 18 families, so coverage is strong. Only the "one named test per rule" framing is slightly inexact; no change is needed.

### instruction.md and environment/ (listed separately)

None needed.
- F2 could alternatively be fixed by loosening 1.4 to allow several week's-pay lines per payday. That is **not** needed and would reopen the contract, so fix the jobs instead.
- I found no promise in the instruction without a discriminating test, and no assertion that fails to trace to a visible sentence. Every coverage item in instruction ¶3 appears in a named family: every weekday, the day a row takes effect and years before the newest row, no wage lines, lines on paydays more than a year before the injury, corrections, 1 and 500,000 cents, average weekly wages above the maximum and below the minimum, one-day periods, twelve periods, exactly fourteen days, and partial weeks earning 0, a few dollars, more than the average weekly wage, or none. The two harness-only tests guard the stated driver promise and the verifier state.

## Checklist summary

- **(1) Coverage.** Every manual rule has a discriminating named family: 2.2 threshold, 3.1 arrears, 2.3, 3.3 (including no wages), 3.4, the maximum and minimum, 2.4 at the day before, the day of and after a change, 3.5 at 44,999 and 45,000, 2.5, 2.6, 4.1 at 13, 14 and 15 days, 4.3 at every remainder, 5.1 cap, 2.8 at exactly 1,000, 2.7, and 6.1 order and keys. The kept steps are covered except for F1.
- **(2) Sound Verifier.**
  - Rejections: all 17 non-F1 mutants are rejected, and a tampered driver fails `test_submitted_driver_unchanged`.
  - Contract-valid alternatives accepted: keys are compared as a set, key order is free, integers are checked strictly (bool excluded), and float or Fraction rounding is safe because no quotient can end in exactly half a cent. Claims and wage lines are shuffled at run time, which the README allows.
  - The only wrongly-at-risk alternative is the F2 case.
- **(3) Correct reference.** `model.py` never imports the package, and `fix.patch` makes the same eight repairs as the model:
  - a line of 2,000 cents or more moves back one week; a smaller line keeps its payday's week
  - the average weekly wage divides by 13
  - the fraction becomes 2/3
  - the rate row is the one in force on the date of injury
  - a wage below the minimum is the rate
  - the waiting period is 3 days
  - both ends of a period count
  - the total-disability amount rounds half up

  Low weeks keep 3/5, rounded half up and capped at the rate. Both the model and the patched package agree with my independent reference on every sealed job.
- **(4) Harness.** The design isolates the candidate on every point I checked:
  - `/tests` and `/logs/verifier` are closed (0700); the verifier's driver is `os.replace`-d onto the documented path, and `/app` is chowned to root and made unwritable.
  - The candidate runs as uid 65534 via `setpriv --no-new-privs` in its own session with `python3 -I -S`. The shipped copy runs as uid 65533 in a 0700 directory, and the ROSTER digests and counts are pinned.
  - The reward is written only on pytest rc 0 plus a `cmp` of the driver. `test_candidate_cannot_read_verifier_state` passed in my run.
- **(5) Determinism.**
  - `RELABEL_SEED` is drawn from `os.urandom`, but a correct package passes under every seed: the names stay within 24 characters, and the shuffles are ones the README allows. Failures print the seed.
  - The expectations are sealed with fixed seeds.
  - The run took under 1 s against a 1500 s budget.
- **(6) task.toml.** The metadata is consistent. Only F3 needs a change.
- **(7) Style.** The test names map to rule numbers, the docstrings are accurate, and the failure messages carry the family, job, claim and key. No issues.

## Recheck (after the repair batch)

**Scope.** `instruction.md` and `environment/` are still byte-identical to the r3 packet. `solution/fix.patch` and `solution/model.py` produce the same Oracle as before. The ROSTER and every sealed family were regenerated.

**Runs.** I rebuilt both images and ran the verifier in a separate container with no network:

| Submission | Result | Reward |
|---|---|---|
| Oracle | 23/23 passed | 1 |
| Unfixed package | 21 failed | 0 |
| F1 mutant A (low week uncapped) | 1 failed (`test_week_below_1000_cents_keeps_todays_share`) | **0** |
| F1 mutant B (low week floored) | 1 failed (same test) | **0** |

My independent reference still matches every sealed expectation, including the new single-job low-week differential, which I checked against the shipped package. All 19 of my scratch mutants are now rejected; previously 17 were.

**F1: closed.**
- `differential-low_partial_weeks` now holds four single jobs, and both new behaviours are graded:
  - Two jobs use a table max of 80,000 with an average weekly wage of 150,000, so the rate sits at the maximum. They include weeks earning 0, 2 and 612, where 3/5 of the loss (90,000 and just under) exceeds the rate. This is the same situation as my failing input A.
  - Two jobs use an average weekly wage of 80,001 with the rate at the row minimum of 60,000. They include weeks earning 0, 135, 215, 795 and 858, where 3 × loss mod 5 is 3 or 4. The week earning 0 gives 48,000.6, which rounds to 48,001; this is my failing input B.
- `low_partial_weeks` also fails both mutants.
- The differential's premise holds: on every one of these jobs, the shipped package and the manual agree on the average weekly wage and the rate, so the shipped partial amount is the correct expected value.

**F2: closed.**
- No sealed claim, in any family including both differentials, has two lines of 2,000 cents or more on one payday.
- The 120-line limits claim is now 13 week's-pay lines of 500,000 plus 107 corrections. It passes `within_limits` and the check that no job carries a trap input, so the corrections sit off the base-period edges.
- `average_weekly_wage` now adds a mid-base correction instead of a second week's pay.

**F3: closed.** `verification_explanation` now accurately describes:
- the capped and the three-or-four-fifths low weeks
- the single-job differential and its premise
- the "at most one line of a week's wages on a payday" property (true of the data, confirmed by scan)
- the composition of the 120-line claim (13 + 107, confirmed)
- twelve 400-day periods and 104 partial weeks (confirmed)
- the two added over-repairs, among the sixteen wrong submissions and 26 mutants

I could not independently enumerate all 26 mutants. The ones I reproduced behave as stated.

**New problems: none blocking.**
- **Polish.** The sentence "Every graded claim pays at most one line of a week's wages on a payday" follows "Every graded job is checked against the section 1 limits", so it reads as if the verifier checks it. Only `seal.py` and the data guarantee it; the verifier doesn't assert it. Either add the assertion to `load()` or reword it as "is built to pay". This is optional.
- Otherwise the prose is coherent with the task, the other metadata is unchanged and consistent, and I found no overstatement.

**Recheck verdict: accept.**
