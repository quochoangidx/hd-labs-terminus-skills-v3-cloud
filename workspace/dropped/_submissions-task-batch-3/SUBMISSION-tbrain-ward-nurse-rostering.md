# SUBMISSION — tbrain-ward-nurse-rostering

- Task: produce four-week nurse rosters for four wards at or below best-known penalty targets under cover, grade, leave, rest and night-rest rules.
- Category: Software / Algorithms
- ZIP: `workspace/submissions/tbrain-ward-nurse-rostering.zip`

# Difficulty Explanation

Each ward is a four-week nurse roster for 16-36 nurses of three grades over early, late and night shifts. Hard rules (minimum cover with registered and senior nurses on every shift, leave, rest between shifts, at most six days in a row, two rest days after a run of nights) make most local changes infeasible, and the soft penalty trades preferred cover against contracted hours, night limits, split and excess weekends, isolated working days and personal requests. The rules interact across days and across nurses: fixing one nurse's weekend moves cover onto someone else, whose rest after nights then blocks a request three days later. A rostering expert has to build a search that moves blocks of shifts between nurses while tracking the hard rules incrementally; the shipped fill-the-gaps planner is valid but costs 7-12 times the target, and the targets come from multi-hour annealing runs, so a short search stops well above them. The wards are synthetic but use typical NHS-style contract and cover rules.

# Solution Explanation

The reference rosters come from simulated annealing in which a hard-rule breach costs 5000 and only rosters with no breach are kept. Moves: set one nurse's code on one day, swap two nurses' codes on one day, swap a block of two to seven days between two nurses, and rotate a block of one nurse's row by a day. Runs started from the shipped planner: several 40-minute seeds, iterated shorter anneals restarted from the best roster at varied temperatures, and fresh single anneals of one, two and four hours (fresh long anneals beat every restart on the two largest wards). Each target is the penalty of the cheapest roster seen. solve.sh copies the four rosters and runs the checker on each.

# Verification Explanation

The verifier reads the four roster files as JSON data and scores them with its own copy of the checker, wards and targets, so nothing the agent edits under /app affects grading and no candidate code runs. For each ward one test checks that the roster is valid (standard JSON within the stated limits, every nurse present with one of E, L, N or . per day, cover, grade, leave, rest, consecutive-day and after-night rules) and one checks that its integer penalty is at or below the target. The reference rosters sit exactly on the targets; the shipped planner's rosters score 5313, 12003, 9002 and 12287 against targets of 450, 1070, 830 and 1665.

# Relevant Experience

Workforce scheduling and optimisation: hospital nurse rostering with cover, rest and contract rules, soft-constraint penalty models, and annealing and neighbourhood search for rota planning.

# Metadata

- Does this task use an approved canonical base image? Yes — `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
- Did you use a Task Inspiration from the Task Gallery? No

# Rubrics

Agent writes a roster for each of the four wards to /app/rosters/<ward>.json in the documented JSON format, +2
Agent meets minimum, registered and senior cover on every shift of every day, +3
Agent keeps leave, rest between shifts, the consecutive-day limit and the rest days after a run of nights for every nurse, +3
Agent evaluates rosters with every soft penalty the rules define, including split weekends, lone days and broken requests, +2
Agent brings every ward's roster penalty to or below its target, +5
Agent builds a search that moves shifts between nurses and days while tracking the hard rules, rather than repairing one nurse at a time, +3
Agent leaves a ward without a valid roster when its time runs out, -3
Agent edits the wards, targets, rules or checker instead of producing better rosters, -5
Agent imports third-party optimisation packages or uses the network, -2
