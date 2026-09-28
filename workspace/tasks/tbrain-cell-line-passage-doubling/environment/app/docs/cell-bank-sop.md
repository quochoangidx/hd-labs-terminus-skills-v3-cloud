# SOP CB-3: passage log and population doubling level

Kestrel Hill Cell Culture Core. This procedure says how the core turns a line's passage
log into the lineage report that goes into the line's file: the passage number,
doublings, population doubling level (PDL) and limit flag of every culture, and the
stock and PDL of every bank. Where the `cellbank` package and this SOP disagree, the
SOP is right. Rule numbers are quoted in deviation reports and do not change between
editions.

## 1. Units, ranges and rounding

1.1 Cell numbers, passage numbers and vial numbers are whole numbers, written as JSON
integers in the log and in the report. A viability is a percentage of the cells counted
that are alive, written with at most one decimal place. Doublings, PDL and age are in
population doublings. Nothing in this SOP is rounded: every figure is reported as
calculated.

1.2 A passage log is a JSON object with `lines` and `records`.

1.3 `lines` holds one to four cell lines. Each has a distinct `name`, a `seed_pdl` from
0 to 100 (the PDL of the supplier's seed stock), a whole `seed_passage` from 0 to 50,
and a `max_pdl`, the highest PDL the line is approved to, from 10 to 300 and at least
`seed_pdl` + 5.

1.4 `records` holds one to four hundred records, in the order the work was done. Every
record has a distinct `id` and a `kind`:

- `thaw`: a vial thawed and counted. `line` names its line; `vial` is the `id` of the
  earlier `freeze` record the vial comes from, or `null` for a vial of the supplier's
  seed stock; `cells` and `viability` are the count of the thawed suspension.
- `culture`: a vessel seeded, grown and harvested. `source` is the `id` of an earlier
  `thaw` or `culture` whose suspension seeded it; `seeded` is the number of cells put
  into the vessel; `harvested` and `viability` are the count of its harvest.
- `freeze`: vials frozen from a harvest. `source` is the `id` of an earlier `culture`;
  `bank` names the bank the vials go into; `vials` is how many were frozen.

1.5 `cells`, `seeded` and `harvested` are from 1,000 to 10^9. A viability is from 1.0
to 100.0. `vials` is from 1 to 500. A culture's harvest may seed any number of later
cultures and freezes. Each `thaw` of a bank vial uses one vial, and no freeze has more
of its vials thawed than it froze. A bank holds vials of one line only, and a thaw's
`line` is the line of its vial. Along every lineage the PDL stays from -100 to 1,000,
and no culture's age (section 5) lies within 10^-6 of its line's `max_pdl` or of
`max_pdl` - 3.

## 2. Terms

2.1 A **suspension** is a batch of loose cells that has been counted: the harvest of a
culture, or a thawed vial.

2.2 A **count** is the number of cells in a suspension together with its viability. A
harvest's count is its culture's `harvested` with that record's `viability`; a thawed
vial's count is the thaw's `cells` with its `viability`.

2.3 A count whose viability is 70.0 or more is a **valid count**. The **viable count**
of a valid count is its number of cells multiplied by its viability and divided by 100.

2.4 A culture's **seed** is the `seeded` cells, drawn from its **source suspension**:
the harvest of the culture its `source` names, or the thawed vial its `source` names. A
seed is counted at the viability of the count of its source suspension.

2.5 A **vial** is one cryovial of a `freeze` record. It is **in stock** from its
freeze until a thaw uses it. A **bank** is every vial frozen under one `bank` name, and
a bank is **in use** while at least one of its vials is in stock. A thaw whose `vial` is
`null` uses a **supplier vial**, which belongs to no bank.

## 3. Doublings

3.1 A culture's **doublings** are the base-two logarithm of the viable count of its
harvest divided by the viable count of its seed.

3.2 A culture harvested with fewer viable cells than its seed held has doublings below
nought. They are counted as they are.

## 4. Passage number and PDL

4.1 Every suspension has a passage number and a PDL. A harvest's passage number is one
more than the passage number of its culture's source suspension. Its PDL is the PDL of
that source suspension plus the culture's doublings. A culture is reported with the
passage number and PDL of its harvest.

4.2 A thawed vial has the passage number and PDL of the harvest its freeze was taken
from: thawing is not a passage. (Some laboratories add one to the passage number at a
thaw. The core does not.) A supplier vial has its line's `seed_passage` and `seed_pdl`.

4.3 Passage numbers and PDL follow the lineage, from each record to its `source` or
`vial`, never the order of the log: two cultures seeded from one harvest start from the
same figures, whatever else was logged between them.

## 5. Age and limit flags

5.1 The **age** of a suspension is the highest PDL reached along its lineage up to and
including it: a harvest's age is the greater of its own PDL and its source suspension's
age; a thawed vial has the age of the harvest its freeze was taken from; a supplier
vial's age is its line's `seed_pdl`. A culture that lost cells lowers the PDL, not the
age.

5.2 A culture's flag is judged on the age of its harvest: `LIMIT` when the age is above
its line's `max_pdl`; `NEAR` when it is above `max_pdl` - 3 and not above `max_pdl`; an
empty string otherwise.

## 6. Banks

6.1 A bank's **vials left** is the number of its vials in stock at the end of the log:
every vial frozen into it less every vial thawed from it.

6.2 A vial's PDL is the PDL of the harvest its freeze was taken from. The **PDL** of a
bank in use is the highest PDL of its vials in stock.

## 7. The report

7.1 `python3 tools/cellbank_run.py LOG.json` prints one JSON object:

- `cultures`: one entry per `culture` record, in log order, with `id`, `line`,
  `passage` (an integer), `doublings`, `pdl` and `flag`;
- `banks`: one entry per bank, in the order of each bank's first `freeze` record, with
  `bank`, `line`, `vials_left` (an integer) and `pdl`.

7.2 A culture's `line` is the line at the root of its lineage. Numbers are not rounded.
These rules add no other correction, exclusion or guard.
