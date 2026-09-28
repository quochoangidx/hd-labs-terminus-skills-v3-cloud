# Domain-crux card (pattern-blind, written before the pattern catalog)

Slug: tbrain-microbial-plate-count-reporting
Date: 2026-09-27, builder B, task-batch 9 (builder_certified)

## Domain-native failure mode

A food-microbiology laboratory reads its aerobic plate count (APC) plates into a
small package that turns the readings into the CFU/g or CFU/mL result on the
certificate. The laboratory's own SOP (fictional Tarnwell Food Laboratory, SOP
MIC-14) validates its own countable range and its own reporting rules, but the
package still carries habits from a reference method and a few coding slips:
the wrong countable range, only one dilution used where two should be pooled by
their plated amounts, 0.1 mL spread plates treated as 1.0 mL pour plates, plates
read as too numerous to count taken as empty, the less-than and greater-than
bounds taken from the wrong end of the series, an estimated count that pools
every uncrowded plate of every dilution, and banker's rounding at the second
significant figure.

## What an expert has to judge

- The count is colonies divided by the amount of sample actually plated: the
  plated amount of a plate is its volume times its dilution, so a 0.1 mL spread
  plate at 10^-2 carries the same sample as a 1.0 mL pour plate at 10^-3.
- Two dilutions are only pooled when they are neighbours in the tenfold series.
  A laboratory that plates alternate steps (10^-1, 10^-3, 10^-5) has no pair to
  pool, and a count at 10^-1 must not be averaged with one a hundredfold weaker.
- A sample with no plate in the countable range is either sparse (every plate
  below the range, estimate from the strongest dilution holding a colony, or a
  less-than result at the detection limit of the strongest dilution) or crowded
  (every plate above, a greater-than result at the weakest dilution). A sample
  that is crowded at the strong end and sparse at the weak end (a dilution jump
  that skipped the countable range) is a genuinely awkward case that the SOP does
  not decide.
- Reporting: two significant figures, an exact half going up, written as d.dEk.

## Work surface and deliverable

A ~250-line Python package (`platecount`) plus a fixed driver that prints the
batch report as JSON (per sample: id, unit, kind, apc). The authority is one
numbered in-environment SOP (`/app/docs/apc-sop.md`). The candidate repairs the
package so the report follows the SOP, and leaves the SOP's silent figures where
today's code puts them.
