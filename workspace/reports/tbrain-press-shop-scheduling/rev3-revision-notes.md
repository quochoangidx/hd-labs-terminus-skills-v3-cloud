# tbrain-press-shop-scheduling rev3 (platform submission f60dccff, v3 + v4 `solvable` returns)

Returned snapshot: v4/tbrain-press-shop-scheduling-source.zip = rev2 (sha256 aaa25cb9...8163, untouched; v3 was the same bytes)
Revised ZIP: revisions/tbrain-press-shop-scheduling-rev3.zip = submissions/tbrain-press-shop-scheduling.zip
sha256 9be2067a6dc65ea45c560066a8597abb898c98f120c4ac9418e9ba31a0b918b9

## Finding (blocking quality gate `solvable`, v3 and v4)
Targets equalled the best cost ever found (12 authoring rounds, pooled seeds incl. trial outputs), zero slack,
while the agent had 5400 s on 2 CPUs; no evidence the bar was reachable within that budget.

## Evidence gathered (Apple M1, one core per week, fresh start, no pooling)
| week | best known | run A: lns 45m + ils 20m (seed 101) | run B: lns 70m + ils 30m (seed 202) |
|---|---|---|---|
| 36 | 33983 | 33983 (0%) | 33983 (0%) |
| 37 | 47936 | 50087 (+4.49%) | 50087 (+4.49%) |
| 38 | 77699 | 79717 (+2.60%) | 81637 (+5.07%) |
| 39 | 112876 | 118165 (+4.69%) | 118759 (+5.21%) |
Logs: workspace/reports/tbrain-press-shop-scheduling/rev3-single-session/{,budget/}

## Decision: narrow the bar (oracle-near threshold -> documented margin) + budget
- targets = floor(best x 1.06): 36021, 50812, 82360, 119648 (tests/ and environment/app/weeks/ identical)
- instruction.md: "Each target is 6 percent above the cost of the best schedule the planning office has found"
- [agent].timeout_sec 5400 -> 14400
- solution/search/one-session/: run B schedules (all meet targets, 8/8 in the verifier image)
- solution_explanation / difficulty_explanation / verification_explanation / solve.sh table rewritten to the new facts
- reference schedules (best known) unchanged as the oracle
Shipped EDD planner still fails all four target tests (4 failed, 4 passed).

## Risk
GPT-5.6 in earlier 90-min runs reached 0-2.2% over best known, i.e. well inside 6%. The platform
requires >= 3/8 failures; this revision may now be too easy. Difficulty not yet re-measured.

Validation: instruction_preflight OK; scripts/preflight.sh --strict all PASS (both builds, Oracle=1, NOP=0, noexec Oracle=1).
