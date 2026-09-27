# SUBMISSION — tbrain-library-overdue-fines

- Task: Repair a county library's circulation package so the due days, late days and fines on returned loans follow the library's overdue fines policy.
- Category: Operations / Finance
- ZIP: `workspace/submissions/tbrain-library-overdue-fines.zip` (sha256 f6458456d33a981b3e408127ede30a6f309ce990756ffe610e918e92e0ba4525)

# Metadata

- Does this task use an approved canonical base image? Yes — `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
- Did you use a Task Inspiration from the Task Gallery? No

# Rubrics

Agent gives a book a loan period of 21 days and a DVD 7 days, the due day being the borrowing day plus the period, +2
Agent counts a late loan's late days as the days after its due day up to and including its return day that are not Sundays, taking every day whose number leaves 6 when divided by 7 as a Sunday, +2
Agent caps a late loan's fine at its replacement cost, a fine exactly on the cost staying as it is, +2
Agent keeps the statement total as the plain sum of every loan's fine, in file order, +1
Agent keeps the package's existing 14-day loan period for a journal, +3
Agent keeps the package's existing late days and fine for a loan returned on or before its due day, its return day less its due day and that many days at its daily fine, nought or a credit, +3
Agent leaves /app/tools/finebook_run.py byte-for-byte as shipped, +1
Agent gives a loan returned on or before its due day nought late days or a fine of nought where today's step gives a negative figure, -3
Agent gives a journal a loan period of 7 or 21 days, -3
Agent still counts Sundays as late days, counts the due day itself, or leaves the return day out, -2
Agent edits the overdue fines policy or hardcodes statement figures for particular files instead of repairing the package, -5
