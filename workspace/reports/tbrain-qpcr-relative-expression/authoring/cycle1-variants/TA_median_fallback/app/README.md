# qpcrrel

Reduces one real-time PCR plate export, with its plate map, to the facility's
relative-expression report. The reduction rules are in
`docs/relative-expression-sop.md` (SOP QP-7).

## Running

    python3 /app/tools/qpcrrel_run.py PLATE.json

prints the report as one JSON object on standard output. The package is
standard-library Python and lives in `src/qpcrrel`; `build_report(plate)` takes
the parsed JSON object and returns the report object.

## Plate file

A JSON object with these keys:

- `plate`: the plate's name, a string.
- `calibrator`: the name of the calibrator sample, a string.
- `reference_genes`, `target_genes`: lists of gene names (strings), the plate
  map's two gene lists, in plate-map order.
- `wells`: a list of well objects in export order. Every well has `well` (its
  position, such as `"B07"`), `kind` (`"unknown"`, `"standard"` or `"ntc"`),
  `gene` and `ct`. `ct` is a number of cycles or the string `"Undetermined"`.
  An `unknown` well also has `sample`, the sample's name; a `standard` well also
  has `quantity`, a number, its relative amount of template.

## Report

A JSON object with these keys:

- `plate`: the plate's name.
- `genes`: one object per gene with `gene` (the name), `factor` (a number, the
  amplification factor) and `contaminated` (`true` or `false`).
- `results`: one object per sample and target gene with `sample`, `gene`,
  `mean_ct` (a number or `null`), `fold_change` (a number or `null`) and `flags`
  (a list of strings).

`examples/plate-demo.json` is a small plate in this format.
