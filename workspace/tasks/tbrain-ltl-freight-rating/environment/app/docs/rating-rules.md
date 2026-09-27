# Rating an LTL shipment with `freightrate`

This note is the design authority for how `freightrate` prices a less-than-
truckload shipment against a class tariff: how each line's freight class comes
from its density, which weight break the shipment rates at, when rating at the
next break's minimum weight is cheaper, and how the discount, minimum charge,
fuel surcharge and accessorials build the total. The functions named in each
section follow it when they are called directly, not only through
`rate_shipment`.

## 1. Units

1.1 Weights are whole pounds, volumes are cubic feet, money is whole cents.
A rate is cents per hundred pounds. A percentage is written in basis points,
where 10000 is the whole.

1.2 Wherever a rule takes a fraction of a whole number of cents, the result is
rounded to the nearest cent, and a result exactly halfway between two cents
goes up to the larger one. `cents(value)` does this.

## 2. Freight class from density

2.1 A line's density is its weight divided by its volume, in pounds per cubic
foot. `density(weight, volume)` computes it.

2.2 The density table lists `(minimum density, class)` rows from the densest
class down. A density takes the class of the first row whose minimum it reaches
or exceeds. `class_for(density)` looks it up.

## 3. The tariff and its weight breaks

3.1 A `Tariff` has a list of break minimums in increasing order, a rate for
every class at every break, and a minimum charge.

3.2 A weight rates at the break with the greatest minimum that the weight
reaches or exceeds. `Tariff.break_index(weight)` gives that break's position in
the list.

## 4. The linehaul charge

4.1 The shipment's weight is the total of its lines' weights, and it rates at
the break for that total (3.2). Every line is charged at that one break.

4.2 A line's charge at a break is its weight times its class's rate at that
break, divided by 100, in cents (1.2). The gross charge at a break is the total
of the line charges.

4.3 Unless the shipment rates at the last break, it is also rated as if it
weighed the next break's minimum. The deficit weight is that minimum less the
shipment's weight. The charge at the next break is the gross charge of the
lines at the next break plus the deficit weight charged at the next break's
rate for the lowest-rated class among the lines, the class whose rate there is
smallest. When that charge is less than the gross charge at the shipment's own
break, it is the gross charge, and the quote records the deficit weight;
otherwise the deficit weight is 0.

## 5. Discount and minimum charge

5.1 The discount is the gross charge times the discount percentage (1.2). The
net linehaul is the gross charge less the discount.

5.2 A net linehaul below the tariff's minimum charge is raised to it.

## 6. Fuel surcharge

6.1 The fuel table lists `(from price, percentage)` rows in increasing order of
from price, prices in cents per gallon. A row covers diesel prices from its
from price up to, but not including, the next row's from price; the last row
covers every price from its own from price up. `fuel_percentage(table, price)`
gives the percentage of the row that covers the price.

6.2 The fuel surcharge is the net linehaul, after the minimum charge, times
that percentage (1.2).

## 7. Accessorials and the total

7.1 Accessorial charges are flat amounts in cents. They take no discount and
no fuel surcharge.

7.2 `rate_shipment` returns a `Quote` whose `total` is the net linehaul plus the
fuel surcharge plus the accessorials.
