# SUBMISSION — tbrain-newspaper-ad-layout

- Task: produce ad layouts for four newspaper editions at or below best-known cost targets under stacking, page-share, front-page and competitor-spread rules.
- Category: Operations / Marketing
- ZIP: `workspace/submissions/tbrain-newspaper-ad-layout.zip` (SHA-256 `bd4bba144e995fe4cd039175160aa28007484ed4cdfd64f5f572211b58148f59`)

# Difficulty Explanation

Each edition is the ad make-up a newspaper's advertising desk does before every print run: 58-138 ads of different column widths and depths go onto 16-32 pages of a six-column, 42-row grid. An ad must rest on the foot of the page or on ads across its whole width, a page carries at most 60 percent ads and the front page only a bottom strip, and two ads of one competitor group may not share a page or a spread. Booked ads must run; others earn their rate if placed, and section and right-hand-page requests cost a share of the rate when missed. It is two-dimensional packing with stacking, capacity and spread-level exclusion rules coupled to a revenue knapsack: which ads to leave out depends on which shapes pack together on which pages. An advertising make-up editor, the person who protects ad revenue at press time, has to search page assignments and packings together, because each target is the cheapest layout found by hours of large-neighbourhood search. The editions are synthetic but modelled on a regional daily's sections and ad rate card.

# Solution Explanation

solution/search.py is the search that produced the reference layouts: a large-neighbourhood search that clears one to four pages (random pages, one spread, or pages of one section), takes the cleared ads plus a sample of left-out ads in a randomized order, and puts each at its cheapest spot on the cleared pages, on the lowest flat stretch of the columns' filled heights, which is exact because an ad must rest across its whole width; steps are accepted by simulated annealing. Runs started from the shipped planner and later from the cheapest layout so far: 40-minute seeds, repeated shorter runs at varied temperatures, and single runs of two and four hours. Each target is the cost of the cheapest layout seen. solve.sh copies the four saved layouts and stops unless the checker reports each one valid within its target.

# Verification Explanation

The verifier reads the four layout files as JSON data and scores them with its own copy of the checker, editions and targets, so nothing the agent edits under /app affects grading and no candidate code runs. For each edition one test checks that the layout is valid (standard JSON within the stated limits, known ads with whole-number positions, inside the page, no overlap, resting on the foot or on ads, page share and front-page strip, competitor groups apart by spread, every booked ad placed) and one checks that its integer cost is at or below the target. The reference layouts sit exactly on the targets; the shipped planner's layouts cost 7114, 9167, 10544 and 13571 against targets of 4635, 6701, 7500 and 10601.

# Relevant Experience

Advertising operations and packing optimisation for print media: ad make-up under page-grid, stacking and competitor-separation rules, and large-neighbourhood search for rectangle packing with revenue trade-offs.

# Metadata

- Does this task use an approved canonical base image? Yes — `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
- Did you use a Task Inspiration from the Task Gallery? No

# Rubrics

Agent writes a layout for each of the four editions to /app/layouts/<edition>.json in the documented JSON format, +2
Agent places every ad inside its page, without overlap, resting on the foot of the page or on ads across its whole width, +3
Agent keeps each page within its ad share and the front page within its strip, and keeps competing ads off one page or spread, +3
Agent places every booked ad, +2
Agent brings every edition's layout cost to or below its target, +5
Agent searches over which ads to leave out and which pages take them together to protect ads revenue, rather than only packing ads in a fixed order, +3
Agent leaves an edition without a valid layout when its time runs out, -3
Agent edits the editions, targets, rules or checker instead of producing better layouts, -5
Agent imports third-party optimisation packages or uses the network, -2
