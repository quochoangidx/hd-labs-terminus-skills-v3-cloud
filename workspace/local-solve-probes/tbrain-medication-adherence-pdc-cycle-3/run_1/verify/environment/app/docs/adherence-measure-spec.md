# Adherence Measure Specification AM-2

Harrowgate Community Health Plan, pharmacy quality programme. Third edition.

This specification is how the plan turns one measurement year of pharmacy
claim lines into each member's proportion of days covered (PDC) for each drug
class, and into each class's adherence rate. Where the measure package and
this specification disagree, the specification governs. Rule numbers do not
move between editions.

The plan's measure is close to the national adherence measures but not the
same. Where it differs, the rule says so, and the plan's rule is the one to
use.

## 1 Units, rounding and limits

1.1 A day is a calendar day, written YYYY-MM-DD. A length of time is a whole
number of days, and a span from one day to another includes both of them. The
measurement year is the calendar year the claims file names.

1.2 Every figure is worked out from unrounded figures. Every PDC and every
adherence rate the report gives is a percentage rounded to the nearest tenth,
an exact half going up, and adherence is judged on the PDC as reported.
Nothing else is rounded.

1.3 This specification provides for claims files within these limits, and each
limit includes its ends:

- the measurement year is from 2000 to 2099;
- a file lists from 1 to 100 members, with claim lines under at most 40
  different class codes, and no two members share an id;
- a member id is 1 to 12 characters, each a capital letter, a digit or a
  hyphen; a drug code is 1 to 11 digits; a class code is 1 to 8 characters,
  each a capital letter or a digit, and every claim line of one drug code in a
  file carries the same class code;
- a member has from 0 to 400 claim lines, each with a fill date in the
  measurement year and a days supply from 0 to 365 days;
- a member has from 0 to 10 stays, each with its admission and discharge in the
  measurement year and its discharge no earlier than its admission; no two
  stays of one member share a day, and a member has at most 60 stay days.

## 2 Terms

2.1 A claim line is one entry of a member's claims: the day the pharmacy
keyed it (its fill date), the drug, the drug's class and the days supply. A
fill is a claim line that dispensed a supply, which is one with a days supply
of one day or more.

2.2 The supply limit is 100 days. A fill whose days supply is no more than the
supply limit is a fill within the limit.

2.3 A member's index date for a class is the fill date of the member's
earliest fill of that class.

2.4 A member is in the measure for a class when the member has fills of the
class on two or more different fill dates and the index date is no later
than 2 October of the measurement year. (The national measures accept two
fills dispensed on one day; the plan does not.)

2.5 The treatment period of a member in the measure runs from the index date
to the last day of the measurement year.

2.6 A stay day is a day from a stay's admission to its discharge.

2.7 A class is reportable when ten or more members are in the measure for it.
The rate base of a reportable class is the number of members in the measure
for it.

## 3 Covered days

3.1 Every fill covers one or more consecutive days, beginning on its start
day. A fill within the limit covers as many days as its days supply.

3.2 A member's fills of one drug are taken in the order of their fill dates,
and fills of one fill date in the order the file lists them. A fill's start
day is its fill date, unless an earlier fill of the same drug covers that
date; then its start day is the day after the last day that the member's
earlier fills of that drug cover. Fills of different drugs never move one
another.

3.3 A day is covered for a class when a fill of that class covers it.

3.4 A member's covered days for a class are the days of the treatment period
that are covered for the class and are not stay days.

## 4 PDC and adherence

4.1 A member's period days for a class are the days of the treatment period
that are not stay days. The member's PDC for the class is 100 times the
covered days divided by the period days. (The national measures take stay
days out of the covered days only; the plan takes them out of the period days
as well.)

4.2 A member is adherent for a class when the member is in the measure for the
class and the PDC is 80.0 or more.

## 5 Classes

5.1 A class's adherence rate is 100 times the number of members adherent for
it divided by its rate base.
