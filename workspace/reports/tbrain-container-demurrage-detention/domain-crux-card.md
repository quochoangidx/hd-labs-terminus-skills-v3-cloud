# Domain-crux card (pattern-blind, written before the pattern catalog)

Slug: tbrain-container-demurrage-detention
Date: 2026-09-27, builder C, task-batch 1 / batch-8 (builder_certified)

## Domain-native failure mode

An ocean carrier's import demurrage-and-detention (D&D) billing package reads
each container's event history (discharge at the terminal, gate-out full to the
consignee's trucker, empty return to the depot) and the consignee's contract
(free days per stage, tiered daily scales that are revised from time to time, a
negotiated discount) and writes the per-container charge statement the billing
desk sends out at an invoice cut-off. The carrier's published tariff rules have
moved on and the package has not: it still counts free time in calendar days
where the rules now count working days at the terminal, charges the days the
terminal was shut, counts every stay a day short, starts the merchant stage the
day after gate-out, charges a long stay entirely at the top tier ("retroactive"
tiers, which the rules dropped), prices every stay on the newest scale even when
its charges began under an older one, and truncates the discount.

## What an expert has to judge

- Terminal free time runs on working days (weekdays that are not port holidays)
  and a terminal closure neither uses free time nor is charged; once free time
  has run out, weekends and holidays are charged like any other day.
- A stay is counted from its first day through its last, both included; the
  gate-out day belongs to both stages.
- Tiers are incremental: each chargeable day is priced by its own place in the
  count, not by where the stay ends.
- A stay is priced on the scale in force when its charges began, which is not
  the scale in force at invoicing.
- An invoice run at a cut-off holds boxes still at the terminal or still out
  with the merchant: their figures are running accruals, not charges, and the
  tariff's discount rule is written for charges. What the billing desk prints
  for such a box, where the rules stop, is what the system prints today.
- A contract's scale history may start after a box's charges began (a contract
  signed while the box was already out): the rules give no scale for that, and
  the desk keeps pricing it the way it does today.

## Work surface and deliverable

A ~300-line Python package (`ddbill`) plus a fixed driver that prints the
invoice statement as JSON (per container: each stage's first day, last free
day, days, chargeable days, amount and status; the container's amount,
discount and net; the invoice total). The authority is one numbered
in-environment document, the carrier's tariff rules
(`/app/docs/tariff-rules.md`). The candidate repairs the package so the
statement follows the rules.

## Why difficulty survives removing incidental schema

The two places the repair has to stop are values the rules define only through
a term whose definition sits elsewhere and does not reach every input: the
discount is taken off "charges", and a running stage has an accrual, not a
charge; the scale is the revision "in force" on the first chargeable day, and
before a contract's first revision none is. In both places the natural repair
(round the discount half up; pick the revision by date) is the correct rule
where the term applies, and it overwrites the value the package must keep
elsewhere, a value that still carries the very departure just fixed. The JSON
shape is incidental.

## Native artifact

Container event histories as a carrier's track-and-trace export reduces them
(event code + date per move), a contract's rate sheet with dated revisions and
tiered daily scales per stage and size, and a port calendar (holidays,
terminal closures).

## Two disjoint natural-but-wrong repairs

1. Fix the truncated discount by rounding half up for every container, which
   also rounds the discount of a box still running at the cut-off, where the
   rules give no rule and today's truncation stands (taken on the repaired
   amounts).
2. Fix "priced on the newest scale" by choosing the revision in force on the
   first chargeable day for every stay, and fall back to the earliest revision
   (or fail) when the charges began before the first revision, where the rules
   give no rule and today's newest-scale choice stands.
