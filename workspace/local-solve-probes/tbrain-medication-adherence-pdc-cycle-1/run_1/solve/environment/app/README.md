# pdcmeasure

Works out the plan's medication adherence measure from a year of pharmacy
claim lines. The figures follow `docs/adherence-measure-spec.md`
(specification AM-2).

## Running

    python3 /app/tools/pdc_run.py CLAIMS.json

prints the measure report for one claims file as a single JSON object on
standard output. The package lives in `src/pdcmeasure`; `examples/` holds a
small claims file.

## Claims file

A JSON object:

- `plan`: the name of the extract, a string.
- `year`: the measurement year, an integer.
- `members`: a list with one object per member, each holding
  - `id`: the member id, a string;
  - `fills`: the member's claim lines in the order the pharmacy system
    exported them, each an object with `date` (the fill date, a
    `YYYY-MM-DD` string), `drug` (the drug code, a string of digits),
    `class` (the class code, a string) and `days` (the days supply, an
    integer); the list may be empty;
  - `stays`: the member's inpatient stays, each a two-item list
    `[admission, discharge]` of `YYYY-MM-DD` strings; the list may be
    empty.

## Report

A JSON object:

- `plan` and `year`, as given.
- `members`: one object for each member and each class the member has a
  fill of; members in the order of the claims file, and one member's classes
  in ascending character order of their codes (digits before letters). Each
  holds `id` and `class`, `index` (the index date, `YYYY-MM-DD`),
  `in_measure` (a boolean), `period` (the number of days the covered days
  are divided by for the PDC, an integer), `covered` (the covered days, an
  integer), `pdc` (a number) and `adherent` (a boolean).
- `classes`: one object per class code in the file, in ascending character
  order of the codes, holding `class`, `members` (how many members have a
  fill of the class), `in_measure` (how many of them are in the measure for
  it), `adherent` (how many are adherent for it) and `rate` (a number).
