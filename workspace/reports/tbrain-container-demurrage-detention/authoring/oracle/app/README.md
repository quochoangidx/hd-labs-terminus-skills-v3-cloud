# ddbill

Import demurrage and detention billing for one invoice run.

- `src/ddbill/`: the package; `build_statement(job)` returns the statement
- `tools/ddbill_run.py`: the driver the billing desk runs, `python3 tools/ddbill_run.py JOB.json`
- `docs/tariff-rules.md`: tariff rules DT-3, which the statement follows
- `examples/small-job.json`: a small job in the input format

## Job file

A job is one JSON object:

- `invoice`: the invoice run's reference, a string
- `cut_off`: the invoice run's cut-off date, `YYYY-MM-DD`
- `holidays`: port holiday dates, `YYYY-MM-DD`
- `closures`: dates the terminal's gates stayed shut, `YYYY-MM-DD`
- `contracts`: an object keyed by contract id; each value has
  - `terminal_free_days`, `merchant_free_days`: whole numbers of days
  - `discount_percent`: a whole number
  - `revisions`: a list of objects with `effective` (a date) and `scales`,
    where `scales["terminal"]` and `scales["merchant"]` each map a size
    (`"20"`, `"40"`) to a list of tiers `[length, rate]`: `length` in days
    (`null` for the last tier) and `rate` in cents per day
- `containers`: a list of objects with `id` (a string), `size` (`"20"` or
  `"40"`), `contract` (a key of `contracts`) and `history`, a list of moves
  `{"move": CODE, "date": "YYYY-MM-DD"}` with `CODE` one of `DISCHARGE`,
  `GATE_OUT` and `EMPTY_RETURN`

The statement layout is given in section 7 of the tariff rules.
