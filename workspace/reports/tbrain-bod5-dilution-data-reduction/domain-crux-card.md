# Domain-crux card (pattern-blind, written before the pattern catalog)

Slug: tbrain-bod5-dilution-data-reduction
Date: 2026-09-27, builder D, task-batch 9 (builder_certified)

## Domain-native failure mode

A municipal/industrial water-quality lab runs the five-day biochemical oxygen
demand (BOD5) test as dilution series: each sample is set up in several 300 mL
bottles holding different sample volumes, most bottles get a little seed
(microbial inoculum), dissolved oxygen (DO) is read on day 0 and day 5. Seed
controls (seed alone), dilution-water blanks and a glucose-glutamic acid (GGA)
check standard run beside the samples. A small reduction package turns the bench
export into reported results under the lab's own SOP (WQ-14, invented here). It
has drifted: it still carries older bench thresholds, pools the seed controls
instead of averaging each control's per-mL rate, subtracts the seed correction
after scaling the depletion up by the dilution, averages the blanks instead of
taking the worst, picks the wrong bottle for a less-than result, judges
duplicate agreement against the parent alone, and rounds to a tenth instead of
three significant figures.

## What an expert has to judge

- Which bottles are usable: enough depletion to be read reliably and enough DO
  left at day 5 that oxygen never ran out. The same test applies to seed
  controls, check bottles and sample bottles.
- Seed correction is a per-mL rate from the seed controls, multiplied by the
  seed in each bottle and removed from the depletion before dividing by the
  sample fraction.
- A sample with no usable bottle is not a number: it is a bound, greater than
  when every bottle ran out of oxygen, less than otherwise, taken from the
  bottle that bounds it most tightly.
- Duplicate agreement (RPD) is only meaningful between two measured values; a
  bound is not a measurement.
- A seed factor needs at least one readable seed control.

## Where the SOP stops (expert judgement about scope)

The SOP builds its seed factor from usable seed controls and its RPD from
measured BODs. A batch where no seed control is usable, and a duplicate pair
where one side is only a bound, have no SOP figure; a lab reviewer would flag
them and move on, and the package's current arithmetic is what the lab has been
reporting there. Keeping it is a scope judgement, not a chemistry one.

## Native artifact and deliverable

Input: one batch JSON (bench export). Output: the batch report the driver
prints (seed factor, blank depletion, check value, batch qualifiers, sample
results with relation, duplicate RPDs with pass/fail).
