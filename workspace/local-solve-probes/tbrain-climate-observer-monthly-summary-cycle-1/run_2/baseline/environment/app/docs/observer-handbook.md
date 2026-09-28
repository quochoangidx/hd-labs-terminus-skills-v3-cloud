# Cooperative observer network handbook CN-7, part 3: the monthly station summary

This part sets how the network turns an observer's monthly form into the station's monthly
climatological summary. Where the summary package and this part disagree, this part governs. Section
numbers are quoted in station correspondence and do not move between editions.

## 1. Units, entries, rounding and limits

1.1 Temperatures are in degrees Fahrenheit and tenths. The form enters a temperature as the observer wrote
it, with one decimal place (`71.3`, `-4.0`, `0.0`), or `M` when the observer has no reading.

1.2 Precipitation is in inches and hundredths. The form enters an amount with two decimal places (`0.37`,
`0.00`, `12.40`), `T` for a trace, or `M` when the observer has no reading. A trace is precipitation that
fell but was too little to measure; it counts as nought wherever this part adds or compares amounts.

1.3 When the observer could not read the gauge at an observation, the form enters `A` for that day's
precipitation. The amount the observer enters at the next observation at which the gauge is read is an
accumulated amount: all the precipitation that fell since the gauge was last read.

1.4 A figure that this part gives to tenths, to hundredths or to the whole degree, and that falls between
two such values, is rounded to the nearer of them; an exact half goes to the higher of the two, for
figures below nought as well. No other figure is rounded.

1.5 This part provides for forms within the following limits, and for no others.

- The form's `month` is from 1950-01 to 2099-12.
- A form holds from 1 to 40 stations with distinct ids. A station's `hour` is a whole number from 0 to 23.
- A station's `days` holds exactly one entry for each day of the month, in date order, and its `next`
  holds the station's first observation of the following month.
- Every temperature entered is from -60.0 to 130.0. Every precipitation amount entered, accumulated or
  not, is from 0.00 to 20.00.
- An `A` is followed, in `days` or in `next`, by another `A` or by an amount or a `T`, never by an `M`;
  a station has at most six `A` entries in a row, and `next` is never `A`. The gauge was read at the
  last observation of the month before, so the first entry of `days` is never an accumulated amount.

## 2. Terms

2.1 An observation is a station's daily reading, taken at its observation hour (`hour`, local standard
time). An observation's form day is the day of the entry it is written on; `next` is written on the first
day of the following month.

2.2 An observation day is the 24 hours that end at an observation. A morning observation is one taken at
an hour from 0 through 11; every other observation is an afternoon observation.

2.3 A day's maximum and a day's minimum are the highest and the lowest temperature of one observation
day, as read at the observation that ends it.

2.4 A day's precipitation is the precipitation of one observation day, as entered at the observation that
ends it.

2.5 A day of the month is credited the readings that section 3 assigns to it. A day's mean temperature is
the average of the maximum and the minimum credited to it; a day credited no maximum or no minimum has no
mean temperature.

2.6 A day of the month lacks a maximum when no maximum is credited to it, and lacks a minimum when no
minimum is credited to it.

2.7 A month is complete for temperature when no more than five of its days lack a maximum and no more than
five of its days lack a minimum.

## 3. Crediting readings to days

3.1 A day's maximum read at a morning observation is credited to the day before its form day, the
calendar day on which most of its observation day fell. A day's maximum read at an afternoon observation
is credited to its form day.

3.2 A day's minimum is credited to its form day at every observation hour.

3.3 A day's precipitation is credited as a day's maximum is: to the day before its form day when it is
entered at a morning observation, and to its form day when it is entered at an afternoon observation.

3.4 A reading credited to a day outside the month plays no part in the month's summary.

## 4. Temperature

4.1 The month's mean maximum is the mean of the maxima credited to its days, to tenths, and its mean
minimum is the mean of the minima credited to its days, to tenths. A month with no maximum credited has
no mean maximum, and a month with no minimum credited has no mean minimum.

4.2 The month's highest temperature is the highest maximum credited to one of its days, with that day,
and its lowest temperature is the lowest minimum credited to one of its days, with that day. When the
highest or the lowest is credited to more than one day, the latest of those days is given.

4.3 A complete month's mean temperature is the average of its mean maximum and its mean minimum, as 4.1
gives them, to tenths.

4.4 A day's degree days are worked from its mean temperature rounded to the whole degree. Its heating
degree days are 65 less that rounded mean, and its cooling degree days are that rounded mean less 65;
either is nought when the result is below nought. The month's heating degree days are the total of its
days' heating degree days, and its cooling degree days the total of its days' cooling degree days.

4.5 The summary counts the month's days credited a maximum of 90.0 or above, the days credited a maximum
of 32.0 or below, the days credited a minimum of 32.0 or below, and the days credited a minimum of 0.0 or
below.

## 5. Precipitation

5.1 A day's credited precipitation is the total of the precipitation credited to it.

5.2 The month's precipitation is the total of its days' credited precipitation.

5.3 A precipitation day is a day of the month whose credited precipitation is 0.01 inch or more. The
summary counts the month's precipitation days, the days whose credited precipitation is 0.10 inch or
more, and the days whose credited precipitation is 1.00 inch or more.

5.4 The month's greatest precipitation is the largest credited precipitation of one of its precipitation
days, with that day; when it is credited to more than one day, the latest of those days is given. A month
with no precipitation day has no greatest precipitation.

## 6. The summary

`tools/coopsum_run.py FORM.json` prints one JSON object with `network` and `month` (the form's own) and
`stations`, which holds one object per station in the form's order, with these keys:

- `id`: the station's id.
- `complete`: `true` when the month is complete for temperature (2.7), otherwise `false`.
- `lacking_max`, `lacking_min`: the numbers of the month's days that lack a maximum and that lack a
  minimum (2.6).
- `mean_max`, `mean_min`: the mean maximum and mean minimum (4.1), `null` for a month that has none.
- `mean`: the month's mean temperature (4.3).
- `highest`, `highest_day`, `lowest`, `lowest_day`: the highest and lowest temperatures and their days
  (4.2), `null` for a month with no maximum, or no minimum, credited.
- `heating_dd`, `cooling_dd`: the month's heating and cooling degree days (4.4).
- `days_max_90`, `days_max_32`, `days_min_32`, `days_min_0`: the four counts of 4.5, in that order.
- `precip`: the month's precipitation (5.2).
- `precip_days`, `precip_days_10`, `precip_days_100`: the three counts of 5.3.
- `greatest`, `greatest_day`: the greatest precipitation and its day (5.4), `null` for a month with no
  precipitation day.

A temperature is a JSON number equal to the figure in tenths, a precipitation figure a JSON number equal
to the figure in hundredths, counts and degree days are integers, and days are written `YYYY-MM-DD`.
