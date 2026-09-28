# rebate

Draws up the quarterly rebate settlement statements the rebate desk sends each
supplier account. The figures follow `docs/rebate-schedule.md` (Schedule R,
edition R-4).

## Running

    python3 /app/tools/rebate_run.py JOB.json

prints the statements for one job file as a single JSON object on standard
output. The package lives in `src/rebate`; `examples/` holds a small job.

## Job file

A JSON object:

- `tiers`: the tier table, a list of rows in table order, each an object with
  `from` (the threshold in cents) and `bp` (the rate in basis points), both
  integers.
- `accounts`: a list of supplier accounts, each an object with
  - `account`: the account code, a string;
  - `quarter`: the quarter being settled, written `YYYY-Qn`;
  - `prior`: the account's net purchases in the same quarter a year before, in
    cents (an integer);
  - `purchases`: the purchase lines, each a three-item list
    `[invoiced, units, unit_cents]`;
  - `returns`: the returns, each a three-item list `[taken, units, unit_cents]`;
  - `notices`: the price notices, each a four-item list
    `[effective, old_cents, new_cents, on_hand]`;
  - `sales`: the sales below cost, each a four-item list
    `[sold, units, cost_cents, price_cents]`.

  Each of the four lists may be empty and is in no particular order. Every date
  is a string written `YYYY-MM-DD`; every other item but the account code and
  quarter is an integer.

## Statements

A JSON object with one key, `settlements`: a list holding one object per
account, in the order of the job's `accounts`, with exactly these keys, every
value but `account` an integer:

- `account`: the account code, as given;
- `purchases`: the purchases, in cents;
- `returns`: the returns credited, in cents;
- `net`: the net purchases, in cents;
- `tier_bp`: the rebate rate, in basis points;
- `rebate`: the volume rebate, in cents;
- `growth`: the growth bonus, in cents;
- `protection`: the price protection, in cents;
- `chargebacks`: the chargebacks, in cents;
- `total`: the settlement, in cents;
- `paid`: the amount paid, in cents;
- `carried`: the amount carried to the next quarter, in cents.
