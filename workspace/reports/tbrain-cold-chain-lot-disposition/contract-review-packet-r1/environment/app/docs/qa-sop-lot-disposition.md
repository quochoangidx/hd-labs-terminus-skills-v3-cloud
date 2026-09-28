# QA-SOP-311 Lot disposition from cold-chain records

Halvern Biologics Distribution, Quality Assurance. Edition 5.

This procedure is how QA decides whether a finished-product lot that has
travelled through our distribution chain is released, quarantined or rejected,
from the temperature-logger exports of its shipment legs and the product's
stability record. Where the disposition tool and this procedure disagree, the
procedure governs. Rule numbers do not move between editions.

Some rules differ from common industry practice. Where they do, the rule says
so, and the procedure's figure is the one to use.

## 1 Units, rounding and limits

1.1 Temperatures are in degrees Celsius, given to one decimal place, and are
compared exactly as written. Times are whole minutes; a stamp names a minute of
Coordinated Universal Time. An hour is sixty minutes.

1.2 Every figure is worked out from unrounded figures, and every comparison in
section 6 uses unrounded figures. Reported hours are rounded to the nearest
hundredth of an hour (a whole number of minutes never falls halfway between
two hundredths), and the mean kinetic temperature to the nearest tenth of a
degree. Nothing else is rounded.

1.3 A temperature in kelvin is the temperature in degrees Celsius plus 273.15.

1.4 This procedure provides for jobs within these limits, and each limit
includes its ends:

- a job holds one stability record and from 1 to 200 lots, each lot id used
  once;
- a lot lists from 1 to 12 legs, no leg twice; one leg's export may serve
  several lots of a job;
- a leg's export holds from 2 to 20,000 readings, stamped in increasing order,
  consecutive stamps from 1 to 1,440 minutes apart;
- the first reading of each of a lot's legs after its first is stamped from 0
  to 2,880 minutes after the last reading of the leg before it;
- stamps fall from 2020-01-01T00:00 to 2039-12-31T23:59;
- a reading is from -40.0 to 60.0 degrees;
- the labelled lower limit is from -30.0 to 20.0 degrees, and the upper limit
  from 1.0 to 25.0 degrees above it;
- the record lists from 1 to 3 bands below the labelled range and from 1 to 3
  above it, each from 0.5 to 40.0 degrees wide, every end from -40.0 to 60.0
  degrees, laid out as 2.5 describes;
- the freeze point is from the lowest band's lower end to the labelled lower
  limit;
- the activation ratio is from 5,000 to 20,000 kelvin;
- a band's allowance is a whole number of hours from 0 to 2,000;
- the release certificate records from 0 to 120,000 minutes of prior time
  against any of the record's bands.

1.5 No lot's mean kinetic temperature, worked out as section 5 states, lies
within 0.001 degrees of the labelled upper limit or within 0.0005 degrees of a
value halfway between two tenths.

## 2 Definitions

2.1 The labelled range runs from the stability record's lower limit to its
upper limit, both limits included. A reading inside it is in range.

2.2 A leg is one journey of the lot between two custody points, recorded by
one logger export. A lot lists its legs in travel order.

2.3 Within one leg's export, each reading and the next reading of the same
export bound an interval, whose length is the number of minutes between their
stamps. The earlier reading opens the interval and the later one closes it.

2.4 A logged interval is an interval of 30 minutes or less.
A longer interval is a logger gap.

2.5 The stability record lists excursion bands below and above the labelled
range. The band nearest the range on each side has the range's limit as its
inner end, and each further band has the outer end of the band before it as
its inner end. A band below the range holds temperatures from its lower end up
to but not including its upper end. A band above the range holds temperatures
above its lower end up to and including its upper end. The table's span runs
from the lowest band's lower end to the highest band's upper end.

2.6 An excursion reading is a reading outside the labelled range and within the table's span.

2.7 A frozen reading is a reading below the record's freeze point.

2.8 Prior time is the minutes the lot's release certificate records against a
band for the time before the lot entered distribution.

## 3 Time on a leg

3.1 The minutes of a logged interval are attributed to the reading that opens it.

3.2 Each excursion reading is charged to the band that holds it. A band's time
on a leg is the total of the minutes attributed to the leg's readings charged
to that band.

3.3 A leg's unlogged time is the total length of its logger gaps.

## 4 Carrying allowances along the chain

4.1 The stability allowance of a band belongs to the lot, not to a leg. A
lot's time in a band is the total of that band's time over every leg of the
lot.

4.2 A band's remaining allowance is its allowance,
less the prior time the release certificate records against it,
less the lot's time in the band. It is reported in hours and may be below
nought.

4.3 A lot's unlogged time is the total of the unlogged time of its legs.

## 5 Mean kinetic temperature

5.1 The lot's mean kinetic temperature is worked out over every reading of
every leg of the lot. Each reading is weighted by the minutes attributed to
it, and its temperature is taken in kelvin. With H the record's
activation ratio (the activation energy divided by the gas constant), the
figure in kelvin is H divided by the negative natural logarithm of the
weighted mean of e raised to the power of minus H over the reading's kelvin
temperature; it is reported in degrees Celsius. Many sites use a fixed ratio of
about 10,000 kelvin; this procedure uses the product's own ratio from its
stability record.

## 6 Disposition

6.1 A lot is rejected when any of its readings is a frozen reading, or when
any band's remaining allowance is below nought.

6.2 A lot that is not rejected is quarantined when its mean kinetic
temperature is above the labelled upper limit, or when its unlogged time is
more than 120 minutes.

6.3 Any other lot is released.
