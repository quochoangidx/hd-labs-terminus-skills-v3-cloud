# Cycle Count Procedure CC-2

Farrow Lane Distribution Centre, inventory control. Second edition.

This procedure is how a finished cycle count is turned into the variance
report the inventory controller signs. Where the counting package and this
procedure disagree, the procedure governs. Rule numbers do not move between
editions.

## 1 Units, rounding and limits

1.1 Quantities are whole units. Money is a whole number of cents.

1.2 Every figure is worked out from unrounded figures.

1.3 This procedure provides for count sheets within these limits, and each
limit includes its ends:

- a sheet lists from 1 to 300 lines, and no two lines share a SKU; a SKU is 1
  to 12 characters, each a capital letter, a digit or a hyphen;
- a line's class is one capital letter;
- a system quantity, a count and a recount are each from 0 to 100,000 units,
  and a line either has a recount or has none (null);
- a unit cost is from 1 to 1,000,000 cents.

## 2 Terms

2.1 A line's final count is its recount when a recount was taken, and its
count otherwise.

2.2 A line's variance is its final count less its system quantity. A variance
below nought is a shortage; one above nought is a surplus.

2.3 A graded item is a line of class A, B or C. The tolerance of a graded
item is nought units for class A, 2 per cent of its system quantity for class
B, and 5 per cent of its system quantity for class C, each a whole number of
units with any fraction of a unit dropped.

2.4 A line is within tolerance when its variance, taken without its sign, is
no more than its tolerance.

## 3 Report

3.1 A line within tolerance is "ok". A line outside tolerance that has no
recount is "recount". A line outside tolerance that has a recount is
"adjust", and is an adjusted line.

3.2 A line's value is its variance times its unit cost.

3.3 An adjusted line books its variance: the units posted to stock are its
variance.

3.4 A sheet's shrink is the sum, over its adjusted lines that are shortages,
of the shortage's value taken without its sign. A surplus does not reduce
shrink.
