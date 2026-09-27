# mlnet

Local-magnitude reduction for the Brennock Range Seismic Network bulletin.

- `mlnet/`: the package; `reduce_bulletin(bulletin)` takes a parsed bulletin file and returns its magnitude report
- `tools/ml_bulletin.py`: the driver the bulletin desk runs, `python3 tools/ml_bulletin.py BULLETIN.json`, which prints the report as JSON
- `manual/npm4-local-magnitude.md`: NPM-4, the part of the processing manual the package implements; the bulletin file is laid out in its section 1 and the report in its section 6
- `samples/brsn-2026-04-12.json`: the bulletin of one day
