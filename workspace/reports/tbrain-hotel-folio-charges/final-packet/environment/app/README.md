# folio

Works out the charges on the folios of guests checking out, for one night
audit. The figures follow `docs/folio-charges-rules.md` (rules FC-3).

## Running

    python3 /app/tools/folio_run.py STAYS.json

prints the folios for one night audit file as a single JSON object on standard
output. The package lives in `src/folio`; `examples/` holds a small file.

## Night audit file

A JSON object:

- `audit`: the file's name, a string.
- `stays`: a list with one object per stay, each holding `id` (a string),
  `nights` (an integer) and `rate` (the nightly room rate in cents, an
  integer).

## Folios

A JSON object:

- `audit`, as given.
- `folios`: one object per stay, in the order of the file, holding `id`,
  `room`, `occupancy_tax`, `city_tax`, `service_fee` and `total`, all in
  cents and all integers except `id`.
- `total`: the sum of the folio totals in cents, an integer.
