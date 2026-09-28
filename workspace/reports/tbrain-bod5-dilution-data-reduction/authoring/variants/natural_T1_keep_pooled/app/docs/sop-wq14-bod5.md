# SOP WQ-14: reducing a five-day BOD batch

This procedure turns the bench sheet of one five-day biochemical oxygen demand
(BOD5) batch into the figures the laboratory reports. Where the reduction
package and this SOP disagree, the SOP governs. Section numbers are quoted in
data-review notes and do not change between editions.

## 1. Units, rounding and limits

1.1 Dissolved oxygen (DO) and every BOD figure are in mg/L; volumes are in mL.
Every bottle is a 300 mL BOD bottle.

1.2 A reported value (a sample's value in section 5 and the check value in
section 7) is rounded to three significant figures, an exact half going away
from nought. Nothing else is rounded: the seed factor, the blank depletion and
every RPD are reported exactly as worked out. Every figure is worked out from
unrounded figures; a value is rounded only as it is written to the report.

1.3 A batch holds:

- one to six seed controls, each with a `seed_ml` from 5 to 30;
- one to four dilution-water blanks;
- one check (the glucose-glutamic acid check standard) of one to three
  bottles, each with a `sample_ml` from 2 to 12;
- one to forty samples with distinct ids, each of one to five bottles, each
  bottle with a `sample_ml` from 0.5 to 300.

Every check or sample bottle has a `seed_ml` from 0 to 3, and its `sample_ml`
and `seed_ml` together are at most 300. A sample's `duplicate_of` is either
null or the id of another sample of the batch whose own `duplicate_of` is null.

1.4 Every bottle has an initial DO from 6.00 to 9.50 and a final DO from 0.00
to 9.50, each read to the hundredth. A seed control's depletion (2.1) is from
nought to 0.3 mg/L per mL of its seed; a blank's depletion is from -0.50 to
1.00. At least one of the check's bottles is usable (2.4).

1.5 Limits are never met exactly: no depletion is 2.50, no final DO is 1.20 and
no blank depletion is 0.20. No RPD lies within 10^-6 of 25, no check value lies
within 10^-6 of 175 or of 225, and no value that is rounded lies within one
part in 10^9 of a tie for three significant figures.

## 2. Bottles

2.1 A bottle's depletion is its initial DO less its final DO. It may be below
nought.

2.2 A bottle's sample fraction is its `sample_ml` divided by 300.

2.3 A bottle is spent when its final DO is below 1.20 mg/L: the oxygen ran out
at some point in the five days and the depletion understates the demand.

2.4 A bottle is usable when it is not spent and its depletion is 2.50 mg/L or
more. The test is the same for seed controls, check bottles and sample bottles.

2.5 The reference controls of a batch are its usable seed controls. A batch
none of whose seed controls is usable takes every one of its seed controls as a
reference control.

## 3. Seed correction

3.1 A seed control's seed rate is its depletion divided by its `seed_ml`, in
mg/L per mL of seed.

3.2 The seed factor of the batch is the mean seed rate of its reference
controls.

3.3 A bottle's seed correction is the seed factor multiplied by the bottle's
`seed_ml`. A bottle without seed has a seed correction of nought.

## 4. Bottle BOD

4.1 The BOD of a check or sample bottle is its depletion less its seed
correction, divided by its sample fraction.

## 5. Sample results

5.1 A sample with one or more usable bottles has a measured BOD: the mean BOD
of its usable bottles. The sample is reported as `=` its measured BOD.

5.2 A sample with no usable bottle, all of whose bottles are spent, is reported
as `>` the BOD of its bottle holding the least sample.

5.3 Any other sample with no usable bottle is reported as `<` 2.50 divided by
the sample fraction of its bottle holding the most sample, spent or not.

5.4 Where two bottles of a sample hold the same `sample_ml`, the one listed
first is taken.

## 6. Duplicates

6.1 A sample whose `duplicate_of` names another sample is a duplicate of that
sample. Its RPD is the difference between its measured BOD and the measured BOD
of the sample it duplicates, taken without sign, as a percentage of the mean of
the two.

6.2 A duplicate passes when its RPD is 25 or less, and fails otherwise.

## 7. Batch checks

7.1 The blank depletion of the batch is the largest depletion among its
dilution-water blanks. A blank depletion above 0.20 mg/L puts the qualifier `B`
on the batch.

7.2 The check value is the mean BOD of the check's usable bottles. A check value
that, before rounding, is below 175 or above 225 puts the qualifier `G` on the
batch.

## 8. The report

`tools/bodcalc_run.py BATCH.json` prints one JSON object:

- `batch`: the batch id;
- `seed_factor`, `blank_depletion` and `check_value`;
- `qualifiers`: the batch's qualifiers as one string, `B` before `G`, empty
  when there are none;
- `samples`: one entry per sample in the order of the batch, with `id`,
  `relation` (`=`, `<` or `>`) and `value`;
- `duplicates`: one entry per duplicate in the order of the batch, with `id`,
  `of` (the id it duplicates), `rpd` and `pass`.

Every number in the report is written as a floating-point number (`12.0`,
never `12`).
