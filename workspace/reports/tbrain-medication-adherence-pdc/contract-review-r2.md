# Contract review r2 — tbrain-medication-adherence-pdc

Scope: contract-packet-r2 instruction.md + environment/ only.

## r1 findings

1. **`period` meaning: CLOSED.**
   - README now says: "`period` (the number of days the covered days are divided by for the PDC, an integer)".
   - Spec 4.1 defines "period days", the treatment-period days that are not stay days.
   - W8 (2024; fills 01-01 and 02-01, 30 days each; stay 07-01..07-04) now has one answer: period 362, covered 60, pdc 16.6.
2. **90-day window: CLOSED.**
   - Rule 2.4 now reads "no later than 2 October of the measurement year".
   - An index of 10-02 is in the measure and 10-03 is not, in leap and non-leap years alike.
3. **Rate for a class that is not reportable: CLOSED.**
   - The spec is still silent, so the code's `100*adherent/members` stays.
   - Rule 1.2 now covers "every adherence rate the report gives", so it is rounded half-up.
   - The symptom now names "our statin class, one of the large ones", which only points at reportable classes.
   - 3 members, 2 of them adherent: rate 66.7. I found no competing reading.
4. **Members not in the measure: CLOSED.**
   - 4.1 is now written in terms of "period days", which exist only for members in the measure, so their PDC denominator is left to today's code.
   - Rule 1.2 covers "every PDC the report gives", so rounding is half-up.
   - The kept value is unique: see S2 below.
5. **79.96 note: CLOSED.** The instruction now says "a PDC of two thirds is reported as 66.6". Floor gives 66.6 and the spec gives 66.7, which is consistent.

## New findings

- **N1 (polish).** The PDC of a member not in the measure depends on the code's `min(max(covered), year_end)` over the *coverage set*. That set includes stay days and days of other drugs in the class. A solver might instead take the max over its stay-excluded covered days. Nothing in the text forces the coverage set, but "the way it does today" does. Counterexample: one fill on 2023-11-01 for 30 days, with a stay covering 11-29..11-30.
  - Coverage-set reading: last day 11-30, period 30, covered 28, pdc 93.3.
  - Stay-excluded reading: last day 11-28, period 28, covered 28, pdc 100.0.

  This sits in the sanctioned silence area, so it is a restraint site and not a defect.
- No other new ambiguity found. Every exact convention now has a sentence behind it:
  - rounding is half-up (1.2);
  - the threshold is 80.0 or more (4.2);
  - same-day order is file order (3.2);
  - list order and digit-before-letter order are in the README;
  - ranges have both floor and ceiling (1.3 and the instruction).

## Figures the silence sentence leaves to today's code

- **S1: coverage of a fill over the supply limit (3.1 governs only fills within the limit).**
  - Kept value: `min(days,100)` = 100 consecutive days from the start day that 3.2 gives. Because it "covers" those days, it also moves later fills of the same drug.
  - Uniquely derivable: yes, from `coverage.py`.
  - Witness (2024, drug D): fills 01-01 for 150 days and 02-01 for 30 days. The first covers 01-01..04-09. The second starts 04-10 and covers 04-10..05-09. Covered days 130, period 366, pdc 35.5, in_measure true.
- **S2: period, covered and PDC of a member not in the measure.**
  - Kept value: span from the index date to min(last day of the coverage set, 31 Dec). Covered = days in that span that are covered and not stay days. period = span length, with stays included. PDC = 100*covered/span, rounded half-up. Adherent is false (4.2).
  - Uniquely derivable: yes (see N1).
  - Witness A (2023): one fill 11-01 for 30 days, stay 11-05..11-06. period 30, covered 28, pdc 93.3, adherent false.
  - Witness B (2024): two 30-day fills on 03-03 of one drug. The second shifts to 04-02..05-01. period 60, covered 60, pdc 100.0, in_measure false.
- **S3: rate of a class that is not reportable.**
  - Kept value: tenth(100*adherent/members), rounded half-up.
  - Uniquely derivable: yes.
  - Witness: 3 members, 2 in the measure and adherent, rate 66.7. A class whose only member has one fill gives rate 0.0.

## Other witnesses

- W1 (2023): fills 01-01 and 01-25, 30 days each. in_measure true, period 365, covered 60, pdc 16.4.
- W2 (2024): fills 01-10 and 02-09, 30 days each. period 357, covered 60, pdc 16.8, adherent false.
- W4: a reportable class with 16 members in the measure, 13 of them adherent, gives rate 81.25, reported as 81.3.
- W5: period 365 and covered 292 give pdc 80.0, adherent true.

## Part 2 — solver-path screen

**A) Pre-mortem.** A strong solver will fix:
- start day and same-drug shifting;
- the year-end treatment period with stay days taken out;
- the distinct-date and 2 October test;
- half-up rounding with Fraction, adherent at 80.0 or more requiring in_measure;
- the in_measure denominator for reportable classes.

It then has to keep three silent behaviours:
- the over-limit cap;
- the code's span for members not in the measure;
- the members denominator for classes that are not reportable.

The instruction's silence paragraph is explicit and each case has a clean definitional chain, so a careful solver keeps them. Its own Fraction reference plus fuzzing will confirm the governed parts.

Likely slips:
- rewriting the not-in-measure path onto the new period logic (N1, or taking stays out of its denominator);
- dropping the 100-day cap as a "clamp";
- a float `round()` on half-tenths.

**B) Scores**

| Measure | Score |
|---|---|
| reference_unreachable | 2 |
| authority_incomplete_for_grading | 1 |
| hidden_state_not_closed_form | 1 |
| restraint_traps | 3 (S1 inside the rebuilt coverage routine; S2 inside the rebuilt period and PDC routine; S3 inside the rebuilt class row) |
| fuzz_blind_spot | 2 |

**C) Judgement**
- self_verification_resistance: 2
- prediction: collapses
- confidence: medium
- decisive_reason: the contract is now closed-form, and the only traps are three silence sites that the instruction's paragraph names generically and a careful solver will preserve.

## Where the shipped package departs from the spec

1. coverage.py: coverage starts at fill date + 1 instead of on the fill date (3.1).
2. coverage.py: no same-drug shifting, and no per-drug grouping (3.2).
3. measure.in_measure: counts fills, not distinct fill dates, and has no 2 October limit (2.4).
4. measure.period: for members in the measure it ends at the last covered day, not 31 Dec (2.5).
5. pdc.figures: for members in the measure, stay days are not taken out of the period days (4.1), so `period` is wrong too.
6. rounding.tenth: rounds down instead of half-up (1.2).
7. pdc.figures: adherent uses `>` instead of `>=` and ignores in_measure (4.2).
8. classes.class_row: reportable classes divide by members, not in_measure (5.1).
