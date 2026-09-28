# Domain-crux card (pattern-blind, written before the pattern catalog)

Slug: tbrain-cold-chain-lot-disposition
Date: 2026-09-27, persistent builder, task-batch 8 (builder_certified, CORE+ bar)

## Domain-native failure mode

A pharmaceutical distributor's QA group disposes each product lot (release,
quarantine, reject) from the temperature-logger exports of every shipment leg
the lot travelled plus the product's stability record (labelled storage range,
excursion bands with hour allowances, freeze point, Arrhenius activation ratio
for mean kinetic temperature). The in-house disposition tool was written for a
single-leg, courier-report world and carries the slips such tools accumulate:
logger rows credited with the interval that *precedes* them instead of the one
they open, band edges that put a reading on the labelled limit into an
excursion, each leg judged on its own so the excursion clock restarts at every
handover, the manufacturer's pre-distribution excursion time ignored, mean
kinetic temperature taken as an unweighted average with a 273 K offset and
compared after rounding, hours truncated for the report, logger gaps detected
with the wrong spacing.

## What an expert has to judge

- Time attribution: which reading's temperature stands for which minutes, and
  what happens where the logger's spacing breaks down (a gap) or where one
  leg's export ends and the next begins (a handover is not logger time).
- Band membership at the edges of the labelled range and of each band, and the
  fate of a reading hotter or colder than the stability table describes.
- Budget carry: excursion time is a property of the lot's whole history, so the
  allowance is consumed across legs and after what the release certificate
  already recorded.
- MKT as a time-weighted Arrhenius mean in kelvin, over exactly the minutes the
  attribution assigns, compared unrounded with the labelled limit.

## Why difficulty survives removing incidental schema

Strip the JSON/CSV layout and the ids: what remains is a time-attribution
ledger whose weights feed two consumers (band clocks and the MKT exponential
mean). Every repair of one consumer invites rewriting the shared attribution or
the lot aggregate, and the SOP defines its terms (logged interval, band ends,
leg export) narrowly enough that a uniform rewrite changes figures the SOP
never governed.

## Two natural but wrong repairs (distinct surfaces)

1. Attribution surface: flip every interval to the reading that opens it
   (including spacings the SOP does not call logged intervals), or flatten all
   legs into one stream and take successive differences for the MKT weights
   (creating intervals across handovers).
2. Band surface: rewrite band lookup as clean two-ended membership, so readings
   hotter/colder than the table's outermost band drop out of every clock.

## Direct observable behaviour

The driver writes one JSON disposition report per job: per lot, disposition,
hours in each band, remaining allowance per band, unlogged hours and MKT to a
tenth. An isolated verifier runs the fixed driver on sealed job directories and
compares whole reports with expectations sealed from an independent model;
each rule and each kept step moves at least one reported figure.
