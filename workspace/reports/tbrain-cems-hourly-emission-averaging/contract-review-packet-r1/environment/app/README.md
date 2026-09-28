# cemsqr

Reduces the Boiler 2 CEMS quarter-hour export to the quarterly NOx report. The
figures follow `docs/data-reduction-procedure.md` (procedure DRP-4).

## Running

    python3 /app/tools/cemsqr_run.py JOB.json

prints the report for one job file as a single JSON object on standard output.
The package lives in `src/cemsqr`; `examples/` holds a small job.

## Job file

A JSON object:

- `unit`: an object with `ref_o2`, the reference oxygen in tenths of a per
  cent, and `limit`, the NOx limit in tenths of a ppm (integers).
- `readings`: the export, a list of records in time order, each a six-item
  list `[start, load, nox, o2, flow, code]`:
  - `start`: the quarter-hour's start, a string written `YYYY-MM-DD HH:MM`;
  - `load`: the unit load in MW;
  - `nox`: the NOx reading in tenths of a ppm;
  - `o2`: the oxygen reading in tenths of a per cent;
  - `flow`: the stack flow in scfh;
  - `code`: the status code, one of `OK`, `CAL`, `MNT`, `OOC`.

  `load`, `nox`, `o2` and `flow` are integers. The analyser keeps writing
  readings while the unit is shut down, so records with a load of 0 carry
  readings too.

## Report

A JSON object with exactly these keys:

- `hours`: one object per operating hour, in time order, with exactly the keys
  `hour` (the hour's start, written `YYYY-MM-DD HH`), `kind` (`"valid"` or
  `"substitute"`), `nox` (the reported concentration, tenths of a ppm) and
  `lb` (the reported mass rate, tenths of a pound per hour);
- `days`: one object per operating day, in date order, with exactly the keys
  `day` (`YYYY-MM-DD`), `rolling` (the rolling average in tenths of a ppm, or
  `null` when the day has none) and `exceed` (`true` or `false`);
- `operating_hours`: the number of operating hours;
- `valid_hours`: the number of valid hours;
- `nox_tons`: the quarter's NOx mass in hundredths of a ton.

Every figure is an integer.
