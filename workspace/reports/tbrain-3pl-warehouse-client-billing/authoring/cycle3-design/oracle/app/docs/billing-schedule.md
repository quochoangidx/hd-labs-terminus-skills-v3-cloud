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

1.3 An energy surcharge (6.2) can fall between two whole cents. It is rounded
to the nearest cent, and an exact half cent is rounded up.

1.4 This schedule provides for jobs within the following limits, and for no
others.

- The period ends on its `end` date, from 2001-03-01 to 2099-12-31, and starts
  on its `start` date, from 0 to 61 days before the end. Every receipt, entry,
  holiday and effective date in the job is on or before the end and at most 400
  days before it.
- A job has from 1 to 300 lots with distinct ids. A lot receives from 1 to
  1,000 pallets and has from 0 to 50 entries in its `dispatches`, none dated
  before its receipt, each giving a whole number of pallets from -1,000 to
  1,000. For every date, the lot's entries dated before it, and its entries
  dated on or before it, each add up to between nought and the pallets it
  received. A lot's client is one of the job's clients.
- A job has from 1 to 20 clients. A client has a `minimum` from 0 to 1,000,000
  cents, a `surcharge_percent` from 0 to 50, both whole numbers, and from 1 to 6
  revisions whose effective dates strictly increase down the list. A client's
  first revision takes effect on or before the receipt date of each of its lots
  and on or before the period's start.
- Every revision holds a storage scale and three handling rates. A storage
  scale has from 1 to 5 tiers; every tier but the last has a length from 1 to 52
  weeks, and the last has no length. Every rate is a whole number from 0 to
  100,000.
- `holidays` holds from 0 to 60 distinct dates.

## 2. Terms

2.1 A lot is received on its `received` date. Each entry of its `dispatches`
is dated and gives a number of pallets; several entries may share a date. A
dispatch is an entry of one pallet or more: a release of that many pallets from
the lot.

2.2 A lot's pallets are on hand from its receipt date, and the entries of its
`dispatches` change them. A dispatched pallet is still on hand on the day it is
dispatched and is gone from the next day.

2.3 A working day is a Monday, Tuesday, Wednesday, Thursday or Friday that is
not one of the job's `holidays`.

2.4 A lot's storage weeks run in blocks of seven days from its receipt date:
its first storage week starts on the receipt date, its second seven days later,
and so on. A week's number is its place in that run. A billed week of a lot is
one of its storage weeks that starts within the period, from its start date
through its end date both included, and on whose first day the lot has pallets
on hand.

## 3. Rate cards

3.1 A client's rate card is revised from time to time, and each revision takes
effect on its effective date. The revision in force on a day is the latest
revision of the client whose effective date is on or before that day.

3.2 The rates of a storage week are those of the revision in force on the
week's first day. The rates of a receipt or a dispatch are those of the
revision in force on its date.

## 4. Storage

4.1 Each billed week is billed for the pallets the lot has on hand on the week's
first day.

4.2 The tiers of a storage scale take a lot's storage weeks by number: the first
tier takes as many weeks as its length, the second tier the next ones, and so
on, and the last tier takes all the rest. A billed week is billed at the rate of
the tier that takes its number. Tiers are not retroactive: a lot reaching a
later tier does not change the rate of its earlier weeks.

4.3 A lot's storage is the total its billed weeks are billed; a lot with no
billed weeks has a storage of nought.

4.4 A lot with billed weeks whose storage is below its client's `minimum` is
billed the minimum for its storage instead: its billed storage is the minimum.
Any other lot's billed storage is its storage.

4.5 A lot's peak is the largest number of pallets it has on hand on the first
day of one of its billed weeks.

## 5. Handling

5.1 A receipt dated within the period is billed for every pallet received, at
the receiving rate (`in`). A dispatch dated within the period is billed for
every pallet dispatched, at the dispatch rate (`out`).

5.2 A receipt or a dispatch dated on a day that is not a working day is billed
at the out-of-hours rate (`after_hours`) for every pallet, instead of its
receiving or dispatch rate.

5.3 A lot's handling is the total its receipt and its entries are billed.

## 6. Lot amounts

6.1 Storage and handling are billed as 4.4 and 5.3 give them.

6.2 A lot's energy surcharge is its client's `surcharge_percent` of its billed
storage, rounded as 1.3 says.

6.3 A lot's amount is its billed storage plus its handling plus its energy
surcharge. The statement's total is the total of its lots' amounts.

## 7. The statement

`tools/stockbill_run.py JOB.json` prints one JSON object with `statement` (the
job's `statement`), `lots` and `total`. `lots` holds one entry per lot, in the
job's order, with `id`, `client`, `storage_weeks` (the number of its billed
weeks), `peak`, `storage` (its billed storage), `handling`, `surcharge` and
`amount`. Counts and money are integers.

This schedule gives no other charge, credit or waiver.
