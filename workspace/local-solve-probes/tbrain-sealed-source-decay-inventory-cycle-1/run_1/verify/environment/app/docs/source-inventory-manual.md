# Carrow Institute, Radiation Protection Office
# Source Inventory Manual RPO-7 (fourth edition)

This manual sets out how the Office decay-corrects its sealed-source inventory to a
survey date and what the quarterly survey reports. The survey package `sealsrc`
exists to carry it out; where the two differ, the manual is right and the package
is wrong. Rule numbers are never reused or moved from one edition to the next.

## 1. Units, figures and terms

1.1 Activity is in becquerels (Bq). No figure is rounded at any stage: every
activity, sum and fraction is carried and reported at the full precision of the
arithmetic, and a location's sums are taken over its entries in inventory order.
A reported figure is taken as the manual's figure when it differs from it by no
more than one part in 10^9 of the manual's figure. That allowance is for reported
figures only: every comparison sections 1 to 7 make against a quantity, threshold,
limit or reading is made on the figures exactly as computed.

1.2 Where this manual counts days from one date to another, it counts actual
days of the Gregorian calendar: every month at its real length, and 29 February in
a leap year. (Thirty-day months belong to interest calculations, not to decay.)

1.3 The *elapsed time* of an entry is the number of days (1.2) from its reference
date to the survey date, for a survey date on or after the reference date.

1.4 Table 2 gives each half-life in days (d) or in years (y). A year of half-life
is 365.25 days.

1.5 This manual provides for inventories within the following limits, each of
which includes its endpoints: reference activities from 1 Bq to 1.0e14 Bq; every
date in an inventory (survey date, reference dates and wipe dates) from
1950-01-01 to 2099-12-31, with no wipe dated after the survey date; removable
activities of wipes from 0 Bq to 1.0e6 Bq; from 0 to 50 wipes of one entry;
location limits from 1 Bq to 1.0e18 Bq; from 0 to 5000 entries and from 1 to 200
storage locations in one inventory. Entry ids are unique, location ids are
unique, every entry names one of the inventory's locations, and every nuclide is
one Table 2 lists.

1.6 A *short-lived* entry is one whose nuclide has a half-life of 120 days or less.

1.7 A *leak test* of an entry is a wipe of the source whose removable activity is
below 185 Bq (0.005 microcurie). A wipe that picks up 185 Bq or more is not a
leak test. It stays on the entry's record as evidence of a leak, and section 5
still governs the entry: only its leak tests count there.

1.8 An entry is *licensed material* when its reference activity, the parent
figure on its certificate, is above the exempt quantity of its nuclide.
Licensing follows the certificate: an entry received as licensed material stays
licensed however far it decays, and one received at or below the quantity is
never licensed material, whatever its daughters add.

## 2. Nuclide data

Table 2. Half-life, exempt quantity, leak-test class and equilibrium daughter.

| Nuclide | Half-life | Exempt quantity (Bq) | Leak-test class | Daughter (branching fraction) |
|---|---|---|---|---|
| H-3 | 12.32 y | 1.0e9 | none | none |
| Na-22 | 2.6018 y | 1.0e6 | beta-gamma | none |
| P-32 | 14.268 d | 1.0e5 | beta-gamma | none |
| S-35 | 87.37 d | 1.0e8 | beta-gamma | none |
| Co-57 | 271.74 d | 1.0e6 | beta-gamma | none |
| Co-60 | 5.2713 y | 1.0e5 | beta-gamma | none |
| Ni-63 | 101.2 y | 1.0e8 | beta-gamma | none |
| Ge-68 | 270.95 d | 1.0e5 | beta-gamma | Ga-68 (1.0) |
| Sr-90 | 28.79 y | 1.0e4 | beta-gamma | Y-90 (1.0) |
| Cd-109 | 461.9 d | 1.0e6 | beta-gamma | none |
| I-125 | 59.49 d | 1.0e6 | beta-gamma | none |
| Ba-133 | 10.551 y | 1.0e6 | beta-gamma | none |
| Cs-137 | 30.08 y | 1.0e4 | beta-gamma | Ba-137m (0.944) |
| Ir-192 | 73.829 d | 1.0e4 | beta-gamma | none |
| Po-210 | 138.376 d | 1.0e4 | alpha | none |
| Am-241 | 432.6 y | 1.0e4 | alpha | none |
| Cf-252 | 2.645 y | 1.0e4 | alpha | none |

## 3. Decay correction

3.1 An entry's *current activity* is its reference activity decayed over its
elapsed time t: A = A_ref x 2^(-t/T), with T the nuclide's half-life in days.
On the reference date itself the current activity is the reference activity.

3.2 A daughter that Table 2 lists is taken to be in secular equilibrium with its
parent. Its activity is the parent's current activity times the branching
fraction; the certificate figure is the parent's alone. An entry whose nuclide
has no daughter listed has a daughter activity of nought.

3.3 An entry's *total activity* is its current activity plus its daughter
activity.

## 4. Exemption

4.1 An entry is *exempt* when its total activity is at or below the exempt
quantity of its nuclide. (The international "parent+" exemption values already
allow for daughters and are compared with the parent alone. The quantities in
Table 2 are the Office's own and are compared with the total.)

## 5. Leak tests

5.1 An entry is *leak-testable* when its current activity reaches the threshold
of its nuclide's leak-test class: 3.7e6 Bq (3.7 MBq) or more for class
beta-gamma, 3.7e5 Bq (0.37 MBq) or more for class alpha. A nuclide of class none
is never leak-testable.

5.2 A leak-testable entry is *due* for a leak test when no leak test is on record
for it, or when its last leak test, the latest by date, was more than 182 days
(1.2) before the survey date. An entry that is not leak-testable is never due.
(Most licences say six months; the Office fixes 182 days so that the interval
never depends on the month.)

## 6. Storage locations

6.1 A location's *held activity* is the sum of the current activities of the
licensed material kept there, and its *source count* is the number of those
entries. Daughter activity is not part of the held activity: location limits are set on
parent activity.

6.2 A location's *fraction of limit* is its held activity divided by its limit.
The location is *over its limit* when its held activity is more than its limit.

## 7. Decay-to-disposal

7.1 A short-lived entry is *eligible for decay-to-disposal* once ten half-lives
have elapsed, that is, when its elapsed time is ten times its half-life or more.
An entry that is not short-lived is never eligible. (Current regulations ask for a
survey reading that cannot be told from background; the Office keeps the older
ten-half-life rule for its own records.)

## 8. The survey report

8.1 The report lists every entry of the inventory, in inventory order, and every
storage location, in inventory order, with the figures and determinations of
sections 3 to 7.
