# SUBMISSION — tbrain-press-shop-scheduling

- Task: produce weekly stamping-press schedules for four weeks at or below best-known cost targets, balancing die changeovers against weighted lateness around maintenance windows.
- Category: Operations / Supply chain
- ZIP: `workspace/submissions/tbrain-press-shop-scheduling.zip`

# Difficulty Explanation

Each week is unrelated parallel-machine scheduling with sequence-dependent die changeovers, press tonnage eligibility, release times, weighted tardiness and maintenance windows that no changeover or run may overlap. Changeover cost and lateness pull in opposite directions: grouping a die family saves hours of changeover but pushes other families' jobs past their due times, and the maintenance windows make the timing of a sequence non-obvious (a job that no longer fits before a window slips past it, and the knock-on delay moves every later job). The targets are the best schedules found by several rounds of multi-seed ruin-and-recreate search and local search, pooled with the best schedules from trial runs, so a production planner has to build a search that works on assignment and sequence together; dispatch rules like the shipped earliest-due-date planner land two to four times over target, and two GPT-5.6 runs with the Codex agent used their full 90 minutes, matched the targets for weeks 36 and 37, and stayed 0.2-2.2 percent over target on weeks 38 and 39. The weeks are synthetic but modelled on a stamping line: six die families, a changeover matrix of 35-120 minutes between families and 10 minutes within one, presses of 200-800 t with different stroke rates, and one or two maintenance windows per press.

# Solution Explanation

The reference schedules come from a ruin-and-recreate search: remove a few jobs (random, one die family, jobs with nearby due times, or a run of consecutive jobs on one press), reinsert each at its cheapest position on any press with enough tonnage, occasionally skipping a position, and accept by simulated annealing; several seeds per week, half an hour each. Schedules from trial runs were pooled with the search's own and the search restarted from the cheapest in further rounds; weeks 37-39 were finished with an iterated local search (exhaustive relocation, swaps and moves of blocks of up to eight consecutive jobs, with small ruin-and-recreate kicks). Rounds stopped when restarts no longer improved any week. solve.sh copies the four schedules and runs the checker on each.

# Verification Explanation

The verifier reads the four schedule files as JSON data and runs them with its own copy of the press rules and its own copies of the weeks and targets, so nothing the agent edits under /app affects grading and no candidate code runs. For each week one test checks that the schedule is valid (every job exactly once, on a press with enough tonnage, known ids) and one checks that its integer cost, computed by simulating changeovers, releases and maintenance windows, is at or below the target. The reference schedules pass all eight tests; the shipped planner's schedules cost 100000, 160603, 307200 and 410333 against targets of 33983, 47936, 77699 and 112876.

# Relevant Experience

Production scheduling and operations research: sequence-dependent setup scheduling on parallel machines, weighted tardiness objectives, and large-neighbourhood search for shop-floor planning.

# Metadata

- Does this task use an approved canonical base image? Yes — `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
- Did you use a Task Inspiration from the Task Gallery? No

# Rubrics

Agent writes a schedule for each of the four weeks to /app/schedules/<week>.json in the documented JSON format, +2
Agent places every job exactly once on a press whose tonnage is at least the job's, +3
Agent models changeovers, releases and maintenance windows the way the press rules define them when it evaluates candidate schedules, +3
Agent brings every week's schedule cost to or below its target, +5
Agent builds a search that changes press assignment and job order together rather than only reordering jobs within a press, +3
Agent trades changeover minutes against weighted lateness instead of only grouping jobs by die family, +2
Agent leaves a week without a valid schedule when its time runs out, -3
Agent edits the weeks, targets, rules or checker instead of producing better schedules, -5
Agent imports third-party optimisation packages or uses the network, -2
