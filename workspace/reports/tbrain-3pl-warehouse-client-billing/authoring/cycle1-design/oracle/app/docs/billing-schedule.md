# Client billing schedule WB-5: pallet storage and handling

This schedule sets what the warehouse bills a client for storing its pallets and
for moving them in and out, and how the period statement shows it. Where the
billing package and this schedule disagree, the schedule governs. Clause numbers
are quoted in client queries and do not move between editions.

## 1. Units, rounding and limits

1.1 A date is a calendar date written `YYYY-MM-DD`. The time of day of a
movement plays no part.

1.2 Money is in whole cents. A storage rate is in cents per pallet per storage
week; a handling rate is in cents per pallet moved.

1.3 The one figure that can fall between two whole cents is a discount (6.3).
It is rounded to the nearest cent, and an exact half cent is rounded up.
Nothing else is rounded.

1.4 This schedule provides for jobs within the following limits, and for no
others.

- The period ends on its `end` date, from 2001-03-01 to 2099-12-31, and starts
  on its `start` date, from 0 to 61 days before the end. Every receipt,
  dispatch, holiday and effective date in the job is on or before the end and
  at most 400 days before it.
- A job has from 1 to 300 lots with distinct ids. A lot receives from 1 to
  1,000 pallets and has from 0 to 50 dispatches, each of 1 to 1,000 pallets,
  none dated before the receipt, and together never more than the lot
  received. A lot's client is one of the job's clients.
- A job has from 1 to 20 clients. A client has a discount of 0 to 50 percent, a
  whole number, and from 1 to 6 revisions whose effective dates strictly
  increase down the list.
- Every revision holds a storage scale and three handling rates. A storage
  scale has from 1 to 5 tiers; every tier but the last has a length from 1 to 52
  weeks, and the last has no length. Every rate is a whole number from 0 to
  100,000.
- `holidays` holds from 0 to 60 distinct dates.

## 2. Lots and pallets on hand

2.1 A lot is received on its `received` date and leaves the warehouse in
dispatches, each on its own date.

2.2 A lot's pallets are on hand from its receipt date. A dispatched pallet is
still on hand on the day it is dispatched and is gone from the next day. The
pallets a lot has on hand on a day are the pallets it received less those
dispatched on earlier days.

2.3 A lot is closed when every pallet it received has been dispatched, and open
otherwise.

2.4 A working day is a Monday, Tuesday, Wednesday, Thursday or Friday that is
not one of the job's `holidays`.

## 3. Rate cards

3.1 A client's rate card is revised from time to time, and each revision takes
effect on its effective date. A revision is in force on a day when it is the
latest revision of its client whose effective date is on or before that day.
On a day before a client's earliest effective date none of its revisions is in
force, and where a rule needs the revision in force on such a day, it gives no
rule for the value it defines.

3.2 The rates of a storage week are those of the revision in force on the
week's first day. The rates of a movement are those of the revision in force on
the movement's date.

## 4. Storage

4.1 A lot's storage weeks run in blocks of seven days from its receipt date:
its first storage week starts on the receipt date, its second seven days later,
and so on. A week's number is its place in that run.

4.2 The period's storage of a lot is billed week by week: every storage week
that starts within the period, from its start date through its end date both
included, and on whose first day the lot has pallets on hand, is billed for the
pallets on hand on that first day.

4.3 The tiers of a storage scale take a lot's storage weeks by number: the first
tier takes as many weeks as its length, the second tier the next ones, and so
on, and the last tier takes all the rest. A billed week is billed at the rate of
the tier that takes its number. Tiers are not retroactive: a lot reaching a
later tier does not change the rate of its earlier weeks.

## 5. Handling

5.1 A receipt dated within the period is billed for every pallet received, at
the receiving rate (`in`). A dispatch dated within the period is billed for
every pallet dispatched, at the dispatch rate (`out`).

5.2 A movement dated on a day that is not a working day is billed at the
out-of-hours rate (`after_hours`) for every pallet moved, instead of its
receiving or dispatch rate.

## 6. Lot amounts

6.1 A lot's storage is the total its billed weeks are billed; its handling is
the total its movements are billed; its amount is its storage plus its handling.

6.2 A lot's handling is a charge. The storage of a closed lot is a charge. The
storage of an open lot is an accrual: the statement shows it, but it is not a
charge, since the lot's stay is not over. Where a rule needs the storage charge
of an open lot, it gives no rule for the value it defines.

6.3 A lot's discount is its client's discount percentage of the total of the
lot's charges, rounded as 1.3 says.

6.4 A lot's net is its amount less its discount. The statement's total is the
total of its lots' nets.

## 7. The statement

`tools/stockbill_run.py JOB.json` prints one JSON object with `statement` (the
job's `statement`), `lots` and `total`. `lots` holds one entry per lot, in the
job's order, with `id`, `client`, `status` (`"open"` or `"closed"`),
`storage_weeks` (the number of billed weeks), `storage`, `handling`, `amount`,
`discount` and `net`. Counts and money are integers.

This schedule gives no other charge, credit or waiver.
