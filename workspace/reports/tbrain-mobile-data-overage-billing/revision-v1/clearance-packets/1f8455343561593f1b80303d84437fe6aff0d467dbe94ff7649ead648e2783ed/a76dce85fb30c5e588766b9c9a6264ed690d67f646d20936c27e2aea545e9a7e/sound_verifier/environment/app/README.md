# usagebill

Works out the data charges on one business account's mobile lines for a
billing cycle. The figures follow `docs/data-usage-tariff.md` (tariff MD-2).

## Running

    python3 /app/tools/usagebill_run.py USAGE.json

prints the statement for one account file as a single JSON object on standard
output. The package lives in `src/usagebill`; `examples/` holds a small file.

## Account file

A JSON object:

- `account`: the account's name, a string.
- `lines`: a list with one object per mobile line, each holding `id` (a
  string), `plan` (`"BASIC"`, `"PLUS"` or `"FLEX"`), `sessions` (a list of
  integers, the kilobytes each data session used in the cycle) and `rate`
  (the overage rate in cents per megabyte, an integer).

## Statement

A JSON object:

- `account`, as given.
- `lines`: one object per line, in the order of the file, holding `id`,
  `used`, `allowance` and `over` (megabytes) and `charge` (cents), all
  integers except `id`.
- `total`: the sum of the charges in cents, an integer.
