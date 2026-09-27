# Contract review r1 — tbrain-medication-adherence-pdc

Scope: instruction.md + environment/ only (spec AM-2, README, shipped package, example, driver).

## Part 1 — Contract findings

1. **BLOCKING: `period` for an in-measure member has two readings.** README: "`period` (the number of days the PDC is taken over, an integer)". Spec 4.1: PDC divides by "the days of the treatment period that are not stay days". Reading A: `period` is the treatment period length (what the code computes as `span`, stays included). Reading B: it is the PDC denominator, which leaves out stay days. Counterexample: year 2024, fills 2024-01-01 and 2024-02-01 (drug D, class C, 30 days each), stay [2024-07-01, 2024-07-04]. A gives period 366; B gives 362. `pdc` is the same under both readings, so only the `period` key disagrees, and that key is compared exactly.

2. **BLOCKING: the 90-day window in rule 2.4 has two readings.** "the index date is at least 90 days before the last day of the measurement year". Reading 1 takes a date difference: year_end − index ≥ 90. Reading 2 uses rule 1.1 ("a span from one day to another includes both of them") and needs a span of at least 90 days, which is a difference ≥ 89. Counterexample (2023): index 2023-10-03 with a second fill on 2023-10-10. Reading 1 gives in_measure false (difference 89). Reading 2 gives true (span 90). The instruction promises "first fills on every day of the year", so this boundary is certain to be graded.

3. **BLOCKING: rounding and denominator for a class that is not reportable.** Spec 5.1 defines only "A reportable class's adherence rate". Rule 1.2 rounds half-up "an adherence rate". The instruction says silent figures keep "the way it does today", but it also lists "the class sheet divides by members who were never in the measure" as a symptom. Readings:
   (a) keep `100*adherent/members` with the code's floor rounding;
   (b) keep the `members` denominator but round half-up, on the grounds that 1.2 governs any rate;
   (c) divide by in_measure for every class. In that case 0/0 is possible, and the instruction forbids adding a guard.
   Counterexample: a class with 3 members, 2 in measure and adherent. (a) 66.6, (b) 66.7, (c) 100.0. The symptom sentence pulls hard toward (c). A contract of this kind needs a positive sentence here.

4. **SHOULD-FIX (close to blocking): PDC, covered and period for members not in the measure.** The treatment period (2.5) and covered days (3.4) exist only for members in the measure. 4.1 says "A member's PDC", without that restriction, but it is written in terms of the treatment period. Readings:
   (a) Keep the code's span, which is index to min(last covered day, year end), with stays left in the denominator. Round half-up because 1.2 covers "a PDC".
   (b) Same as (a) but with floor rounding.
   (c) Use the treatment-period formula for everyone. A member not in the measure because of a late index still has a well-defined span to year end.
   Counterexample: year 2023, one fill on 2023-11-01 for 30 days, stay [2023-11-05, 2023-11-06]. (a) period 30, covered 28, pdc 93.3. (c) period 61, stay-excluded denominator 59, covered 28, pdc 47.5. Under (a), whether stay days leave the denominator is also open: 28/30 vs 28/28.

5. **SHOULD-FIX: coverage of a fill over the supply limit.** Rule 3.1 governs only "A fill within the limit". Why would the spec define "within the limit" at all unless over-limit fills are treated differently? Readings: covers nothing, covers `days` in full, or keeps the code's `min(days,100)`. The silence rule settles it on the code's cap, measured from the start day set by 3.2. But the code today starts at `date+1` and never shifts fills, so "the way it does today" mixes one silent figure with a governed one. A second open question: does an over-limit earlier fill push later fills of the same drug? That depends on whether it "covers" those days (3.2). Counterexample: drug D, fills on 2024-01-01 (150 days) and 2024-02-01 (30 days). Cap reading: the second fill starts 2024-04-10. "Covers nothing" reading: it starts 2024-02-01. Derivable, but only through a definitional chain. The chain holds up, so this is a legitimate restraint site and not a defect.

6. **POLISH: exact half detection.** Rule 1.2 is clear, but its half cases can only arise with dyadic-friendly denominators, for example 1/16 = 6.25, which rounds to 6.3. Float `round()` uses banker's rounding and gives 6.2. This is well specified, so it is not a defect.

7. **POLISH: when a member's rows are listed.** "one object for each member and each class the member has a fill of" is clear, and so is the digits-before-letters ordering (ASCII). Class order is sorted over all codes. No issue.

8. **Preservation line:** the instruction's silence rule ("keeps working the figure out the way it does today, from the figures the specification does define") is sound in principle. Findings 1, 3 and 4 are cases where the spec partly speaks: 1.2 rounding and 4.1 "a member's PDC" reach toward cases the instruction treats as silent. The value such a case keeps is not uniquely derivable.

## Witnesses (hand-derived)

Unless noted, each fill is drug D, class C, with no stays.

- W1 (2023): fills 01-01 30d and 01-25 30d. The second fill shifts to 01-31..03-01. in_measure true, period 365, covered 60, pdc 16.4 (16.438), adherent false.
- W2 (2024, "stopped in March"): fills 01-10 30d and 02-09 30d. Coverage runs 01-10..03-09, 60 days. Period 01-10..12-31 is 357 days. pdc 16.8 (16.806). The code instead ends the period at the last covered day and gives 100-ish.
- W3 (2024, same-day pair): 03-03 30d, twice. in_measure false. The second fill shifts to 04-02..05-01. Period under the code's rule: 03-03..05-01 = 60 days, covered 60, pdc 100.0, adherent false. **Guessed** (finding 4).
- W4 (2023, one class, 16 members in measure, 13 adherent): rate 81.25 → 81.3. Floor gives 81.2.
- W5 (2024, 80.0 exact): an in-measure member with 365 non-stay treatment days and 292 covered. pdc 80.0, adherent true. The code says false because it tests `>`.
- W6 (2024, 79.96): 364 non-stay days, 291 covered (79.945 → 79.9). 292/365 = 80.0 and 291/364 = 79.945, so this is not a 79.96 case. A true 79.96 is 1999/2500, which the day ranges cannot produce. The instruction's "79.96 → 79.9" is illustrative only; 79.96 would round to 80.0.
- W7 (2023, index boundary): index 10-02 (difference 90). in_measure true under both readings. Index 10-03 differs between readings (finding 2). **Guessed.**
- W8 (2024, stay): W-finding-1 input. pdc = 100*60/362 = 16.574 → 16.6. period is 366 or 362. **Guessed.**
- W9 (non-reportable class, 3 members, 2 adherent): rate 66.6, 66.7 or 100.0. **Guessed** (finding 3).

## Part 2 — Solver-path screen

A) Pre-mortem. A strong solver reads the five symptoms and maps each to a fix:
- start at the fill date and add same-drug shifting;
- use a year-end period for in-measure members;
- count distinct dates plus the 90-day window;
- round half-up with Fraction or Decimal, and adherent at ≥ 80.0;
- use the in_measure denominator for reportable classes.

It then writes a Fraction-based reference and fuzzes it against its own code. Those self-tests share its interpretations, so they cannot catch the forks at findings 1–4. The likely failures are:
- the `period` key for in-measure members with stays (about 50/50);
- the non-reportable rate, where a solver will probably apply the in_measure denominator everywhere or keep floor rounding;
- the rounding and denominator of non-in-measure PDCs;
- the 89/90 boundary.

The over-limit cap is likely preserved by a careful solver, because the code visibly holds `min(days, SUPPLY_LIMIT)`.

B) Scores:
- reference_unreachable: 2
- authority_incomplete_for_grading: 4 (these are ambiguities and count as defects, not difficulty)
- hidden_state_not_closed_form: 1
- restraint_traps: 2 (the over-limit cap inside the rebuilt coverage routine; the non-in-measure period kept routing). The non-reportable rate fails the 0/8 screen because of the contrary symptom sentence, so it counts as a defect, not a point.
- fuzz_blind_spot: 3

C) Judgement:
- self_verification_resistance: 3
- prediction: resists, but for the wrong reasons (ambiguity)
- confidence: medium
- decisive_reason: the only discriminating sites left are ones where the authority does not fix the answer (`period` with stays, the non-reportable rate, the non-in-measure PDC, the 89/90 window), so failures would come from contract ambiguity rather than difficulty.

## Where the shipped package departs from the spec

1. coverage.py: fills start at `date + 1`, not the fill date (3.1).
2. coverage.py: no same-drug shifting of overlapping refills (3.2).
3. measure.in_measure: counts fills, not distinct fill dates, and has no 90-day window (2.4).
4. measure.period: ends at the last covered day, not at year end (2.5).
5. pdc.figures: stay days are not taken out of the denominator (4.1).
6. rounding.tenth: floors instead of rounding half-up (1.2).
7. pdc.figures: adherent uses `>` 80.0, not `>=` (4.2).
8. pdc.figures: adherent does not require in_measure (4.2). The fill-count test hides this.
9. classes.class_row: the rate divides by `members`, not in_measure, for reportable classes (5.1), and it floors.
10. Coverage is applied per class across drugs, which is correct, but shifting must be per drug inside the class. The code has no per-drug grouping.
