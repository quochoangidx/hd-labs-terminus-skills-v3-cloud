# stockbill

Client billing for a third-party logistics warehouse: pallet storage and handling for one billing period.

- `src/stockbill/`: the package; `build_statement(job)` returns the period statement
- `tools/stockbill_run.py`: the driver the billing team runs, `python3 tools/stockbill_run.py JOB.json`
- `docs/billing-schedule.md`: client billing schedule WB-5, which the statement follows
- `examples/small-job.json`: a small job in the input format

## Job file

A job is one JSON object:

- `statement`: the statement's reference, a string
- `period`: `{"start": DATE, "end": DATE}`, the billing period
- `holidays`: public holiday dates
- `clients`: an object keyed by client id; each value has
  - `minimum`: the minimum storage bill for a lot, in cents
  - `surcharge_percent`: the energy surcharge, a whole number of percent
  - `revisions`: a list of objects with `effective` (a date) and `rates`, where
    `rates["storage"]` is a list of tiers `[length, rate]` (`length` in storage
    weeks, `null` for the last tier; `rate` in cents per pallet per week) and
    `rates["handling"]` holds `fee` (cents per receipt) and `in`, `out` and `after_hours`,
    each in cents per pallet
- `lots`: a list of objects with `id` (a string), `client` (a key of `clients`),
  `received` (a date), `pallets` (the pallets that arrived that day, a whole
  number) and `dispatches`, a list of `{"date": DATE, "pallets": N}` as the
  warehouse keys them against the lot; `N` is signed, and pallets taken back
  into stock are keyed below nought

Dates are `YYYY-MM-DD` strings. The statement layout is given in section 7 of the schedule.
