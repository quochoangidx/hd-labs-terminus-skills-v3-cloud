# SUBMISSION — tbrain-car-rental-agreement-billing

- Task: Repair a car and van hire branch's billing package so the time, mileage, fuel and tax charges on closed rental agreements follow the branch's rental charges manual.
- Category: Operations / Finance
- ZIP: `workspace/submissions/tbrain-car-rental-agreement-billing.zip` (sha256 0921c086b71f054a74dc622ffaf057c87b1fb2b9e7fec8aa5ca834804b6b2906)

# Metadata

- Does this task use an approved canonical base image? Yes — `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
- Did you use a Task Inspiration from the Task Gallery? No

# Rubrics

Agent charges a rental of a day or more for its whole days of 1,440 minutes and one more day only when more than 59 minutes are left over, instead of every day begun, +2
Agent allows 150 free miles for each day charged instead of the old 100, and charges the mile rate only for miles beyond the allowance, +2
Agent adds 1,000,000 miles when the odometer came back reading less than it went out, so a turned-over odometer gives the true miles driven, +2
Agent charges a car brought back short of fuel the fuel rate for each eighth short plus the 1,500-cent refuelling fee, +2
Agent taxes only the time and mileage charges at 8.25 per cent and rounds the tax to the nearest cent with an exact half cent going up, +2
Agent keeps the package's existing every-day-begun step for a rental under a day, so a rental of under an hour is still charged one day, +3
Agent keeps the package's existing fuel line for a car brought back with as much fuel or more, nought or a credit of the fuel rate per eighth over, with no refuelling fee, +3
Agent leaves /app/tools/rentcharge_run.py byte-for-byte as shipped, +1
Agent applies the 59-minute grace rule to rentals under a day, so a rental of under an hour is charged for no days, -3
Agent floors the fuel line at nought, or adds the refuelling fee, for a car brought back with as much fuel or more, -3
Agent still taxes the fuel charge or rounds the tax down, -2
Agent edits the rental charges manual or hardcodes bill figures for particular agreements instead of repairing the package, -5
