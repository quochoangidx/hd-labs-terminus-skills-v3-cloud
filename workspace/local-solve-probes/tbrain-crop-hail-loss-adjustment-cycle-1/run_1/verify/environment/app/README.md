# hailadj

Draws up the crop-hail claim statements the claims office pays from. The
figures follow `docs/loss-adjustment-procedure.md` (edition 7).

## Running

    python3 /app/tools/hail_run.py JOB.json

prints the statements for one job file as a single JSON object on standard
output. The package lives in `src/hailadj`; `examples/` holds a small job.

## Job file

A JSON object with one key, `claims`: a list of claims, each an object with

- `claim`: the claim number, a string;
- `fields`: the insured fields of the claim, each an object with
  - `field`: the field code, a string;
  - `acres`: the insured acres, in tenths of an acre (an integer);
  - `per_acre`: the amount of insurance per acre, in whole dollars (an integer);
  - `deductible`: the deductible option, one of `"full"`, `"straight"` and
    `"vanishing"`;
  - `stage`: the growth stage on the day of the storm, a string such as
    `"V10"` or `"R2"`;
  - `replanted`: the acres replanted after the storm, in tenths of an acre (an
    integer, 0 when nothing was replanted);
  - `plots`: the sample plots, each a three-item list `[stand, dead, leaf]`:
    the plants in the row before the storm, the plants found dead or broken
    below the ear, and the leaf area the surviving plants lost in tenths of a
    per cent, all integers.

Plots are listed in the order the adjuster walked them, which carries no
meaning.

## Statements

A JSON object with one key, `claims`: a list holding one object per claim, in
the order of the job's `claims`, with exactly these keys:

- `claim`: the claim number, as given;
- `fields`: one object per field, in the claim's order, with exactly these
  keys, every value but `field` an integer:
  - `field`: the field code, as given;
  - `stand_loss`: the field's stand loss, in tenths of a per cent;
  - `defoliation`: the field's defoliation, in tenths of a per cent;
  - `leaf_loss`: the field's leaf loss, in tenths of a per cent;
  - `loss`: the field's loss, in tenths of a per cent;
  - `payable`: the field's payable loss, in tenths of a per cent;
  - `indemnity`: the field's indemnity, in cents;
  - `replant`: the field's replant line, in cents;
  - `payment`: the field's payment, in cents;
- `total`: the claim's total, in cents (an integer);
- `paid`: the amount paid on the claim, in cents (an integer).
