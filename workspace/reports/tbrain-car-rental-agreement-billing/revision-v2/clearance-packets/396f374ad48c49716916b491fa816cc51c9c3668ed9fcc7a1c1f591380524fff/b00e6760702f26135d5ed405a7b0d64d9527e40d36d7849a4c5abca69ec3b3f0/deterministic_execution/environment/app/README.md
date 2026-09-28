# rentcharge

Works out the charges on closed rental agreements. The figures follow
`docs/rental-charges-manual.md` (manual RC-3).

## Running

    python3 /app/tools/rentcharge_run.py AGREEMENTS.json

prints the bill run for one agreement file as a single JSON object on standard
output. The package lives in `src/rentcharge`; `examples/` holds a small file.

## Agreement file

A JSON object:

- `branch`: the branch's name, a string.
- `agreements`: a list with one object per closed agreement, each holding
  `id` (a string), `out` and `in` (the times the car went out and came back,
  `YYYY-MM-DDTHH:MM` strings), `odometer_out` and `odometer_in` (integers),
  `fuel_out` and `fuel_in` (eighths, integers), and `day_rate`, `mile_rate`
  and `fuel_rate` (cents, integers).

## Bill run

A JSON object:

- `branch`, as given.
- `bills`: one object per agreement, in the order of the file, holding `id`
  (the agreement's id string, as given), and `days` (the days the time charge
  is for), `miles` (the miles driven), `time_charge`, `mileage_charge`,
  `fuel_charge`, `tax` and `total`, these all integers, the charges in cents.
- `revenue` and `tax`: the file's revenue and tax in cents, integers.
