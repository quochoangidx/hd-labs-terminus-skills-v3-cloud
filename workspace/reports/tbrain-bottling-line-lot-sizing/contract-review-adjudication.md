# contract_review adjudication (reviewer: fresh local Claude Opus subagent, blind to tests/solution; stb unavailable)
Verdict: accept with fixes. 6,000 random plans and 31 hand witnesses: rules and checker agree exactly.
1. Blocking-precondition, targets.json absent: accept; written by finalize with the reference costs (tool and grader copies identical).
2. Should-fix, targets reachable with stdlib: accept; targets come from a pure-stdlib annealer, stated in solve.sh and solution_explanation.
3. Should-fix, "each file in sites/" includes targets.json: accept; rules now say every file except targets.json.
4. Advisory, "almost every run": accept; reworded (every run pays its changeover).
5. Advisory, planner spills to later lines: accept; instruction reworded.
6. Advisory, edge cases stated: no action.
7. Advisory, missing file traceback: accept; loader reports "the file cannot be read" (both copies identical).
8. Advisory, lone surrogate / 1e400 in ignored keys: legal JSON, no scoring effect; no action.
