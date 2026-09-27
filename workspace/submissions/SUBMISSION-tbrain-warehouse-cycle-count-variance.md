# SUBMISSION — tbrain-warehouse-cycle-count-variance

- Task: Repair a distribution centre's cycle-count package so its variance report (final counts, class tolerances, recount and adjust status, booked units and shrink) follows the centre's cycle count procedure.
- Category: Operations / Supply chain
- ZIP: `workspace/submissions/tbrain-warehouse-cycle-count-variance.zip` (sha256 e3336b63e799b619c6d495b4b985e7e954240a5952b2f3b58c377845e7b8c4b3)

# Metadata

- Does this task use an approved canonical base image? Yes — `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
- Did you use a Task Inspiration from the Task Gallery? No

# Rubrics

Agent takes a line's recount as its final count whenever a recount was taken, including a recount of nought, +2
Agent gives graded items a tolerance of nought for class A, 2 per cent for class B and 5 per cent for class C of the system quantity, dropping any fraction of a unit, +2
Agent marks a line outside tolerance "recount" when no recount was taken and "adjust" when one was, with a variance exactly on the tolerance "ok", +2
Agent has an adjusted line book its variance worked from the final count, +2
Agent sums shrink over adjusted shortages only, so a surplus or a line awaiting recount never changes it, +2
Agent keeps the package's existing 5 per cent tolerance with Python's round for a line whose class is not A, B or C, +3
Agent keeps the package's existing booked figure, the count less the system quantity, for a line that is not adjusted, even when its recount changed the variance, +3
Agent leaves /app/tools/cyclecount_run.py byte-for-byte as shipped, +1
Agent books the variance, or nought, on lines that are not adjusted, -3
Agent gives lines of other classes a tolerance of nought, or drops the fraction for them, -3
Agent still nets surpluses against shrink or counts shortages that were not adjusted, -2
Agent edits the cycle count procedure or hardcodes report figures for particular sheets instead of repairing the package, -5
