# Domain-crux card

Slug: tbrain-3pl-warehouse-client-billing
Date: 2026-09-27, builder C, batch-8 (builder_certified). Replaces tbrain-container-demurrage-detention
(orchestrator novelty ruling: same setting as an accepted ULD demurrage task); trap mechanics carried over,
domain, authority, data and wording new.

## Domain-native failure mode

A third-party-logistics (3PL) warehouse bills each client monthly for storing its pallets and for moving
them in and out. The client billing schedule (WB-5) bills storage on each lot's receipt anniversary
(seven-day storage weeks from the receipt date, charged for the pallets on hand on the week's first day),
prices each week on a non-retroactive long-stay tier by the week's own number, bills handling per pallet
moved with an out-of-hours rate on weekends and public holidays, prices every line on the client rate
card in force on its date, and takes a contract discount on invoiced charges. The billing package has
drifted: pallets leave on their dispatch day, storage runs on calendar weeks, a lot that reaches the
long-stay tier has every week billed there, a dispatch is billed as one pallet, holidays are not out of
hours, every line uses the newest rate card, and discounts are truncated.

## What an expert has to judge

- Anniversary storage: a pallet on hand on the first day of a storage week pays the whole week, and a
  pallet dispatched that very day was still on hand.
- Tiers by week number, not by the lot's age at the end of the period.
- Rate cards in force by date, line by line.
- Stock still on hand at the period end: its storage on the statement is an accrual, not a charge; the
  discount rule is written for charges, so where it stops the desk's present figure stands.
- A client whose rate card begins inside the period: lines dated before it have no card in force, and the
  desk keeps pricing them the way it does today.

## Work surface and deliverable

A ~190-line Python package (`stockbill`) and a fixed driver printing the period statement as JSON (per lot:
status, billed storage weeks, storage, handling, amount, discount, net; the total). Authority:
`/app/docs/billing-schedule.md`.

## Why difficulty survives removing incidental schema

The two stops are values the schedule defines only through a term defined elsewhere that does not reach
every input: the discount is taken on "charges" and an open lot's storage is an accrual; a line is priced
on the revision "in force" and before the earliest effective date none is. The natural repairs (round half
up; look up the card by date) are right where the term applies and overwrite a kept value that still
carries the departure just fixed.

## Two disjoint natural-but-wrong repairs

1. Round every discount half up (or take an open lot's discount on its handling only) instead of keeping
   today's truncated percentage of the repaired amount.
2. Price a line dated before the client's first rate card on the earliest card (or fail) instead of today's
   latest card.

## Addendum after contract_review r1 (redesign 1/1)

The open-lot accrual/discount and the static "before the first rate card" silence are gone (F1, F2).
The two stops now hang on membership the repair itself computes: a lot whose rebuilt storage falls
below the client's minimum pays a minimum fee, which is not a "storage charge", so the energy
surcharge rule (whose rounding is a departure) gives no rule for it; a lot that the rebuilt anniversary
weeks and on-hand counts leave without a billed week has no figure for its peak (the largest over billed
weeks), and today's daily maximum stands. One general sentence (2.6) states the silence for every term.

## Addendum after skeleton cycle-2 (the one strengthening)

The schedule now only defines and rules; no sentence says a value has no rule. The warehouse keys
pallets taken back into stock as a negative entry in the lot's dispatch list; the schedule's timing
rule is for dispatches, which it defines as entries of one pallet or more, so a return keeps the
package's same-day timing while the natural fix moves every entry to the next day. A lot with no billed
week keeps today's daily-maximum peak.

## Addendum after skeleton cycle-3

The peak of a lot with no billed week is now governed (nought). The second stop is a lot booked in that
arrived with no pallets: the schedule bills a receipt fee per receipt and defines a receipt as an arrival of
one pallet or more, so the natural "fee on every lot received in the period" over-bills it. Returns are
never billed handling (only receipts and dispatches are).
