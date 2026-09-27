# Rental Charges Manual RC-3

Pellham Car & Van Hire, counter and billing office. Third edition.

This manual is how a closed rental agreement is turned into the charges on
the customer's bill. Where the billing package and this manual disagree, the
manual governs. Rule numbers do not move between editions.

## 1 Units, rounding and limits

1.1 Money is a whole number of cents. A time is a local date and time to the
minute, written YYYY-MM-DDTHH:MM, and a length of time is a whole number of
minutes. Odometer readings and distances are whole miles. A fuel level is a
whole number of eighths of a tank, from 0 (empty) to 8 (full).

1.2 Every charge is worked out from unrounded figures and is a whole number of
cents. The tax is rounded to the nearest cent, an exact half cent going up.
Nothing else is rounded.

1.3 This manual provides for agreement files within these limits, and each
limit includes its ends:

- a file lists from 1 to 200 agreements, and no two share an id; an id is 1 to
  10 characters, each a capital letter, a digit or a hyphen;
- every time falls in the years 2000 to 2099, and an agreement comes back from
  1 minute to 86,400 minutes (60 days) after it went out;
- an odometer reading is from 0 to 999,999, and an agreement's miles driven
  are at most 20,000;
- a fuel level is from 0 to 8;
- a day rate is from 100 to 100,000 cents, a mile rate from 0 to 500 cents and
  a fuel rate from 0 to 2,000 cents.

## 2 Terms

2.1 A rental's length is the number of minutes from the time the car went out
to the time it came back.

2.2 A day rental is a rental whose length is 1,440 minutes or more.

2.3 A day rental's charged days are its whole days of 1,440 minutes, and one
more day when the minutes left over are more than 59. Up to 59 minutes past a
whole day are free.

2.4 The allowance days of a rental are the charged days of a day rental.

2.5 A rental's miles driven are the odometer reading when the car came back
less the reading when it went out. The odometer turns over from 999,999 to 0,
so when the reading coming back is the smaller one, 1,000,000 is added.

2.6 A refuelling rental is a rental whose car came back with fewer eighths than
it went out with. Its eighths short are the difference.

## 3 Charges

3.1 A rental's time charge is its charged days times the day rate.

3.2 A rental's mileage allowance is 150 miles for each allowance day. The
mileage charge is the mile rate for each mile driven beyond the allowance.
(The old counter card gave 100 miles a day; the allowance was raised.)

3.3 A refuelling rental's fuel charge is the fuel rate for each eighth short,
plus a refuelling fee of 1,500 cents.

## 4 Tax and total

4.1 A rental's tax is 8.25 per cent of its time charge plus its mileage charge.
Fuel is not taxed.

4.2 A rental's total is its time charge, mileage charge, fuel charge and tax
added together.

4.3 A file's revenue is the sum of its rentals' totals, and its tax is the sum
of their taxes.
