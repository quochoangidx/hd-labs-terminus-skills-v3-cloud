# FM-4: Driver hours of service

This manual sets the hours-of-service limits for the fleet's drivers and says
how a driver's log is audited against them. Where the audit package disagrees
with it, the manual governs. Rule numbers do not move between editions; safety
staff cite them in audit findings.

The fleet's limits follow the federal hours-of-service rules (49 CFR Part 395)
in outline but are stricter in several places. Each rule that departs from the
federal rule says so, and the federal rule does not apply in its place.

## 1. The log

1.1 An audit reads one driver's log, which gives:

- `driver`: the driver's fleet number, a string of 1 to 32 characters;
- `end`: the minute at which the log ends, from 1 to 20160 (fourteen days);
- `recap`: the driver's on-duty time, in minutes, on each of the seven days
  before the log, oldest first, each from 0 to 1440;
- `events`: 1 to 2000 duty-status entries in time order. Each has `at`, the
  minute the entry takes effect; `status`, one of `off` (off duty), `sleeper`
  (in the sleeper berth), `driving` and `on` (on duty, not driving); and
  `miles`, the distance the truck covered while the entry was in force, a
  number from 0 to 1000. The first entry is at minute 0, each later one comes
  after the one before it, and every one comes before `end`.

An entry is in force from its `at` until the next entry's `at`, or until `end`
for the last one. That span is a stretch.

1.2 Minutes are whole minutes counted from midnight, home-terminal time, at the
start of the log. Day 1 is minutes 0 to 1439, day 2 is minutes 1440 to 2879,
and so on. The log's days run from day 1 to the day that holds minute `end` − 1.

1.3 The driver completed a reset (2.4) just before minute 0, and rest at the
start of the log continues it. Every log holds some on-duty time.

1.4 Every figure is a whole number of minutes except time left (section 5),
which is reported in hours. Nothing is rounded where no rule says so.

1.5 This manual provides for logs as 1.1 to 1.3 describe them, and for time
left from nought up to the limit it is left under, judged on the exact time
left of 5.1 before any rounding.

## 2. Definitions

2.1 Rest is time off duty or in the sleeper berth. On-duty time is all time
that is not rest.

2.2 Driving time is time in the `driving` status together with time spent on
yard moves. Federal rules treat a yard move as on-duty time that is not
driving; the fleet counts yard moves against every limit in section 3.

2.3 A yard move is on-duty time in a stretch in which the truck covers one
mile or more.

2.4 A rest period is an unbroken run of rest, whatever mix of off-duty and
sleeper-berth time it holds. A reset is a rest period of 10 hours or more.

2.5 A shift begins at the first minute of on-duty time after a reset and ends
where the next reset begins.

2.6 A break is a rest period of 30 minutes or more. Federal rules also accept
30 consecutive minutes on duty not driving as a break; the fleet does not.

2.7 The cycle total at a minute is the driver's on-duty time earlier on that
minute's day, plus the on-duty time of each of the six days before that day,
taken from the log or, for days before the log, from the recap. The fleet runs
the 60-hour, 7-day schedule, not the 70-hour, 8-day one. It does not use the
34-hour restart or the sleeper-berth split, and neither changes any figure in
this manual.

## 3. Limits

Each rule names a limit that a driver may not drive past. A minute of driving
time driven past a limit is a violation minute of that rule, and one minute may
be a violation minute of several rules.

3.1 Driving limit. A driver may drive 10 hours in a shift. A minute of driving
time is past the limit when the shift's driving time before that minute already
amounts to 10 hours. The federal limit is 11 hours.

3.2 Window. A driver may not drive once 14 hours have passed since the shift
began. The window runs on the clock: rest inside the shift, breaks included,
does not stop it. A minute of driving time that starts 14 hours or more after
the shift began is past the window.

3.3 Break. A minute of driving time is past the break limit when the driving
time since the later of the start of the shift and the end of the driver's
latest break before that minute already amounts to 8 hours.

3.4 Cycle. A minute of driving time is past the cycle limit when the cycle total
at the start of that minute amounts to 60 hours or more.

## 4. Day figures

4.1 For each day of the log the audit gives the day's driving time, its on-duty
time and its violation minutes under each rule of section 3. A stretch that
crosses midnight counts on each day for the minutes that fall in it, and a
violation minute counts on the day it falls in.

## 5. Time left

5.1 Time left is given at the end of the log, for the latest shift that began
before `end`. Under 3.1 it is 10 hours less that shift's driving time up to
`end`; under 3.2 it is 14 hours less the time from the start of that shift to
`end`; under 3.4 it is 60 hours less the on-duty time of the log's last day and
of the six days before it.

5.2 Time left that this manual provides for (1.5) is reported in hours,
rounded down to a tenth of an hour.

## 6. The report

6.1 The audit prints one JSON object with the keys `driver`, `days` and `left`.
`driver` is the log's `driver`. `days` lists the log's days in order, each an
object with `day` (1 for day 1), `driving`, `on_duty` and `violations`, which
maps each of `"3.1"`, `"3.2"`, `"3.3"` and `"3.4"` to that rule's violation
minutes on the day. `left` has `driving`, `window` and `cycle`, the time left
under 3.1, 3.2 and 3.4. Minutes are integers; hours are numbers.
