# demurrage

Works out the demurrage charges on one terminal's released containers. The
figures follow `docs/demurrage-tariff.md` (tariff DM-3).

## Running

    python3 /app/tools/demurrage_run.py RELEASES.json

prints the statement for one release file as a single JSON object on standard
output. The package lives in `src/demurrage`; `examples/` holds a small file.

## Release file

A JSON object:

- `terminal`: the file's name, a string.
- `containers`: a list with one object per container, each holding `id` (a
  string), `type` (`"DRY"`, `"REEFER"` or `"TANK"`), `discharged` and
  `picked_up` (day numbers, integers) and `rate` (the daily rate in cents, an
  integer).

## Statement

A JSON object:

- `terminal`, as given.
- `containers`: one object per container, in the order of the file, holding
  `id`, `dwell`, `free` and `days` (days) and `charge` (cents), all integers
  except `id`.
- `total`: the sum of the charges in cents, an integer.
