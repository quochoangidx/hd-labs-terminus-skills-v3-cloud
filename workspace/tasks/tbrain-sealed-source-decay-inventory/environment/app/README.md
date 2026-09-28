# sealsrc

Quarterly survey of the Radiation Protection Office's sealed-source inventory.

- `src/sealsrc/`: the package; `survey(inventory)` returns the report
- `tools/sealsrc_run.py`: the driver the Office runs, `python3 tools/sealsrc_run.py INVENTORY.json`
- `docs/source-inventory-manual.md`: manual RPO-7, which the package implements
- `examples/small-inventory.json`: a small inventory in the input layout

## Inventory file (JSON)

- `survey_date`: the survey date, `YYYY-MM-DD`
- `locations`: list of `{"id": string, "limit_bq": number}`, the storage locations
- `sources`: list of inventory entries, each
  `{"id": string, "nuclide": string, "ref_bq": number, "ref_date": "YYYY-MM-DD", "location": string, "leak_tests": [...]}`;
  `ref_bq` and `ref_date` are the activity and reference date on the source's
  certificate, `location` is the location id the entry names, and `leak_tests`
  lists the wipes taken of the source, each `{"date": "YYYY-MM-DD", "removable_bq": number}`,
  in the order the counting room returned them (not necessarily by date); the
  list is empty when the source has never been wiped

## Report (JSON, printed on standard output)

- `survey_date`: copied from the inventory
- `sources`: one row per entry, in inventory order:
  `{"id", "nuclide", "location", "activity_bq", "daughter_bq", "exempt", "leak_test_due", "disposal_eligible"}`,
  with `activity_bq` the current activity, `daughter_bq` the daughter activity
  (both numbers) and the other three true or false
- `locations`: one row per location, in inventory order:
  `{"id", "held_bq", "sources", "fraction_of_limit", "over_limit"}`, with
  `held_bq` the held activity and `fraction_of_limit` numbers, `sources` the
  source count as an integer, and `over_limit` true or false
