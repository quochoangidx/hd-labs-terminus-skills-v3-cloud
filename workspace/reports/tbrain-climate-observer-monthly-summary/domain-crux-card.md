# Domain-crux card

Slug: tbrain-climate-observer-monthly-summary
Date: 2026-09-27, builder D, batch-8 (builder_certified, CORE+ bar). Written before the design is mapped to any
trap pattern; the pattern mapping is in trap-screen.json.

## Domain-native failure mode

A cooperative climate-observer network collects one form per station per month: once a day, at the station's
fixed observation hour, a volunteer reads the maximum and minimum thermometers and the rain gauge and resets
them. The network publishes a monthly climatological summary per station (mean maximum and minimum, mean
temperature, heating and cooling degree days, threshold-day counts, extremes with dates, precipitation total,
precipitation-day counts and the greatest day, completeness). The summary is only right if each reading is
credited to the calendar day it describes, not to the day the form row carries it:

- A reading taken in the morning closes an observation day that mostly fell on the previous calendar day, so
  the network credits a morning observer's maximum and rain to the day before (the minimum, reached near
  dawn, stays on the form day). The first reading of the next month closes the month's last day.
- A gauge that could not be read for a few days produces one accumulated amount at the next reading; it is not
  the rain of one observation day.
- A trace is rain that fell but could not be measured: it is not a hundredth.
- Degree days follow the national convention (each day's mean rounded to a whole degree before the 65 F
  base), and a month's mean temperature for a complete month is the average of its mean maximum and mean
  minimum, not the mean of daily means.

## What an expert has to judge

- Which calendar day each reading belongs to for a morning or a midnight observer, including the month's
  first and last days (a reading drops out of the month or comes in from the next form).
- Which amounts are the rain of one observation day and which are not (an accumulated amount after unread
  days), and what the network's crediting rule does and does not say about each.
- Whether a month is complete for temperature, and which mean-temperature formula the network prescribes for
  which months.
- Inclusive thresholds (90 F and above, 32 F and below, 0 F and below, 0.10 and 1.00 inch or more) and the
  latest-date convention for tied extremes.

## Work surface and deliverable

A ~260-line Python package (`coopsum`) and a fixed driver `tools/coopsum_run.py FORM.json` that prints the
month's summary as JSON (one object per station, in form order). Authority: the network handbook
`/app/docs/observer-handbook.md` (CN-7 part 3), numbered, units and rounding first.

## Why difficulty survives removing incidental schema

The JSON layout is supplied and already right. What is hard is knowing where each handbook rule stops:
the crediting rule speaks of the rain of one observation day, and the mean-temperature formula speaks of
complete months; the package's present treatment of everything else is the answer, and a repair that applies
the new rule to every reading or every month looks correct and is wrong. No reference implementation or
standard library computes this network's figures.

## Natural non-goals

Snowfall and snow depth, evaporation, soil temperature, observation-time changes within a month, quality
control of implausible readings, normals and departures from normal, text (CF6-style) output.
