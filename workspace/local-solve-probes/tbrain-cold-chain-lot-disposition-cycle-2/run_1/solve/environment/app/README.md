# coldchain

Disposes finished-product lots from the temperature records of their
distribution. The figures follow `docs/qa-sop-lot-disposition.md`
(QA-SOP-311).

## Running

    python3 /app/tools/coldchain_run.py JOB_DIR

prints the report for one job directory as a single JSON object on standard
output. The package lives in `src/coldchain`; `examples/` holds a small job.

## Job directory

- `stability.json`: the product's stability record, a JSON object with
  - `product`: the product name, a string;
  - `labelled_range_c`: `[lower, upper]`, the labelled storage limits;
  - `freeze_point_c`: the freeze point;
  - `activation_ratio_k`: the activation ratio in kelvin, a number;
  - `bands`: the excursion bands, each an object with `band` (its name, a
    string), `lower_c` and `upper_c` (its ends) and `allowance_h` (its
    allowance in hours, an integer). The list may be in any order.

  Temperatures are numbers with at most one decimal place.
- `lots.json`: a JSON list with one object per lot, each holding `lot` (the
  lot id, a string), `legs` (the names of the lot's legs in travel order) and,
  optionally, `certificate`, an object from band name to the list of entries
  the lot's release certificate records against that band, each entry its
  length in whole minutes. A band the object does not name has no entries.
- `loggers/<leg>.csv`: one logger export per leg name, with a header row
  `timestamp,temp_c` and one row per reading, for example
  `2031-05-04T13:25,6.4`. Stamps are UTC to the minute.

## Report

A JSON object with `product` (as given) and `lots`, one object per lot, in the
order of `lots.json`, holding:

- `lot`: the lot id, as given;
- `disposition`: `"release"`, `"quarantine"` or `"reject"`;
- `band_hours`: an object from each band name of the record to the lot's time
  in that band, in hours;
- `remaining_hours`: an object from each band name to the band's remaining
  allowance, in hours;
- `unlogged_hours`: the lot's unlogged time, in hours;
- `mkt_c`: the lot's mean kinetic temperature in degrees Celsius.

Every figure in `band_hours`, `remaining_hours`, `unlogged_hours` and `mkt_c`
is a JSON number written with a decimal point.
