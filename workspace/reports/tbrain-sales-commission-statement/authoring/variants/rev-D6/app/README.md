# commission

Draws up the quarterly commission statement of each field sales rep. The
figures follow `docs/compensation-plan.md` (Field Sales Compensation Plan,
issue 6).

## Running

    python3 /app/tools/commission_run.py JOB.json

prints the statements for one job file as a single JSON object on standard
output. The package lives in `src/commission`; `examples/` holds a small job.

## Job file

A JSON object with one key, `reps`: a list of reps, each an object with

- `rep`: the rep code, a string;
- `quarter`: the quarter being paid, written `YYYY-Qn`;
- `quota`: the rep's quota, in cents;
- `draw`: the rep's draw, in cents;
- `owed`: the owed balance brought forward, in cents;
- `carried`: the carried amount brought forward, in cents;
- `orders`: the rep's orders, each a four-item list
  `[booked, value_cents, split, first]`, where `split` is the rep's split in
  per cent and `first` is `true` for a customer's first order and `false`
  otherwise;
- `credits`: the credit notes raised against the rep's orders, each a
  four-item list `[raised, booked, amount_cents, split]`, where `booked` is the
  day the credit note's order was booked and `split` the rep's split of that
  order in per cent.

Both lists may be empty and are in no particular order. Every date is a string
written `YYYY-MM-DD`; `first` is a JSON boolean; every other item but the rep
code and quarter is an integer.

## Statements

A JSON object with one key, `statements`: a list holding one object per rep, in
the order of the job's `reps`, with exactly these keys, every value but `rep`
an integer:

- `rep`: the rep code, as given;
- `bookings`: the rep's bookings, in cents;
- `commission`: the commission, in cents;
- `bonus`: the total of the first-order bonus lines, in cents;
- `clawback`: the clawback, in cents;
- `total`: the rep's total, in cents;
- `recovered`: the amount recovered from the owed balance, in cents;
- `owed`: the owed balance after this quarter, in cents;
- `paid`: the amount paid, in cents;
- `carried`: the amount carried to the next quarter, in cents.
