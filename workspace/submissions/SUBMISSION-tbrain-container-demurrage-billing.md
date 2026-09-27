# SUBMISSION — tbrain-container-demurrage-billing

- Task: Repair a container terminal's demurrage billing package so the dwell, free days, demurrage days and charges on its release files follow the terminal's demurrage tariff.
- Category: Operations / Logistics
- ZIP: `workspace/submissions/tbrain-container-demurrage-billing.zip` (sha256 ZIPSHA)

# Metadata

- Does this task use an approved canonical base image? Yes — `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
- Did you use a Task Inspiration from the Task Gallery? No

# Rubrics

Agent counts a container's dwell from its discharge day to its pickup day with both days included, +2
Agent gives a dry container 5 free days and a reefer container 3, +2
Agent charges a container on demurrage its daily rate for each of its first 4 demurrage days and twice its daily rate for each day after the fourth, +2
Agent keeps the statement total as the plain sum of every container's charge, in file order, +1
Agent keeps the package's existing 5 free days for a tank container, +3
Agent keeps the package's existing days and charge for a container picked up inside its free time, its dwell less its free days and that many days at the rate, nought or a credit, +3
Agent leaves /app/tools/demurrage_run.py byte-for-byte as shipped, +1
Agent floors the days or the charge of a container inside its free time at nought, -3
Agent gives a tank container nought or 3 free days, -3
Agent still charges every demurrage day at the single daily rate, or starts the doubled rate after a day other than the fourth, -2
Agent edits the demurrage tariff or hardcodes statement figures for particular files instead of repairing the package, -5
