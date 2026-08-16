# Local Solve Evidence Schema

This is the handoff contract between `probe.py` and `batch-handover.py`.
Receipts are generated from raw artifacts; do not hand-author a passing result.

## Probe manifest — schema 3

`workspace/local-solve-probes/<slug>/probe-manifest.json` records:

- `task_slug` and the absolute `source_task`;
- `mode`: `exploratory` or `counted`;
- `profile`: `general` or `advanced_frontier_only`;
- the sanitized solver-contract hash and complete task snapshot hash;
- for counted probes, paths and SHA-256 values for
  `instruction-sufficiency.json`, `semantic-coverage.json`, and
  `verifier-matrix.json`;
- SHA-256 values for `probe-preflight.json`, `pre-freeze-review.json`,
  `task-style-preflight.json`, and `agent-session-budget.json` after
  `preprobe_check.py` validates them;
- a passing `quota-ledger.json` pre-solver check. The ledger is intentionally
  not frozen into `preprobe_receipts` because each subsequent solver invocation
  must append a turn; final handover validates the complete append-only ledger;
- preparation time.

Counted preparation first validates V3 evidence inferability and semantic
coverage, then proves the exact same snapshot has Docker Oracle/NOP validity,
pre-freeze client review, and task-visible prose quality. The campaign profile uses the semantic checker's
`--advanced-plus` geometry. Changing the task, profile, either evidence
receipt, or verifier matrix requires a new probe directory and fresh runs.
Exploratory manifests intentionally omit semantic receipts and can never pass
final handover.

## Per-run result — schema 2

Each `run_N/result.json` must bind:

- a unique fresh-agent session, actual runtime/model/reasoning effort, and
  launch command;
- `pass` or `fail`, with only `semantic` failures eligible for difficulty;
- the exact verification command, exit code, reward, and task snapshot;
- SHA-256 values for `solve.diff`, verifier log, CTRF, derived case matrix, and
  raw agent transcript.

`probe.py record` derives the case matrix from CTRF. `probe.py materialize`
reconstructs `verify/` as the current full task plus only the solver's
`environment/` delta. Handover recomputes both and reruns the trusted NOP
verifier against every materialized solve.

## Semantic interpretation

Every verifier behavior ID is mapped by `semantic-coverage.json` to at least
one mechanism or interaction. Probe geometry is computed from those nodes,
not from fixture count:

- a two-run split requires the adaptive third run;
- campaign `1/3` is provisional Advanced only when both failures span at
  least two nodes and the node sets differ;
- zero-solve Frontier additionally requires complete per-case union, no common
  miss, and de-correlated semantic-node failures;
- setup, compile, dependency, timeout, refusal, stale snapshot, or incomplete
  evidence is never a difficulty signal.

The diagnostic summary cannot emit `candidate_ready`. Only
`scripts/batch-handover.py` can do so after validating the raw probe bundle and
all other task receipts.
