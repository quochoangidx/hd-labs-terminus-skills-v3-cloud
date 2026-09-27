# cyclecount

Turns a finished cycle-count sheet into the variance report. The figures
follow `docs/cycle-count-procedure.md` (procedure CC-2).

## Running

    python3 /app/tools/cyclecount_run.py SHEET.json

prints the report for one count sheet as a single JSON object on standard
output. The package lives in `src/cyclecount`; `examples/` holds a small sheet.

## Count sheet

A JSON object:

- `sheet`: the sheet's name, a string.
- `lines`: a list with one object per counted location line, each holding
  `sku` (a string), `class` (a one-letter string), `system`, `count` (whole
  units, integers), `recount` (whole units, an integer, or `null` when no
  recount was taken) and `unit_cost` (cents, an integer).

## Report

A JSON object:

- `sheet`, as given.
- `lines`: one object per line, in the order of the sheet, holding `sku`,
  `variance`, `tolerance`, `status` (`"ok"`, `"recount"` or `"adjust"`),
  `value` and `booked` (the units posted to stock), all integers except
  `status`.
- `shrink`: the sheet's shrink in cents, an integer.
