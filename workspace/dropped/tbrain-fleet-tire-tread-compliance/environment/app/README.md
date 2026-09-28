# treadcheck

Works out the tire compliance summary the tire shop issues from its tread
inspection log. The figures follow `docs/tread-standard.md` (edition TS-6).

## Running

    python3 /app/tools/treadcheck_run.py JOB.json

prints the summary for one job file as a single JSON object on standard
output. The package lives in `src/treadcheck`; `examples/` holds a small job.

## Job file

A JSON object:

- `report_date`: the date the summary is made for;
- `gauges`: the tread gauges, each an object with `gauge` (the gauge number, a
  string) and `offset` (its calibration offset in tenths of a millimetre, an
  integer);
- `tires`: a list of tires, each an object with
  - `tire`: the tire number, a string;
  - `position`: `"steer"`, `"drive"` or `"trailer"`;
  - `new_depth`: the tread depth when new, in tenths of a millimetre (an
    integer);
  - `casing`: the date the casing was made;
  - `retreads`: the number of times it has been retreaded (an integer);
  - `mounted_km`: the odometer at mounting, in km (an integer);
  - `readings`: the readings in date order, each a four-item list
    `[date, odometer, shown, gauge]`: the date, the odometer in km (an
    integer), what the gauge showed in tenths of a millimetre (an integer) and
    the gauge number.

Every date is a string written `YYYY-MM-DD`.

## Summary

A JSON object with one key, `tires`: a list holding one object per tire, in
the order of the job's `tires`, with exactly these keys:

- `tire`: the tire number, as given;
- `position`: the position, as given;
- `latest`: the latest depth, in tenths (an integer);
- `worn`: the tread worn, in tenths (an integer);
- `distance`: the distance it was worn over, in km (an integer);
- `rate`: the wear rate, in tenths per 10,000 km (an integer);
- `status`: `"in service"`, `"watch"` or `"pull"`;
- `retread`: `true` when the casing may go for retread, else `false`;
- `km_left`: the distance in km the tire can still run before its removal
  depth at its wear rate (an integer);
- `regroove`: `true` when the tire passes the shop's regrooving check, else
  `false`.
