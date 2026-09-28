# metalquant

Data reduction for ICP-MS trace-metal batches.

- `src/metalquant/`: the package; `reduce_batch(batch)` returns the report
- `tools/metalquant_run.py`: the driver the laboratory runs, `python3 tools/metalquant_run.py BATCH.json`
- `docs/reduction-sop.md`: SOP TM-07, which the package implements
- `examples/small-batch.json`: a small batch in the input format
