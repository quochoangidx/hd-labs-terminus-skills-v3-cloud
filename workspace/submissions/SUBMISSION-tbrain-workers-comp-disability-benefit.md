# SUBMISSION — tbrain-workers-comp-disability-benefit

- Task: Repair a workers' compensation claims unit's temporary disability indemnity package so its per-claim benefit statements (average weekly wage, weekly rate, waiting and retroactive days, total and partial disability amounts) follow the unit's benefits manual.
- Category: Operations / Claims
- ZIP: `workspace/submissions/tbrain-workers-comp-disability-benefit.zip` (sha256 7a094e3c0fa096b22e80c6959d367c9db1c5e315c4d5d231c34558fa098e9afc, rev3)

# Metadata

- Does this task use an approved canonical base image? Yes — `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
- Did you use a Task Inspiration from the Task Gallery? No

# Rubrics

Agent credits a wage line of 2,000 cents or more, a week's pay, to the payroll week before its Friday payday's week, the week whose work it pays, instead of the week it was paid in, +2
Agent divides the base-period wages by thirteen for every worker, including one paid in only a few base weeks or in none, rather than by the number of weeks that received pay, +2
Agent sets the weekly rate at two thirds of the average weekly wage in place of the package's 60 per cent, rounded to the nearest cent, +2
Agent bounds the rate with the maximum and minimum of the rate-table row in force on the date of injury, not the newest row, including an injury on the very day a row takes effect and the last row of a 40-row table, and applies the row's figures as given, however low the maximum or high the minimum, +2
Agent pays a worker whose average weekly wage is below that minimum the wage itself as the weekly rate instead of lifting it to the minimum, +2
Agent counts both the first and the last day of every certified period as disability days, +2
Agent treats only the first three disability days as the waiting period and pays them back as retroactive days once the claim reaches fourteen disability days, +2
Agent rounds the total-disability amount, weekly rate times paid days over seven, to the nearest cent rather than truncating it, +2
Agent keeps a correction line below 2,000 cents counting toward the week that holds its payday while moving every week's pay back a week, so a correction paid in the week of injury stays out of the base period and one paid in the first base week stays in, +3
Agent keeps paying a partial-earnings week below 1,000 cents at the package's existing 60 per cent of its wage loss, rounded to the cent and capped at the weekly rate, while weeks of partial disability move to two thirds, +3
Agent leaves /app/tools/tdbenefit_run.py byte-for-byte as shipped, +1
Agent shifts every wage line a week earlier when fixing the payroll lag, corrections included, -3
Agent drops wage lines below a week's pay from the base-period wages instead of leaving them in their payday's week, -2
Agent changes the shared RATE_FRACTION to two thirds so that weeks under 1,000 cents are also paid two thirds of their loss, -3
Agent pays nothing for a partial week under 1,000 cents, treating it as no week of partial disability at all, -2
Agent floors a low week's 60 per cent share to the cent or lets it exceed the weekly rate, -1
Agent edits the benefits manual or hardcodes statement figures for particular claims instead of repairing the package, -5

# Revision notes (rev1, answering the v1 quality panel)

Tests-only revision: instruction.md, environment/ and solution/ are byte-identical to v1.

1. [Sound Verifier] The fortieth row of a 40-row table was never in force: new test `test_rule_3_4_row_figures_at_their_ends_decide_the_rate` states a 40-row daily table whose last row (maximum 20,000) sets the rate. A lookup over the first 39 rows now fails.
2. [Sound Verifier] A low maximum never bound: the same test adds a 20,000 maximum holding an unbounded 20,001 (AWW 30,001). A maximum floored at 30,000 now fails.
3. [Sound Verifier] A high minimum never decided the rate: the same test adds a 100,001 minimum lifting 66,667 (AWW exactly 100,001). A minimum capped at 100,000 now fails. As part of the same sweep, a 1,000 minimum lifting 800 also catches an invented minimum floor.

All four mutants passed v1 (reward 1) and fail rev1 on the new test. The 29 earlier sweep mutants and 16 wrong paths still fail as before, and Oracle 1 / NOP 0.

# Revision notes (rev2, answering the v2 quality panel)

Tests-only revision: instruction.md, environment/ and solution/ are byte-identical to v2 (and v1). Only tests/ and the verification explanation changed.

1. [Sound Verifier, Major] No register with more than 52 distinct Friday paydays was graded. New test `test_register_of_more_than_52_distinct_paydays` works by hand the panel's own case (53 weekly lines of 2,000 cents, 2024-01-05 to 2025-01-03, injury 2025-01-06: AWW 1,846, rate 1,231) and a 57-payday register (AWW 2,000, rate 1,333). The reference with a guard that refuses more than 52 paydays scored 1 on v2 and now fails this test.
2. [Sound Verifier, Minor] Every numeric input came from the sealed corpus. New test `test_jobs_drawn_at_run_time` draws four jobs at run time (seeded from os.urandom in rev2; fixed seeds since rev3, see below): fresh rate tables, 20 to 60 claims, registers up to every Friday of the 431-day window (the first claim always has more than 52 distinct paydays), non-edge corrections, 1 to 12 periods and partial weeks of 1,000 cents or more, all inside section 1 and free of the two cases left to today's code. They are graded against `tests/manual_model.py`, a byte copy of `solution/model.py`, which the candidate cannot read. A lookup table of every sealed claim scored 1 on v2 and now fails this test. Offline, the model and the Oracle agree on 6,000 drawn jobs.

Previous findings (rev1: 40th row, low maximum, high minimum) remain closed; their mutants still fail. All 17 earlier wrong paths and the sweep catalog still fail on their own tests. Oracle 1, NOP 0, three repeat Oracle runs 1.

# Revision notes (rev3, answering the v3 quality panel)

Tests-only revision: instruction.md, environment/ and solution/ are byte-identical to v3 (and v1). Only tests/test_outputs.py and the verification explanation changed.

1 and 2. [Deterministic Execution, Major ×2] The drawn jobs came from an os.urandom seed, so clean runs graded different jobs. Now `DRAW_SEEDS = (5, 6, 31, 139)` draws one job per seed, so every clean run grades the same four jobs. The set is chosen to include both flip cases the panel described, and the test asserts both are present. Seed 5 draws a 40-row table with 38 claims, and seed 6 draws a row taking effect on 2016-01-02. Two single-row jobs are also included. The claim relabelling seed, also from os.urandom, is now fixed at 20260928. No randomness in the verifier comes from the OS now. The panel's two flip submissions are the reference with a wrong total, one when a job has 40 rows and 20 to 60 claims, the other when any row starts on 2016-01-02. Both were accepted by v3 (reward 1) and both fail rev3 on `test_jobs_drawn_at_run_time`.

Earlier findings (rev1, rev2) stay closed. All 19 earlier wrong paths and the 33-entry sweep catalog still come out as expected. Oracle 1, NOP 0, and the determinism re-run is identical.
