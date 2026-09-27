# Ward rostering rules

These rules decide whether a four-week ward roster can be worked and what its
penalty is. They are the rules `tools/check_roster.py` applies.

## The ward

Each file in `wards/` is one ward's roster period. It has `days` days, numbered
from 0; day 0 is a Monday, so days 5 and 6 are the first Saturday and Sunday,
days 12 and 13 the second weekend, and so on. Nothing before day 0 or after
the last day is taken into account.

There are three shifts: `E` (early), `L` (late) and `N` (night), and
`shift_hours` gives the hours each one counts for. A night belongs to the day
it starts on.

A nurse has an `id`, a `grade` (`senior`, `RN` or `HCA`; a senior nurse is also
a registered nurse, an `HCA` is not), `min_hours` and `max_hours` for the whole
period, `max_nights` for the whole period, a list of `leave` days, and a list of
`requests`. A request `{"day": d, "off": "day"}` asks not to work on day `d` at
all; `{"day": d, "off": "E"}` (or `"L"`, `"N"`) asks not to work that shift on
day `d`.

`cover[s]` gives, for shift `s`, the `minimum` number of nurses on duty, how
many of them must be `registered` nurses, and the `preferred` number on duty.
`rules` gives `max_consecutive_days`, `rest_days_after_nights` and
`max_weekends`; `weights` gives the price of each soft rule below.

## Hard rules

A roster gives every nurse exactly one code per day: `E`, `L`, `N`, or `.` for
a day off. It must keep all of these:

1. On every day, every shift has at least its `minimum` nurses on duty, at
   least its `registered` count of senior or RN nurses among them, and at least
   one senior nurse.
2. A nurse on leave on a day has `.` that day.
3. Rest between days: a night is not followed the next day by an early or a
   late, and a late is not followed the next day by an early.
4. A nurse works at most `max_consecutive_days` days in a row (any shift counts
   as a working day).
5. After a run of nights, the nurse rests: when a nurse works `N` on day `d`
   and not `N` on day `d + 1`, days `d + 1` up to `d + rest_days_after_nights`
   (those that exist) are days off. A run of nights may go on for as many days
   as rules 4 and 3 allow.

## Penalty

A valid roster's penalty is the sum of:

- `short_of_preferred` for each nurse missing from a shift's `preferred`
  number on each day (nothing for nurses above it);
- for each nurse, `hour_under` for each hour worked below `min_hours`, and
  `hour_over` for each hour above `max_hours`;
- for each nurse, `night_over` for each night above `max_nights`;
- for each nurse and each weekend (Saturday and the Sunday after it), 
  `split_weekend` when the nurse works exactly one of the two days;
- for each nurse, `weekend_over` for each weekend above `max_weekends` on which
  the nurse works at least one of the two days;
- for each nurse, `lone_day` for each working day with a day off both before
  and after it (the first and last day of the period never count);
- `request` for each request not kept: a day-off request is broken by any shift
  on that day, a shift request only by that shift.

Penalties are whole numbers, and lower is better.

## File format

    {"roster": {"A01": "EELL..NN..E...", "A02": "...", ...}}

The file is a JSON object whose `roster` key holds a JSON object. Every nurse
of the ward is a key of that object, with a string of exactly
`days` characters, one per day in order, each `E`, `L`, `N` or `.`. Unknown
nurse ids are an error. Any other top-level key is ignored.

The file must be standard JSON in UTF-8 (so no `NaN` or `Infinity`), at most
2,000,000 bytes long.
