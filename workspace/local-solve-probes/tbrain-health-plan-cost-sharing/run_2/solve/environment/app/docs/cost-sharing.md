# Cost sharing in `costshare`

This note is the design authority for how `costshare` splits a claim line
between the plan and the member, and for what each line leaves on the running
totals. One `Adjudicator` serves one family for one benefit year and prices that
family's lines in the order they arrive; its `Ledger` holds the totals.

## 1. Money and rates

1.1 Every amount is a whole number of cents: settings, allowed amounts, member
parts and totals alike.

1.2 A coinsurance rate is written in basis points, from 0 for none of an amount
to 10000 for all of it.

1.3 The share of an amount at a rate from 0 to 10000 is the amount times the
rate divided by 10000, rounded to the nearest whole cent. A result exactly
halfway between two cents goes to the even cent. `share(amount, rate)` computes
it.

## 2. Plans, lines and results

2.1 A `Plan` carries a member deductible, a family deductible, a coinsurance
rate, an office copay, a member out-of-pocket maximum and a family out-of-pocket
maximum.

2.2 A `Line` names the member it is for, its kind and its allowed amount, which
is what the plan recognises for the service. A line's kind is `preventive`,
`office` or `facility`; a line of any other kind is priced as a facility line.

2.3 A line's `Result` has three member parts: deductible, copay and
coinsurance. Their sum is the member's cost share on the line, and the plan
pays the allowed amount less that cost share.

## 3. Preventive lines

A preventive line costs the member nothing. All three parts are zero, the plan
pays the whole allowed amount, and the line adds nothing to any total.

## 4. Office lines

4.1 An office line charges the plan's office copay. When the allowed amount is
above zero but below the copay, the copay part is the allowed amount instead.

4.2 The deductible does not apply to an office line and no coinsurance is
taken on it: the plan pays whatever the copay part leaves.

## 5. Facility lines

5.1 A facility line first meets what is left of the member's deductible. Its
deductible part is the smaller of the allowed amount and what is left.

5.2 What is left is the member deductible less the deductible parts already on
the member's deductible total. On a plan with a family deductible above zero,
what is left is the smaller of that and the family deductible less the family's
deductible total.

5.3 The coinsurance part is the share (1.3), at the plan's coinsurance rate, of
what the deductible part, before any cut (6.2), leaves of the allowed amount. A
facility line has no copay part.

## 6. Out-of-pocket maximums

6.1 Each out-of-pocket maximum above zero, the member's and the family's,
leaves room for a line's cost share: the maximum less the out-of-pocket total
it is matched with, which is the member's total for the member maximum and the
family's total for the family maximum.

6.2 When the cost share is larger than the smallest room, the excess is cut.
It comes off the coinsurance part first, then the copay part, then the
deductible part. No part is taken below zero, and a part at or below zero gives
nothing to the cut. The plan pays what is cut.

## 7. Totals

7.1 Once a line is priced and cut, its deductible part is added to the
member's deductible total and to the family's.

7.2 Its whole cost share is added to the member's out-of-pocket total. On a
plan with a family maximum above zero, the family's out-of-pocket total is the
sum of its members' out-of-pocket totals.

7.3 `Ledger.record(member, deductible, copay, coinsurance)` adds one priced
line's parts to the totals, and `Adjudicator.deductible_left(member)` gives what
is left of the member's deductible (5.2). `share`, `Ledger.record` and
`deductible_left` follow this note when they are called directly, not only
through `Adjudicator.adjudicate`.
