# tdbenefit

Works out the temporary disability benefit statements the claims unit sends
with indemnity payments. The figures follow `docs/td-benefits-manual.md`
(manual TD-7).

## Running

    python3 /app/tools/tdbenefit_run.py JOB.json

prints the statements for one job file as a single JSON object on standard
output. The package lives in `src/tdbenefit`; `examples/` holds a small job.

## Job file

A JSON object:

- `rates`: the rate table, a list of rows in table order, each an object with
  `from` (the date the row takes effect), `max` and `min` (the weekly maximum
  and minimum in cents, integers).
- `claims`: a list of claims, each an object with
  - `claim`: the claim number, a string;
  - `injury`: the date of injury;
  - `wages`: the wage lines, each a two-item list `[paid, cents]`: the date
    the payment was made and its gross in cents (an integer); the list may be
    empty and is in no particular order;
  - `disability`: the certified periods of total disability, each a two-item
    list `[first, last]` of dates;
  - `earnings`: the partial earnings, each a two-item list `[week, cents]`:
    the Sunday that names the payroll week and what the worker earned in it,
    in cents (an integer); the list may be empty.

Every date is a string written `YYYY-MM-DD`.

## Statements

A JSON object with one key, `statements`: a list holding one object per
claim, in the order of the job's `claims`, with exactly these keys, every value
but `claim` an integer:

- `claim`: the claim number, as given;
- `aww`: the average weekly wage, in cents;
- `rate`: the weekly rate, in cents;
- `waiting_days`: the number of days in the waiting period;
- `retro_days`: the retroactive days;
- `ttd_days`: the paid days;
- `ttd`: the total-disability amount, in cents;
- `tpd_weeks`: the number of weeks of partial disability;
- `tpd`: the partial amount, in cents;
- `total`: the total owed, in cents.
