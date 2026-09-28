# Tariff rules DT-3: import demurrage and detention

These rules set what the carrier charges a consignee for an import container
kept at the discharge terminal (demurrage) and kept away from the carrier once
it has left the terminal (detention), and how the billing statement shows it.
Where the billing package and these rules disagree, the rules govern. Rule
numbers are quoted in disputes and do not move between editions.

## 1. Units, rounding and limits

1.1 A date is a calendar date written `YYYY-MM-DD`. A figure counted in days is
a whole number of calendar dates; the hour of a move plays no part.

1.2 Money is in whole US cents. A scale rate is in cents per day.

1.3 The one figure that can fall between two whole cents is a discount (6.2).
It is rounded to the nearest cent, and an exact half cent is rounded up.
Nothing else is rounded.

1.4 These rules provide for jobs within the following limits, and for no
others.

- The `cut_off` is a date from 2001-03-01 to 2099-12-31. Every move, holiday,
  closure and effective date in the job is on or before the cut-off and at most
  400 days before it.
- A job has from 1 to 300 containers with distinct ids. A container's size is
  `"20"` or `"40"`, and its contract is one of the job's contracts.
- A job has from 1 to 20 contracts. A contract gives from 0 to 20 terminal free
  days, from 0 to 30 merchant free days and a discount of 0 to 50 percent, all
  whole numbers, and from 1 to 6 revisions whose effective dates strictly
  increase down the list.
- Every revision holds a scale for each stage and each size. A scale has from 1
  to 5 tiers. Every tier but the last has a length from 1 to 60 days; the last
  tier has no length. Every rate is a whole number from 0 to 100,000.
- A history holds exactly one `DISCHARGE`; at most one `GATE_OUT`, not dated
  before the discharge; and at most one `EMPTY_RETURN`, only when there is a
  gate-out and not dated before it.
- `holidays` and `closures` each hold from 0 to 60 distinct dates.

## 2. Stays

2.1 A container is discharged on the date of its `DISCHARGE` move, leaves the
terminal on the date of its `GATE_OUT` move and is returned on the date of its
`EMPTY_RETURN` move.

2.2 A container has up to two stages. Its terminal stage, which earns
demurrage, starts on the day it is discharged and ends on the day it leaves the
terminal. Its merchant stage, which earns detention, starts on the day it leaves
the terminal and ends on the day it is returned. A container that has not left
the terminal has no merchant stage. The gate-out date is a day of both stages.

2.3 A stage has ended when the move that ends it is in the history. A stage
that has not ended is running.

2.4 A stage's days are the dates from its first day through its last day, both
included. The last day of a stage that has ended is the date it ended; a
running stage's days run through the cut-off date.

2.5 A working day is a Monday, Tuesday, Wednesday, Thursday or Friday that is
not one of the job's `holidays`. A closure day is one of the job's `closures`:
a day the terminal's gates stayed shut.

## 3. Free time

3.1 The terminal stage's free days are used one per working day, starting on
its first day; a closure day uses none. Its last free day is the date on which
the last of the contract's terminal free days is used.

3.2 The merchant stage's free days are used one per calendar date, starting on
its first day. Its last free day is the date on which the last of the
contract's merchant free days is used.

3.3 With no free days, a stage's last free day is the day before its first day.
Free time is counted out in full whether or not the stage lasts that long.

## 4. Chargeable days

4.1 A stage's chargeable days are its days after its last free day. A closure
day is not a chargeable day of the terminal stage. Weekends and holidays after
the last free day are chargeable days like any other.

## 5. Charges

5.1 A contract's rate sheet is revised from time to time, and each revision
takes effect on its effective date. A revision is in force on a day when it is
the latest revision of its contract whose effective date is on or before that
day. On a day before a contract's earliest effective date none of its revisions
is in force, and where a rule needs the revision in force on such a day, it
gives no rule for the value it defines.

5.2 The scale of a stage that has chargeable days is the scale for that stage
and the container's size in the revision in force on the stage's first
chargeable day.

5.3 A scale's tiers take a stage's chargeable days in date order: the first
tier takes as many of them as its length, the second tier the next ones, and
so on, and the last tier takes all the rest. Each chargeable day is charged at
the rate of the tier that takes it. Tiers are not retroactive: reaching a later
tier does not change the rate of the days before it.

5.4 A stage's amount is the total its chargeable days are charged; a stage with
no chargeable days has an amount of nought. The amount of a stage that has
ended is its charge. The amount of a running stage is an accrual: the
statement shows it, but it is not a charge, since the stage can still run on.
Where a rule needs the charge of a running stage, it gives no rule for the
value it defines.

## 6. Containers and the statement total

6.1 A container's amount is the total of its stages' amounts.

6.2 A container's discount is its contract's discount percentage of the total
of its stages' charges, rounded as 1.3 says.

6.3 A container's net is its amount less its discount. The statement's total
is the total of its containers' nets.

## 7. The statement

`tools/ddbill_run.py JOB.json` prints one JSON object with `invoice` (the
job's `invoice`), `containers` and `total`. `containers` holds one entry per
container, in the job's order, with `id`, `terminal`, `merchant` (`null` for a
container with no merchant stage), `amount`, `discount` and `net`. Each stage
entry holds `first_day`, `last_free_day`, `days` (the number of its days),
`chargeable` (the number of its chargeable days), `amount` and `status`
(`"ended"` or `"running"`). Dates are `YYYY-MM-DD` strings; counts and money
are integers.

These rules give no other charge, credit or waiver.
