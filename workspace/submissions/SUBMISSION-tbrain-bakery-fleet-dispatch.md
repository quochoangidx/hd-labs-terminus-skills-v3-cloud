# SUBMISSION — tbrain-bakery-fleet-dispatch

- Task: produce heterogeneous-fleet delivery plans with time windows for four mornings at or below best-known cost targets.
- Category: Operations / Logistics
- ZIP: `workspace/submissions/tbrain-bakery-fleet-dispatch.zip`

# Difficulty Explanation

Each morning is a heterogeneous-fleet vehicle routing problem with hard delivery windows, per-kind capacity, pace, shift length and range limits, fixed costs that dominate distance costs, and a limited count of each vehicle kind. The targets are the best plans found by several hours of multi-seed large-neighbourhood search, so a plan that is merely good fails. A routing engineer has to build a search that trades vehicle count against vehicle kind and distance at the same time, because the cheapest route on one kind is often not the cheapest plan once the fleet counts bind; has to choose departure times so long routes stay inside a shift without making an early-window stop late; and has to keep improving past the plateau where insertion heuristics and single-customer relocation stop, which takes moves that remove and rebuild several routes at once. The orders are synthetic but modelled on a wholesale bakery: clustered city customers, early market-hall windows, cafes with narrow morning windows, cargo bikes, vans and trucks. In practice this is the work of an operations-research or logistics engineer who builds and tunes route-optimisation for a distribution or last-mile delivery fleet.

# Solution Explanation

The reference plans come from a slack-induced string-removal search over the dispatch rules: remove short strings of consecutive customers from routes near a random customer, reinsert them at their cheapest feasible positions (a new route of any vehicle kind with spare count being one option), move each route to the cheapest kind that can run it and swap kinds between routes, and accept by simulated annealing; many seeds were run for a few hours in total and the cheapest plan kept. Departure times are the latest start that removes waiting without making any stop late, which keeps route duration inside the shift. The search is shipped as solution/search/sisr.py; solve.sh copies the four plans it produced and runs the checker on each.

# Verification Explanation

The verifier reads the four plan files as JSON data and evaluates them with its own copy of the dispatch rules and its own copies of the orders and targets, so nothing the agent edits in /app/tools or /app/orders affects grading and no candidate code runs. For each morning one test checks that the plan is runnable (every customer served exactly once, windows, capacity, shift, range, fleet counts, integer departures) and one checks that its integer cost is at or below the target. Plans are read as strict JSON through the checker's own loader, which rejects repeated keys, NaN and Infinity, and keys the plan format does not define. The reference plans pass all eight tests; the plans from the shipped planner fail (two mornings miss customers, the other two cost 30-45 percent over target).

# Relevant Experience

Operations research on vehicle routing and fleet sizing: building and tuning large-neighbourhood and string-removal searches for time-windowed routing with heterogeneous fleets, and validating plans against depot operating rules.

# Metadata

- Does this task use an approved canonical base image? Yes — `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
- Did you use a Task Inspiration from the Task Gallery? No

# Rubrics

Agent writes a plan for each of the four mornings to /app/plans/<morning>.json in the documented JSON format, +2
Agent delivers every customer exactly once within its delivery window on every morning, +3
Agent respects each vehicle kind's capacity, shift length, range and available count, +3
Agent chooses departure times that keep long routes inside the shift limit, +2
Agent brings every morning's plan cost to or below its target, +5
Agent builds a search that trades vehicle count and vehicle kind against distance rather than only reordering routes, +3
Agent leaves a morning without a runnable plan when its time runs out, -3
Agent edits the orders, targets, rules or checker instead of producing better plans, -5
Agent imports third-party optimisation packages or uses the network, -2
