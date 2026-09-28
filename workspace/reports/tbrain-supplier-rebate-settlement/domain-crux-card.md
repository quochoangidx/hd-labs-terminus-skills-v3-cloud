# Domain-crux card (pattern-blind, written before the pattern catalog)

Slug: tbrain-supplier-rebate-settlement
Date: 2026-09-28, builder G, task-batch 9 (builder_certified, CORE+ bar)

## Domain-native failure mode

A wholesale distributor settles each supplier's quarterly rebate from its
purchase ledger export under a numbered supplier agreement schedule. The
settlement statement combines a volume rebate at the tier the quarter's net
purchases reach, a growth bonus over the same quarter last year, returns netted
off purchases less the supplier's handling charge, price-protection credits on
stock on hand when the supplier cuts a list price, and ship-and-debit
chargebacks on sales to contract customers below the distributor's cost. A
statement below the agreement's minimum is not paid but carried to the next
quarter. The package was written from how the ledger export looks, not from the
agreement, and carries slips a rebate analyst sees in real settlement tools:
goods counted toward the quarter they were invoiced in rather than received in,
tiers picked on gross instead of net purchases, a tier threshold treated as
exclusive, the rebate truncated instead of rounded, the growth bonus paid on
all purchases instead of on the increase, an old handling charge, an old
minimum settlement.

## What an expert has to judge

- Purchases count by receipt, not invoice: freight in transit at a quarter end
  belongs to the next quarter. Goods that do not travel by freight have no such
  lag; the agreement's receipt rule speaks of freight shipments only.
- Tiers are retroactive on the whole net volume; returns reduce the volume.
- Growth bonus rewards the increase, not the base.
- Price protection is owed on a price drop the agreement recognises; the
  supplier's price file also carries small tidy-up adjustments that the
  protection clause does not speak of.
- A chargeback is owed on a contract sale as the agreement defines it; the
  distributor also records price-match sales a few cents under cost that the
  chargeback clause does not speak of.
- A contractual figure (handling charge, minimum settlement) changes by
  schedule edition; the package keeps several figures in shared places, and a
  figure the agreement sets for one purpose is not thereby set for another.

## Work surface and deliverable

A ~300-line synthetic Python package (`rebate`) plus a fixed driver that reads
one job file (the tier table and a list of supplier accounts with their ledger
export) and prints a JSON settlement statement per account. The authority is
one numbered in-environment agreement schedule. The candidate repairs the
package so the statement follows the schedule.

## Why difficulty should survive removing incidental schema

The deliverable is a dozen integers per account. What stays hard is how far
each repaired rule reaches: which ledger lines the receipt rule moves, and
which consumers of a shared contractual figure the schedule actually sets. A
solver who writes its own reference from the schedule and fuzzes the package
against it only learns what its own reading of those reaches says.
