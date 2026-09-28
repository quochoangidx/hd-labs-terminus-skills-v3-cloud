# SUBMISSION — tbrain-airport-gate-assignment

- Task: produce daily stand-allocation plans for four days at or below best-known cost targets, trading transfer walking against remote-stand bussing under size, border-control, buffer and wingtip rules.
- Category: Operations / Logistics
- ZIP: `workspace/submissions/tbrain-airport-gate-assignment.zip` (SHA-256 `df164038c369bddc29124385681ed80d5e96087a203fe00adfad81ad092f484c`)

# Difficulty Explanation

Each day is the stand plan an airport's apron planner draws up for the next day of flights: 180-360 aircraft turns on 31-63 stands, with stand size limits, border-control stands for international flights, a buffer between turns on one stand, and wingtip pairs of neighbouring stands that cannot hold two widebodies at once. The cost is transfer passengers walking between the stands of connecting flights plus a per-passenger bus charge for remote stands, so the plan is a quadratic assignment problem on top of interval scheduling: the value of a stand for one turn depends on where every connecting turn is, and moving one turn usually means moving the turns it collides with. An apron or stand planner, whose work sits between flight planning and ground transportation, has to search the assignments with moves that shift chains of turns and exchange what two stands hold over a time window, tuned to the size of a move and run for most of the time available, because each target is the cheapest plan found by hours of that kind of search. The days are synthetic but modelled on a three-pier terminal with a remote apron.

# Solution Explanation

solution/search.py is the search that produced the reference plans: simulated annealing over the stand rules with incremental cost updates, whose moves shift a turn to another stand it fits (sending the turns it collides with there back to its old stand) and exchange everything two stands hold over a time window that grows until no turn crosses its edges. Runs started from the shipped planner and later from the cheapest plan so far, pooled with the best plans from trial runs, with the temperature falling from 30000-60000 to 10-30 over 20-60 minutes, several seeds per day, until restarts stopped improving. Each target is the cost of the cheapest plan seen. solve.sh copies the four saved plans and stops unless the checker reports each one valid within its target.

# Verification Explanation

The verifier reads the four plan files as JSON data and scores them with its own copy of the checker, days and targets, so nothing the agent edits under /app affects grading and no candidate code runs. The verifier keeps each day as a gzip-compressed copy of /app/days/<day>.json and fails if its SHA-256 or its stand, turn and transfer counts differ from a roster. For each day one test checks that the plan is valid (standard JSON within the stated limits, every turn placed exactly once on a known stand, size, border control, buffer and wingtip rules) and one checks that its integer cost is at or below the target. The reference plans sit exactly on the targets; the shipped planner's plans cost 9077225, 12189855, 14519325 and 21326260 against targets of 7241380, 9017700, 10098740 and 15505590.

# Relevant Experience

Airport operations research for flight planning and ground transportation: stand and gate allocation with transfer-passenger walking costs, aircraft size and border-control constraints, and local-search and annealing methods for daily apron planning.

# Metadata

- Does this task use an approved canonical base image? Yes — `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
- Did you use a Task Inspiration from the Task Gallery? No

# Rubrics

Agent writes a plan for each of the four days to /app/plans/<day>.json in the documented JSON format, +2
Agent places every turn exactly once on a stand whose size and border control fit it, +3
Agent keeps the buffer between turns on one stand and never has two widebodies on a wingtip pair at once, +3
Agent evaluates plans with the rules' cost, including the diagonal walking entry and walking to and from remote stands, +2
Agent brings every day's plan cost to or below its target, +5
Agent builds a search that moves chains of turns or exchanges what two stands hold, rather than only relocating single turns, +3
Agent leaves a day without a valid plan when its time runs out, -3
Agent edits the days, targets, rules or checker instead of producing better plans, -5
Agent imports third-party optimisation packages or uses the network, -2
