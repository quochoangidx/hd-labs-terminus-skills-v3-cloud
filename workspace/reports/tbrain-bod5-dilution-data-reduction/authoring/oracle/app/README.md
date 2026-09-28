# bodcalc

Reduction of a five-day BOD (BOD5) bench sheet to the batch report.

- `src/bodcalc/`: the package; `reduce_batch(batch)` returns the report
- `tools/bodcalc_run.py`: the driver the laboratory runs,
  `python3 tools/bodcalc_run.py BATCH.json`
- `docs/sop-wq14-bod5.md`: SOP WQ-14, the reduction procedure
- `examples/small-batch.json`: a small batch in the input format

## Batch file

One JSON object:

- `batch`: the batch id (a string)
- `seed_controls`: list of `{id, seed_ml, do_initial, do_final}`
- `blanks`: list of `{id, do_initial, do_final}` (dilution water only)
- `check`: `{id, bottles}` for the glucose-glutamic acid check standard
- `samples`: list of `{id, duplicate_of, bottles}`; `duplicate_of` is null or
  another sample's id

Each check or sample bottle is `{sample_ml, seed_ml, do_initial, do_final}`;
`seed_ml` is 0 for a bottle set up without seed. DO readings are in mg/L as read
on day 0 (`do_initial`) and day 5 (`do_final`); a final reading may be higher
than the initial one. Volumes are in mL.
