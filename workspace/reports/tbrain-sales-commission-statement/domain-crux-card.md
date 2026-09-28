# Domain-crux card (pattern-blind; written before the design was fixed)

Slug: tbrain-sales-commission-statement
Date: 2026-09-28, builder I, task-batch 9 (builder_certified, CORE+ bar)

## Domain-native failure mode

A B2B equipment seller's sales-operations desk pays its field reps a quarterly
commission statement under a written compensation plan. Each rep's quarter
starts from the CRM export: the rep's credit on every order booked (with the
rep's split when a deal was shared), credit notes billing raised against the
rep's orders, the rep's quota, a recoverable draw and anything owed or carried
from earlier quarters. The desk works out bookings, commission in quota bands
with accelerators above quota, clawbacks on cancelled business, a bonus for
winning a new customer, the draw guarantee and its recovery, and a minimum
payment below which nothing is sent that quarter. The statement tool was
written years ago and carries slips a comp analyst meets in real incentive
software: split deals credited in full to every rep on them, the accelerator
paid retroactively on the whole quarter instead of on the part above quota,
cents truncated, an old clawback window, a new-logo bonus that silently drops
small splits, draw recovery that eats into the guaranteed draw, and an old
minimum payment.

## What an expert has to judge

- Split credit: a shared deal credits each rep only the rep's split of it, and
  the split share is rounded once.
- Marginal bands: the accelerator rate applies to the part of bookings above
  quota, not retroactively to the whole quarter; each band rounds on its own.
- Clawback: the plan claws commission back on cancelled business raised within
  a window after booking. Billing also raises small courtesy credits (a late
  delivery, a price keyed wrong); the plan gives every credit note a clawback
  line but prices only a cancellation.
- New-logo bonus: written for a real new customer, a first order of a stated
  size. Many first orders are trial orders of a few units; the plan lines them
  up on the bonus without pricing them.
- Draw: a guaranteed advance; a shortfall becomes owed, and later recovery can
  only come out of earnings above the draw, never out of the draw itself.
- Minimum payment: a plan figure that changes by plan year; the statement tool
  keeps its money thresholds in one place that several steps read, and a figure
  the plan sets for one step is not thereby set for another.

## Work surface and deliverable

A ~300-line synthetic Python package (`commission`) plus a fixed driver that
reads one job file (reps, each with orders, credit notes, quota, draw, owed and
carried amounts) and prints one JSON statement per rep. The authority is one
numbered in-environment compensation plan. The candidate repairs the package so
the statements follow it.

## Why difficulty should survive removing incidental schema

The deliverable is ten integers per rep. What stays hard is how far each
repaired rule reaches: which credit notes the clawback rule prices, which first
orders the bonus rule prices, and which steps a changed plan figure moves. A
solver who writes a reference from the plan and fuzzes the package against it
learns only what its own reading of those reaches says; domain instinct (a
goodwill credit should not cost a rep commission, a trial order is not a new
logo) pulls toward zeroing the lines the plan leaves unpriced.
