# SOP TM-07: data reduction for an ICP-MS trace-metal batch

This procedure turns the counts an ICP-MS run list produces into the numbers the
laboratory reports. It covers one batch at a time. Section numbers are cited in
review comments, so keep them stable.

## 1. The batch

A batch file holds three things.

- `analytes`: one to four analytes, each with a `name`, a method detection limit
  `mdl` and a limit of quantitation `loq`, both in µg/L. `mdl` is above nought
  and at most 100; `loq` is at least `mdl` and at most 1000. Names are distinct.
- `standards`: three to eight calibration standards. Each gives, for every
  analyte, its nominal concentration in `conc` (from 0 to 1000 µg/L) and its
  analyte counts in `counts`, plus one internal-standard count `is_counts` for
  the whole standard.
- `runs`: one to eighty runs in the order the instrument measured them. Every run
  has a distinct `id`, a `kind`, analyte `counts` for every analyte and an
  `is_counts`. The kinds are:
  - `sample`: a digested field sample, with an integer `dilution` from 1 to 1000;
  - `spike`: a portion of an earlier `sample` run of the batch (named by
    `parent`) with a known amount of every analyte added before digestion, given
    per analyte in `added` (above nought, at most 1000 µg/L); it carries its own
    `dilution` from 1 to 1000; `added`, like every amount in this SOP, is in µg/L
    of the sample as received;
  - `blank`: a method blank, reagent water carried through the whole digestion;
  - `ccv`: a continuing calibration verification standard with its true
    concentration per analyte in `true`.

All analyte counts are from 0 to 10^9 and every `is_counts` is from 1000 to
10^9. Blanks and CCVs are never diluted. For every analyte the standards hold at
least two different concentrations and the fitted slope (section 2) is above
nought. Every CCV's true concentration is at least ten times the analyte's
`loq`, its reading (section 3) lies between half and one and a half times that
true concentration, and its recovery (section 6) never lies within 10^-6 of a
tie for rounding to one decimal place. Every run's reading lies from -10^4 to
10^4 µg/L. A value judged against an analyte's limits (section 3) never lies
within 10^-5 of its `mdl` or its `loq`, nor within one part in 10^5 of either
limit when that limit is above one.

## 2. Calibration

Each standard gives one point per analyte: its nominal concentration against its
response, the analyte counts divided by the standard's internal-standard counts.
The calibration line of an analyte is the ordinary least-squares straight line of
response on concentration through all the standards' points, unweighted and with
its intercept fitted (not forced through the origin).

## 3. Readings

A run's response for an analyte is its analyte counts divided by its own
`is_counts`. Its reading is the concentration the calibration line gives for that
response: the response less the intercept, divided by the slope. A reading may be
below nought.

In what follows, a blank or a CCV is judged on its reading, and a sample or a
spike on its corrected reading (section 5). A value judged in this way that is at
or above the analyte's `mdl` is a **result**. A value below the `mdl` is a
non-detect, and a non-detect is not a result. Where a rule of this SOP needs the
result of a run that is a non-detect, it gives no rule for the value it defines.

## 4. Blank level

The blank level of an analyte is the mean of the batch's method-blank results for
it, taking every blank of the batch wherever it sits in the run order.

## 5. Samples and spikes

A sample's or a spike's corrected reading is its reading less the blank level.
Its amount is the corrected reading multiplied by its `dilution`; this is the
concentration in the sample as received, in µg/L.

Each is reported per analyte with a flag:

- `ND` when the corrected reading is below the `mdl`; no value is reported;
- `J` when the corrected reading is at or above the `mdl` and below the `loq`;
  the amount is reported;
- an empty string when the corrected reading is at or above the `loq`; the
  amount is reported.

## 6. Continuing calibration verification

A CCV's recovery for an analyte is its reading as a percentage of its true
concentration. The CCV passes for that analyte when the recovery, rounded to one
decimal place, is from 90.0 to 110.0 inclusive, and fails otherwise. The
reported recovery is not rounded.

A sample or spike with a CCV both before it and after it in the run order is
bracketed by the nearest CCV on each side. Its `ccv_ok` for an analyte is false
when either of those two CCVs failed for that analyte, and true when both
passed.

## 7. Spike recovery

A spike's recovery for an analyte is the amount of the spike's result less the
amount of its parent's result, as a percentage of the amount added.

## 8. The report

`tools/metalquant_run.py BATCH` prints one JSON object:

- `blank_levels`: the blank level of every analyte, keyed by analyte name (the
  order of the keys carries no meaning);
- `samples`: one entry per sample or spike run and analyte, with `id`, `analyte`,
  `value` (the amount, or `null` for `ND`), `flag` and `ccv_ok`;
- `ccvs`: one entry per CCV run and analyte, with `id`, `analyte`, `recovery` and
  `pass`;
- `spikes`: one entry per spike run and analyte, with `id`, `analyte` and
  `recovery`, which is always a number.

Each list follows the run order, and within a run the order of `analytes`.
Numbers are not rounded.

These rules give no other correction, qualifier or exclusion.
