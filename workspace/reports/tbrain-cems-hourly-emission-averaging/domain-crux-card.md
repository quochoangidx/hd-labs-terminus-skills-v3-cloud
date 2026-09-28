# Domain-crux card (pattern-blind, written before the pattern catalog)

Slug: tbrain-cems-hourly-emission-averaging
Date: 2026-09-27, builder A, task-batch 9 (builder_certified, CORE+ bar)

## Domain-native failure mode

A power plant's environmental team files a quarterly NOx report for a boiler
under its air permit. The data acquisition system (DAHS) exports the stack
continuous emissions monitor (CEMS) as quarter-hour records: unit load, NOx
ppm, O2 per cent, stack flow and a QA status code. A small in-house package
reduces that export to operating hours, hourly averages, O2-corrected
concentrations, mass rates, substitute values for lost hours, tons for the
quarter and 30-operating-day rolling averages with exceedance flags. The
package was written from habits that do not match the plant's data reduction
procedure: every record of an hour averaged (bad codes and shut-down quarters
included), an hour thrown out whenever any quarter is short (the calibration
allowance forgotten), 21.0 per cent ambient oxygen instead of 20.9, mass
computed from the corrected concentration, a whole hour of mass for an hour
the unit ran fifteen minutes, lost hours filled by carrying the last good hour
forward, and rolling averages over 30 calendar days of daily means that also
swallow substitute data and flag at-limit days.

## What an expert has to judge

- An operating hour is not a valid hour: the minimum-data rule decides
  validity quarter by quarter, and a calibration hour has its own allowance.
- Which averages feed which figure: measured concentration for mass, O2
  corrected concentration for the limit, operating time for tons.
- The O2 correction is written for flue gas from firing burners; near-ambient
  oxygen at light-off or purge blows the ratio up, which is why plants carry a
  diluent cap, and a procedure may simply not speak to such hours.
- Substitute data fill hours of lost data; the procedure's own definition of
  lost data decides which hours the fill rule reaches.
- A 30-day rolling average for boilers counts operating days, and compliance
  averages use measured hours only, not substitute values.

## Work surface and deliverable

A ~300-line synthetic Python package (`cemsqr`) and a fixed driver
`tools/cemsqr_run.py JOB.json` printing one JSON report: every operating hour
(kind, corrected NOx, mass rate), every operating day (rolling average,
exceedance), operating and valid hour counts, and quarter tons. The authority
is one numbered data reduction procedure in `/app/docs`. The candidate repairs
the package to the procedure.

## Why difficulty should survive removing incidental schema

The report is a few integers per hour and per day. What stays hard is scope:
the procedure defines lost data and firing hours narrowly, and the package's
fill loop and its correction expression serve hours beyond those definitions.
A reference written from the procedure and fuzzed against the repair shares
whatever the solver decided for those hours, so self-testing cannot reveal an
over-reach.
