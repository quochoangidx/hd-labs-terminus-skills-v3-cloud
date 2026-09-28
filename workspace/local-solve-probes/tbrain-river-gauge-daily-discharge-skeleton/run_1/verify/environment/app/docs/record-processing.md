# Processing a stage record with `gaugeflow`

This note is the design authority for how `gaugeflow` turns a gauge's stage
record into discharge: the shifts applied to recorded stage, the rating that
converts stage to discharge, and the daily means, volumes and peaks computed
from the resulting series. The functions named in each section follow it when
they are called directly, not only through `daily_values`.

## 1. Times, stages and series

1.1 Times are whole seconds from the station's epoch. Day `d` is the half-open
span from `86400 * d` up to, but not including, `86400 * (d + 1)`.

1.2 A reading is a time and a recorded stage in metres. A record is a list of
readings in time order; two readings may share a time.

1.3 A series is a list of `(time, value)` points in time order, such as a
discharge series in cubic metres per second. Two points may share a time.

## 2. Stage shifts

2.1 A shift table is a list of `(time, shift)` entries, in strictly increasing
time order. `shift_at(table, t)` gives the shift in force at time `t`.

2.2 Between two consecutive entries the shift changes linearly with time: at a
time `t` after entry `(t0, s0)` and before the next entry `(t1, s1)`, the shift
is `s0 + (s1 - s0) * (t - t0) / (t1 - t0)`. At an entry's own time, that entry's
shift is in force.

2.3 At or before the first entry's time the first entry's shift is in force;
at or after the last entry's time, the last entry's shift.

2.4 The shifted stage of a reading is its recorded stage plus the shift in
force at its time.

## 3. The rating curve

3.1 A rating curve is a list of segments in strictly increasing order of their
lower stage. Each segment has a lower stage, a coefficient, an offset and an
exponent. `RatingCurve.discharge(stage)` rates one stage.

3.2 A stage is rated on the segment with the greatest lower stage that is at or
below it. A stage below the first segment's lower stage has no discharge: 0.0.

3.3 On its segment, a stage above the segment's offset has discharge
`coefficient * (stage - offset) ** exponent`. For a segment with an exponent
above zero, a stage at or below the offset has no discharge: 0.0.

## 4. The discharge series

`discharge_series(record, table, curve)` gives one point per reading, in the
record's order: the reading's time and the rating of its shifted stage.

## 5. Joined pieces

5.1 Two consecutive points of a series are joined when the second is later than
the first by no more than the gap limit. The piece between joined points
carries the straight line from the first point's value to the second's.

5.2 Points at the same time, or further apart than the gap limit, are not
joined; no piece lies between them. With a gap limit of zero or less, nothing
is joined.

5.3 The covered time of a span is the total length of the parts of pieces that
fall inside it. The integral over a span is the total, over those parts, of the
area under each piece's line.

5.4 `joined_pieces(series, gap)` yields `(t0, v0, t1, v1)` for each joined pair
of consecutive points, in series order. `span_totals(series, start, end, gap)`
gives `(covered time, integral)` for the span from `start` up to `end`.

## 6. Daily means

`daily_mean(series, day, gap)` is the day's integral divided by the day's
covered time: the time-weighted mean of the value over the part of the day the
series covers.

## 7. Volumes

`volume(series, start, end, gap)` is the integral over the span from `start`
up to `end`. A span whose end is not after its start holds no time, and its
volume is 0.0.

## 8. Peaks

8.1 `peaks(series, threshold, separation)` finds the events in a series. A run
is a longest stretch of consecutive points whose values are all above the
threshold.

8.2 A run starting less than `separation` seconds after the end of the event
before it belongs to that event. Otherwise it starts a new event. A run's end
is the time of its last point, and an event's end is the end of its last
run.

8.3 An event's peak is its greatest value, at the time of the first point in
the event that reaches it. `peaks` returns one `(time, value)` pair per event,
in time order.

## 9. Daily values

`daily_values(record, table, curve, first_day, last_day, gap)` gives the daily
mean of the discharge series (section 4) for every day from `first_day` to
`last_day` inclusive, in order.
