# Contract review r4 — tbrain-medication-adherence-pdc

Scope: contract-packet-r4 instruction.md + environment/ only.

## Summary of what this packet contains (read cold)

- Claim lines may now carry a days supply of 0. Rules 1.3 and 2.1 and the README all allow it.
- A "fill" is a claim line with a days supply of 1 or more (2.1).
- The package drops classes that have no fill (claims.by_class), and it takes the index date from the first line *in file order* that has a supply.
- A new symptom in the instruction: "exported out of date order gets an index date from the middle of the year".
- Up to 100 members.

## Do README, rule 1.3 and rule 2.1 agree on what a claims file may hold?

Yes.

| Point | 1.3 | 2.1 | README |
|---|---|---|---|
| Days supply | 0 to 365 | a fill is 1 or more; a claim line is any entry | 0 is allowed, for "price or quantity correction" lines |
| Class codes | "claim lines under at most 40 different class codes" | — | one row "per class code that some member has a fill of" |
| Member rows | — | — | one for "each class the member has a fill of" |
| Other limits | member count 1–100 (the instruction agrees); every line of one drug carries one class | — | — |

- The README key is still named `fills` but holds claim lines. The README says so ("the member's claim lines"), so this is polish only.
- A class code that appears only on zero-supply lines counts toward the limit of 40 but gets no row. That is consistent.

## New findings

- **P1 (polish): the key `fills` holds claim lines, not fills in the 2.1 sense.** Both texts say so explicitly, so no reading splits.
- **Two-way sentences: none found.** Checks:
  - 2.3 ("earliest fill") uses the fill *date*, not file order, and the new symptom confirms it.
  - 2.4 counts fills on distinct dates, so a zero-supply line on a second date does not count.
  - 3.1–3.3 say only fills cover days and only fills move one another. A zero-supply line never shifts anything, and it covers nothing.
  - The zero-supply lines cannot split a reading anywhere: nothing a correction line holds changes any figure, and the governed text reaches no case they could disturb.
- Everything else (1.2, 2.4 with 2 October, 2.7/5.1 rate base, 4.1 period days, the 3.1 over-limit length) reads the same as a cold review would expect.

## Witnesses (hand-worked, changed parts)

"line" means a claim line and "fill" means a line with a supply. All are drug D, class C, with no stays unless noted.

1. **(2023) Zero line before the first fill.** Lines 03-01 (0 days), 05-01 (30), 06-01 (30).
   - index 05-01, in_measure true.
   - Coverage runs 05-01..05-30 and 06-01..06-30. The second fill is not covered on its own date, so it does not shift.
   - covered 60; period 245 (05-01..12-31).
   - pdc = 6000/245 = 24.49, reported 24.5; adherent false.
   - The code today gives index 05-01 too, but covers from +1.
2. **(2023) Out of date order.** Lines 06-01 (30) then 01-01 (30).
   - The index is 01-01. The code says 06-01.
   - in_measure true, period 365, covered 60, pdc 16.4.
3. **(2023) A class with only zero lines.** Lines 01-01 (0) and 02-01 (0) under class Z, which no one fills.
   - No member row and no class row for Z.
   - Other classes of the member are unaffected.
4. **(2023) One fill plus a zero line on another date.** Lines 04-01 (30) and 05-01 (0).
   - Only one fill date, so in_measure false.
   - Kept figures: period 30 (04-01..04-30), covered 30, pdc 100.0, adherent false.
   - Class of 1 member: rate 100*0/1 = 0.0.
5. **(2024) Zero line and fill on the same date.** Lines 03-03 (0) and 03-03 (30).
   - One fill, so in_measure false; period 30, covered 30, pdc 100.0.
6. **(2023) Zero line inside coverage.** Lines 01-01 (30), 01-15 (0), 01-20 (30).
   - The third fill starts 01-31. The zero line neither covers anything nor moves anything.
   - covered 60, period 365, pdc 16.4.
7. **(2023) Zero line out of order ahead of the first fill.** Lines 07-01 (30), 02-01 (0), 03-01 (30).
   - index 03-01, not 02-01 and not 07-01; in_measure true.
   - Coverage: 03-01..03-30 and 07-01..07-30, so covered 60.
   - period 306 (03-01..12-31); pdc = 6000/306 = 19.61, reported 19.6.
8. **(2023) Reportable class with zero lines.** 10 members each have 2 fills covering the whole year, and 1 member has only a zero line.
   - The class row has members 10, in_measure 10, adherent 10, rate 100.0.
   - The zero-only member is not in `members`.

## Figures left to today's code

- **Over-limit fill length:** min(days, 100) = 100 consecutive days from the start day. Unique.
  - Witness (2024): fills 01-01 (150) and 02-01 (30). covered 130, period 366, pdc 35.5.
- **Member not in the measure:** span = index date to min(last covered day, 31 Dec), stay days kept in. covered = days in the span that are covered and not stay days. pdc = 100*covered/span, rounded half-up. Unique.
  - Witness 4 above; also 2023 fill 11-01 (30) with a stay 11-05..11-06, giving period 30, covered 28, pdc 93.3.
- **Rate base of a class that is not reportable:** `members`, the number of members with a fill of the class. It is never zero and it is unique.
  - Witness 4: rate 0.0. Another: 3 members, 2 adherent, rate 66.7.
- **Rows for classes with only zero-supply lines:** the README positively governs these (no row). This is not a silence site.

No sentence of the spec positively governs any of the three kept figures.

## Part 2 — solver-path screen

**A) Pre-mortem.** A strong solver will:
- filter zero-supply lines out of the fills;
- take the index date as the minimum fill date;
- rebuild coverage per drug with shifting;
- set the in-measure test to distinct dates and 2 October;
- set the year-end period with stay days taken out;
- round half-up exactly, judge adherent at 80.0 or more and in the measure, and divide by the rate base.

A Fraction reference plus fuzzing confirms the governed parts.

The zero-supply change adds breadth but no trap:
- the natural filter is correct;
- the package's own `by_class` already drops classes with only zero lines, and the README demands that.

The remaining risks are the three restraint sites: removing the 100-day cap, the not-in-measure span, and the non-reportable denominator. The silence paragraph covers all three.

**B) Scores**

| Score | Value |
|---|---|
| reference_unreachable | 2 |
| authority_incomplete_for_grading | 1 |
| hidden_state_not_closed_form | 1 |
| restraint_traps | 3 |
| fuzz_blind_spot | 2 |

**C) Assessment**

- self_verification_resistance: 2
- prediction: collapses
- confidence: medium
- decisive_reason: the contract is closed-form and every exact convention is written down; the zero-supply addition is a straightforward filter, so only the three kept-figure sites could separate solvers.

## Where the shipped package departs from the spec

1. coverage.covered: coverage starts at fill date + 1, not the start day (3.1).
2. coverage.covered: there is no same-drug shifting and no per-drug grouping (3.2).
3. measure.index_date: it takes the first line in file order that has a supply, not the earliest fill date (2.3).
4. measure.in_measure: it counts fills, not distinct fill dates, and has no 2 October limit (2.4).
5. measure.period: for members in the measure, the period ends at the last covered day, not 31 Dec (2.5).
6. pdc.figures: stay days are not taken out of the period days for members in the measure (4.1), so `period` is wrong too.
7. rounding.tenth: floor instead of half-up (1.2).
8. pdc.figures: adherent uses `>` and ignores in_measure (4.2).
9. classes.class_row: a reportable class divides by members, not its rate base (5.1).

For contrast, two parts are consistent with the spec:
- zero-supply lines produce empty coverage;
- `by_class` drops classes that have no fill.
