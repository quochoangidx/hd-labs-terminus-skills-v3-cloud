# SUBMISSION — tbrain-car-rental-agreement-billing

- Task: Repair a car and van hire branch's billing package so the time, mileage, fuel and tax charges on closed rental agreements follow the branch's rental charges manual.
- Category: Operations / Finance
- ZIP: `workspace/submissions/tbrain-car-rental-agreement-billing.zip` (sha256 6f5824b395c78a6707b7adfd5cc5a600bb99c82283826f7ca72c32a78ba5b882)

# Metadata

- Does this task use an approved canonical base image? Yes — `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
- Did you use a Task Inspiration from the Task Gallery? No

# Rubrics

Agent charges a rental of a day or more for its whole days of 1,440 minutes and one more day only when more than 59 minutes are left over, instead of every day begun, +2
Agent allows 150 free miles for each day charged instead of the old 100, and charges the mile rate for miles beyond it on every rental, a rental of under an hour included, +2
Agent adds 1,000,000 miles when the odometer came back reading less than it went out, so a turned-over odometer gives the true miles driven, +2
Agent charges every car brought back short of fuel, however short the rental, the fuel rate for each eighth short plus the 1,500-cent refuelling fee, +2
Agent taxes only the time and mileage charges at 8.25 per cent and rounds the tax to the nearest cent with an exact half cent going up, +2
Agent keeps the package's existing every-day-begun step for a rental under a day, so a rental of under an hour is still charged one day, +3
Agent keeps the package's existing fuel line for a car brought back with as much fuel or more, nought or a credit of the fuel rate per eighth over, with no refuelling fee, +3
Agent leaves /app/tools/rentcharge_run.py byte-for-byte as shipped, +1
Agent returns the branch and each agreement id exactly as the strings the file gives, and bills a file passed under any pathname, +1
Agent applies the 59-minute grace rule to rentals under a day, so a rental of under an hour is charged for no days, -3
Agent floors the fuel line at nought, or adds the refuelling fee, for a car brought back with as much fuel or more, -3
Agent still taxes the fuel charge or rounds the tax down, -2
Agent edits the rental charges manual, the README or the example file, or hardcodes bill figures for particular agreements, instead of repairing the package, -5

# Revision notes (rev2, answering evaluation 2)

1. [Coherent Contract] id declared an integer: the README bill schema now gives `id` as the agreement's id string, as given, and keeps "all integers" for the figures; instruction.md now says the branch and each id are compared as the strings given and every other figure as a JSON integer. The verifier already compared id as a string, so no grading changed; a package returning the numeric id "0" as 0 fails `test_bill_order_and_file_totals`.
2. [Sound Verifier] refuelling fee on a sub-day rental: `traps_combined` now bills rentals of 1 minute, 30 minutes, 10 hours and 1,439 minutes that come back short of fuel, the report's case among them (fuel charge 2,100, total 7,513). A fee kept to day rentals, to an hour or more, or to ten hours or more now fails.
3. [Sound Verifier] mileage past the allowance under an hour: the same file now bills 59- and 30-minute rentals past 150 miles (the report's case: mileage charge 30, total 5,445, and one over a turnover), plus 10-hour and 1,439-minute ones. No mileage charge under an hour or a day, and turnover only on day rentals, now fail.

Only `11-traps_combined.jsonl` gained cases; the limits file's ids were shortened (no figure moved) so it stays within one panel read. The rule-per-test layout, the other sealed files and the reference patch are unchanged.
