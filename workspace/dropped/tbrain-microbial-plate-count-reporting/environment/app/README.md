# platecount

Turns the plate readings of an aerobic plate count batch into the result the
laboratory reports for each sample. The results follow `docs/apc-sop.md`
(SOP MIC-14).

## Running

    python3 /app/tools/platecount_run.py BATCH.json

prints the report for one batch file as a single JSON object on standard
output. The package lives in `src/platecount`; `examples/` holds a small batch.

## Batch file

A JSON object:

- `batch`: the batch's name, a string.
- `samples`: a list with one object per sample, each holding
  - `id`: the sample id, a string;
  - `unit`: `"g"` for a sample weighed in grams, `"mL"` for one measured in
    millilitres;
  - `dilutions`: the dilutions the analyst plated, each an object holding
    - `step`: the step of the dilution series, an integer;
    - `volume`: the volume plated on each of its plates in millilitres, the
      number `1.0` or `0.1`;
    - `plates`: one reading per plate, each an integer number of colonies, or
      `null` for a plate marked as too numerous to count.

## Report

A JSON object:

- `batch`: the batch's name, as given.
- `samples`: one object per sample, in the order of the batch file, holding
  `id` as given, `unit` (`"CFU/g"` or `"CFU/mL"`), `kind` (`"count"`,
  `"estimate"`, `"below"` or `"above"`) and `apc`, the reported result as a
  string written the way the SOP writes it, with its `<` or `>` sign where it
  has one.
