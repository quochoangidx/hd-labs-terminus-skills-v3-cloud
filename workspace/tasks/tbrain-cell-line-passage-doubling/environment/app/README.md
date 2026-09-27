# cellbank

Lineage report for a cell line's passage log.

- `src/cellbank/`: the package; `build_report(log)` returns the report
- `tools/cellbank_run.py`: the driver the core runs, `python3 tools/cellbank_run.py LOG.json`
- `docs/cell-bank-sop.md`: SOP CB-3, which the package implements
- `examples/small-log.json`: a small passage log in the input format

A log is a JSON object with `lines` and `records`. A line has `name`, `seed_pdl`,
`seed_passage` and `max_pdl`. A record has `id` and `kind`, and then:

- `thaw`: `line`, `vial` (a `freeze` id, or `null`), `cells`, `viability`
- `culture`: `source` (a `thaw` or `culture` id), `seeded`, `harvested`, `viability`
- `freeze`: `source` (a `culture` id), `bank`, `vials`

Cell numbers are integers; `viability` is a percentage such as `92.5`. Records are listed
in the order the work was done.
