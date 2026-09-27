# finebook

Works out the overdue fines on one branch's returned loans. The figures follow
`docs/overdue-fines-policy.md` (policy LF-5).

## Running

    python3 /app/tools/finebook_run.py LOANS.json

prints the fines statement for one return file as a single JSON object on
standard output. The package lives in `src/finebook`; `examples/` holds a small
file.

## Return file

A JSON object:

- `branch`: the file's name, a string.
- `loans`: a list with one object per returned loan, each holding `id` (a
  string), `kind` (`"BOOK"`, `"DVD"` or `"JOURNAL"`), `borrowed` and
  `returned` (day numbers, integers), `daily_fine` and `replacement` (cents,
  integers).

## Statement

A JSON object:

- `branch`, as given.
- `loans`: one object per loan, in the order of the file, holding `id`, `due`
  (a day number), `late` (days) and `fine` (cents), all integers except `id`.
- `total`: the sum of the fines in cents, an integer.
