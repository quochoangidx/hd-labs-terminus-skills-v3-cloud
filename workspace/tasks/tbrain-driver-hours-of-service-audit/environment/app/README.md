# hoslog

Hours-of-service audit of a driver's duty-status log.

- `src/hoslog/`: the package; `audit_log(log)` returns the report
- `tools/hoslog_run.py`: the driver the safety team runs, `python3 tools/hoslog_run.py LOG.json`
- `docs/hours-manual.md`: FM-4, the fleet's hours-of-service manual, which the package implements
- `examples/two-day-log.json`: a short log in the input format

A log is a JSON object with `driver`, `end`, `recap` and `events`, laid out as
FM-4 section 1 describes. Each event is `{"at": minute, "status": ..., "miles": ...}`.
`miles` comes from the truck's engine connection and is recorded on every entry,
whatever its status: it is the distance the truck covered while the entry was in force.

The report is the JSON object of FM-4 section 6, printed on one line.
