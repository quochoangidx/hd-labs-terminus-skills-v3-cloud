# noisedose

Reduces personal noise-dosimeter surveys to the exposure report of the
hearing conservation programme. The figures follow
`docs/noise-survey-manual.md` (manual HC-4).

## Running

    python3 /app/tools/noisedose_run.py SURVEY.json

prints the report for one survey file as a single JSON object on standard
output. The package lives in `src/noisedose`; `examples/` holds a small survey.

## Survey file

A JSON object:

- `survey`: the survey's name, a string.
- `workers`: a list with one object per surveyed worker, each holding
  - `id`: the worker id, a string;
  - `group`: the worker's group code, a string;
  - `shift_minutes`: the length of the worker's shift, an integer;
  - `log`: the dosimeter's runs in the order it logged them, each a two-item
    list `[minutes, level]` with `minutes` an integer and `level` the logged
    level in dBA (a number with one decimal place); the list may be empty;
  - `peaks`: the peak levels the dosimeter held, in dBC, a list of numbers
    with one decimal place (possibly empty).

## Report

A JSON object:

- `survey`: the survey's name, as given.
- `workers`: one object per worker, in the order of the survey file, holding
  `id` and `group` as given, `dose` (the worker's shift dose in per cent, a
  number), `twa` (the worker's TWA in dB, a number, or `null` when the worker
  has none), `status` (`"below"`,
  `"action"` or `"over"`), and `ceiling` and `impulse` (booleans).
- `groups`: one object per group code in the survey, in ascending character
  order of the codes (digits before letters), holding `group` (the code),
  `dose`, `twa` and `status` with the same meanings as for a worker.
