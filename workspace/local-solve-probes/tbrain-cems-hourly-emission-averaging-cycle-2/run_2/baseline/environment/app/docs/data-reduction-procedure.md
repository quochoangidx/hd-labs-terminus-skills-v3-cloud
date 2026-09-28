# CEMS Data Reduction Procedure (DRP-4)

Environmental Section, Boiler 2 stack NOx monitor.

This procedure governs how the quarter-hour export of the Boiler 2 continuous
emissions monitor is reduced to the quarterly NOx report sent under the
plant's air permit. Where the report package and this procedure disagree, the
procedure is right. Rule numbers stay the same from one revision to the next.

## 1. Units, rounding and limits

1.1 Every figure in a record and in the job's unit settings is a whole number
in the unit this section gives it. Arithmetic is exact. A result is rounded
only where a rule says so, to the nearest whole unit of the figure it
produces, and an exact half goes up. A figure no rule rounds is not rounded.

1.2 NOx is kept in tenths of a ppm, oxygen in tenths of a per cent, stack flow
in standard cubic feet per hour (scfh), load in megawatts (MW), mass rates in
tenths of a pound per hour and the quarter's NOx mass in hundredths of a ton of
2,000 pounds.

1.3 A job gives the unit settings and the export. The settings are a
reference oxygen from 0 to 150 tenths of a per cent and a NOx limit from 1 to
20,000 tenths of a ppm. The export holds 1 to 11,520 records.

1.4 A record covers one quarter-hour, named by its start time written
YYYY-MM-DD HH:MM with the minutes 00, 15, 30 or 45. The records are in time
order and each starts fifteen minutes after the one before it. Every date
falls in the years 2020 to 2039. A record gives the unit's load, from 0 to
1,500 MW, the NOx reading, from 0 to 20,000, the oxygen reading, from 0 to
205, the stack flow, from 0 to 90,000,000, and a status code: OK for a normal
reading, CAL for a quarter in which the analyser ran its daily calibration,
MNT for maintenance and OOC for an analyser out of control. A CAL record
always has a load of 1 MW or more, and an hour holding a CAL record holds no
MNT or OOC record.

1.5 An hour is a clock hour, HH:00 to the start of the next hour, and belongs
to the calendar day on which it starts.

## 2. Definitions

2.1 An operating quarter is a record whose load is 1 MW or more. An operating
hour is an hour holding at least one operating quarter, and its operating
time is the number of its operating quarters divided by four.

2.2 A valid reading is the record of an operating quarter whose status code is
OK.

2.3 A valid hour is an operating hour with a valid reading for each of its
operating quarters. An operating hour holding a CAL record is also a valid
hour when it has two valid readings or more.

2.4 A firing hour is a valid hour whose oxygen average is below 190 tenths of
a per cent. With the burners firing, the flue gas carries well under 19 per
cent oxygen; at light-off and during a purge it is close to ambient air.

2.5 A lost hour is an operating hour in which no reading is valid.

2.6 An operating day is a calendar day holding at least one operating hour.

2.7 The firing ratio of a firing hour is (209 less the reference oxygen)
divided by (209 less its oxygen average).

## 3. Hourly values

3.1 The NOx, oxygen and flow averages of a valid hour are the averages of the
NOx, oxygen and flow of its valid readings.

3.2 The corrected concentration of a firing hour is its NOx average times
its firing ratio, rounded, in tenths of a ppm.

3.3 The mass rate of a valid hour is 1.194 x 10^-7 pounds per scf per ppm
times its NOx average in ppm times its flow average, rounded, in tenths of a
pound per hour. The measured NOx average is used, never a corrected
concentration.

## 4. Substitute data

4.1 Every operating hour that is not a valid hour is reported as a
substitute hour, and every operating hour has a reported concentration and a
reported mass rate.

4.2 A lost hour takes, for each of the two figures, the average of the
reported figure of the last valid hour before it and of the first valid hour
after it, rounded.

4.3 When there is a valid hour on only one side of a lost hour, the lost hour
takes that valid hour's reported figures. When the job has no valid hour, a
lost hour's figures are nought.

## 5. Mass

5.1 The NOx mass of an operating hour is its reported mass rate times its
operating time. The quarter's NOx mass is the total over its operating hours,
rounded, in hundredths of a ton.

## 6. Rolling averages

6.1 An operating day has a rolling average once the job holds at least
twenty-nine operating days before it. The rolling average is the average of
the reported concentrations of the valid hours in that operating day
and the twenty-nine operating days before it, rounded, in tenths of a ppm. An
operating day whose thirty operating days hold no valid hour has no rolling
average.

6.2 An operating day whose rolling average is above the NOx limit is an
exceedance day.

## 7. The report

7.1 The report lists every operating hour in time order with its kind (valid
or substitute), its reported concentration and its reported mass rate; every
operating day in date order with its rolling average, if it has one, and
whether it is an exceedance day; the number of operating hours; the number of
valid hours; and the quarter's NOx mass.
