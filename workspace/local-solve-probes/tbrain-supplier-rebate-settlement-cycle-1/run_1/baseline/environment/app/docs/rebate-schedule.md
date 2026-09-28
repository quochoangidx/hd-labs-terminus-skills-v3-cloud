# Schedule R: Quarterly Rebate Settlement (edition R-4)

Schedule R to the distribution agreement between the supplier and the
distributor. It governs the settlement statement the distributor's rebate desk
draws up for each supplier account at the end of a calendar quarter. Where the
settlement package and this schedule disagree, the schedule is right. Rule
numbers stay the same from one edition to the next.

## 1. Units, rounding and limits

1.1 Money is kept in whole cents. When a rule takes a share of an amount, at a
rate in basis points or a percentage, the result is rounded to the nearest
cent, and an exact half cent goes up. A figure no rule takes a share of is not
rounded.

1.2 A date is written YYYY-MM-DD and days are calendar days. The quarters of a
year run January to March, April to June, July to September and October to
December; a quarter is written YYYY-Qn, as in 2027-Q3. A quarter includes its
first and its last day.

1.3 A job gives the tier table and the supplier accounts to be settled. The
table has 1 to 12 rows. Each row gives a threshold of 0 to 100,000,000,000
cents and a rate of 0 to 1,500 basis points; the first row's threshold is 0 and
each later row's threshold is higher than the one above it. A job has 1 to 100
accounts. Each has an account code of 1 to 16 characters that no other account
in the job shares, the quarter being settled, in the years 2020 to 2039, and
the account's net purchases in the same quarter a year before, 0 to
100,000,000,000 cents.

1.4 An account's purchase lines are the ledger export's invoice lines for the
supplier around the quarter: 0 to 400 lines, each giving its invoice date, 1 to
5,000 units and a unit price of 100 to 1,000,000 cents. The supplier raises the
invoice on the day the goods leave its warehouse. Full cartons go by road
freight; when the distributor asks for a few loose units picked from an open
carton, the supplier sends them by courier.

1.5 An account's returns are the goods the supplier took back: 0 to 100
returns, each giving the day it was taken back, 1 to 5,000 units and the unit
price they were bought at, 100 to 1,000,000 cents.

1.6 An account's price notices are the supplier's list-price changes for items
the distributor stocks: 0 to 50 notices, each giving the day the new price
takes effect, the old and the new unit price (the new price at least 1 cent and
below the old one, the old at most 1,000,000 cents) and the units the
distributor had on hand that day, 100 to 50,000. Besides real price cuts, the
supplier's price file carries tidy-ups of a few cents to a couple of dollars a
unit, made when it rounds a price or redoes a currency conversion.

1.7 An account's sales below cost are the distributor's sales of the
supplier's goods at less than its own unit cost: 0 to 200 sales, each giving
the day of the sale, 1 to 5,000 units, the distributor's unit cost of 100 to
1,000,000 cents and the unit price charged, at least 1 cent and below that
cost. Most are sales to the supplier's contract customers at the contract
price; the rest are counter sales where a clerk matched a competitor's price a
little under cost.

1.8 Every invoice date, return, price notice and sale of an account falls
between 45 days before its quarter's first day and 45 days after its last day.

## 2. Definitions

2.1 An account's quarter is the quarter the job names for it.

2.2 A carton shipment is a purchase line of 12 units or more. It travels by
road freight, and the distributor receives it on the fourth day after its
invoice date.

2.3 The value of a purchase line or a return is its units times its unit
price.

2.4 A price drop is a price notice that lowers the unit price by 250 cents or
more.

2.5 A contract sale is a sale below cost whose unit price charged is 100 cents
or more below the distributor's unit cost.

2.6 The tier an amount reaches is the last row of the tier table whose
threshold the amount is at or above. An amount below nought reaches no tier.

## 3. Purchases, returns and the volume rebate

3.1 A carton shipment counts toward the quarter in which the distributor
receives it.

3.2 Every purchase line counts toward exactly one quarter. An account's
purchases are the total value of the lines that count toward its quarter.

3.3 A return counts toward the quarter in which it was taken back, and it is
credited at its value less a handling charge of 40 cents a unit. An account's
returns are the total credited for the returns that count toward its quarter.

3.4 An account's net purchases are its purchases less its returns.

3.5 The rebate rate is the rate of the tier the net purchases reach, or nought
when they reach none.

3.6 The volume rebate is the rebate rate, in basis points, of the net
purchases.

## 4. Growth bonus

4.1 An account whose net purchases a year before were above nought, and whose
net purchases are 110 per cent or more of them, earns a growth bonus of 200
basis points of the amount by which its net purchases exceed them. Any other
account earns no growth bonus.

## 5. Price protection and chargebacks

5.1 A price drop that takes effect in the account's quarter earns a credit of
the amount the unit price was lowered by, times the units on hand.

5.2 A contract sale made in the account's quarter earns a chargeback of the
amount the unit price charged was below the unit cost, times the units.

5.3 Every price notice that takes effect in the account's quarter carries one
credit line, and every sale below cost made in it carries one chargeback line.
An account's price protection is the total of its credit lines, and its
chargebacks are the total of its chargeback lines.

## 6. Settlement

6.1 An account's settlement is its volume rebate, growth bonus, price
protection and chargebacks added together.

6.2 A settlement of 25,000 cents or more is paid in full. A smaller settlement
is not paid; the whole of it is carried to the account's next quarter.
