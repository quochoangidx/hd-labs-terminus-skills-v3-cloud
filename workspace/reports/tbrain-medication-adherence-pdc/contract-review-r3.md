# Contract review r3 — tbrain-medication-adherence-pdc

Scope: contract-packet-r3 instruction.md + environment/ only.

Changes since r2:
- Rule 1.3 lowers the member limit to 200, and each drug code now carries one class code.
- Rule 3.1 is rewritten.
- Rule 2.7 adds the term "rate base", which the new 5.1 uses.
- The instruction's member count is 200.

## New findings

- **N2 (polish): "Add no exception, clamp or guard that the specification does not give" versus the existing `min(days, SUPPLY_LIMIT)`.**
  - Rule 3.1 now says every fill covers "one or more consecutive days" but gives a length only for fills within the limit.
  - The existing cap is the value kept for over-limit fills. It is not an *added* clamp, and the silence sentence keeps it.
  - A hasty solver could read the cap as a clamp the spec does not give and remove it.
    - Counterexample (2024): fills 01-01 for 150 days and 02-01 for 30 days, drug D.
    - Keep the cap: covered 130, pdc 35.5.
    - Remove the cap: the second fill starts 05-30, covered 180, pdc 49.2.
  - The text resolves it: "keeps working the figure out the way it does today". So this is a restraint site, not an ambiguity.
- **1.3 drug/class limit: closes a gap I had not raised before.** In r2, a drug listed under two classes left open whether the shifting in 3.2 crosses classes. That input is now out of scope. No new issue.
- **Member limit 200:** the spec and the instruction agree.
- **Sentences that read two ways:** none found. I checked:
  - 3.1 ("Every fill covers one or more consecutive days"): it settles the start day and that coverage is continuous, and leaves only the length open.
  - 5.1 plus 2.7: the rate formula now applies to every class, and only its denominator is left undefined for a class that is not reportable.
  - 1.2, 2.4 and 4.1: unchanged since r2 and still single-reading.

## Figures left to today's code

- **S1: how many days an over-limit fill covers.**
  - What the spec positively governs: the start day (3.1/3.2), that the days are consecutive, and that the fill covers at least one day (3.1). No sentence gives the length.
  - Kept value: min(days, 100) = 100. It is unique.
  - Because the fill "covers" those days, it moves later fills of the same drug.
  - Witness (2024, drug D): fills 01-01 for 150 days and 02-01 for 30 days. The first covers 01-01..04-09. The second covers 04-10..05-09. period 366, covered 130, pdc 35.5, in_measure true, adherent false.
- **S2: period, covered and PDC of a member not in the measure.**
  - Governed by 2.5/3.4/4.1: no, because the treatment period and period days exist only for members in the measure.
  - Governed elsewhere:
    - rounding (1.2, "every PDC the report gives");
    - adherent = false (4.2);
    - coverage (3.1–3.3).
  - Kept value: span = index date to min(last day of the coverage set, 31 Dec), with stay days kept in the period. covered = days in that span that are covered and not stay days. PDC = 100*covered/span, rounded half-up. It is unique.
  - A solver could slip by ending the span at the last covered day that is not a stay day, but the code rules that out (N1 from r2).
  - Witness (2023): one fill 11-01 for 30 days, stay 11-05..11-06. period 30, covered 28, pdc 93.3, in_measure false, adherent false.
- **S3: rate base of a class that is not reportable.**
  - What the spec governs: the rate formula for every class (5.1), the numerator (4.2) and the rounding (1.2).
  - The rate base is defined only for reportable classes (2.7), so the denominator is left to the code.
  - Kept value: `members`, the count of members with a fill of the class. It is never zero, so no guard is needed. It is unique.
  - Nothing in the spec extends "rate base" to other classes.
  - Witness: 3 members, 2 in the measure and adherent, gives rate 100*2/3 = 66.7. A single member whose one fill does not put it in the measure gives rate 0.0.

## Part 2 — solver-path screen

**A) Pre-mortem.** A strong solver will:
- rebuild coverage per drug, starting on the fill date, with shifting;
- set a year-end treatment period with stay days taken out for members in the measure;
- apply the distinct-date and 2 October test;
- round half-up with Fraction or an exact comparison;
- judge adherent as PDC ≥ 80.0 and in the measure;
- divide by the rate base.

It then writes its own reference and fuzz tests, and those confirm the governed parts. The 5.1/2.7 wording now makes it plain where the rate base stops, so S3 is easy to keep. The remaining risks:
- S1: removing the 100-day cap after reading "add no clamp";
- S2: rewriting the not-in-measure path onto the new period logic, or ending its span at the last non-stay covered day.

A solver that follows the silence paragraph literally keeps all three.

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
- decisive_reason: every sentence now reads one way, and the only places a strong solver could fail are three sites the silence paragraph covers, so the task depends on restraint rather than on any ambiguity.

## Where the shipped package departs from the spec

These are unchanged from r2:
1. Coverage starts at fill date + 1 (3.1).
2. There is no same-drug shifting (3.2).
3. in_measure counts fills and has no 2 October limit (2.4).
4. For members in the measure, the period ends at the last covered day, not 31 Dec (2.5).
5. Stay days are not taken out of the period days (4.1).
6. Rounding is floor, not half-up (1.2).
7. Adherent uses `>` and ignores in_measure (4.2).
8. A reportable class divides by members, not its rate base (5.1).
