# SUBMISSION — tbrain-hotel-folio-charges

- Task: Repair a hotel's checkout folio package so the room charge, city tax, occupancy tax and service fee on guest folios follow the hotel's folio charges rules.
- Category: Operations / Finance
- ZIP: `workspace/submissions/tbrain-hotel-folio-charges.zip` (sha256 9e6ec5d8907f1e33eb057bb4b721d61d656e43c228973a89b8cfc0b1281ee8cd)

# Metadata

- Does this task use an approved canonical base image? Yes — `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
- Did you use a Task Inspiration from the Task Gallery? No

# Rubrics

Agent charges a stay's nightly rate for each of its nights except every seventh night, which is free, +2
Agent gives a room at 5,000 cents a night or more a city tax of 250 cents for each of its first 14 nights and nothing for later nights, +2
Agent takes the occupancy tax at 13.5 per cent of the room charge, rounding an exact half cent up, +2
Agent keeps the folio total as the room charge, occupancy tax, city tax and service fee added together, and the file total as their sum, in file order, +1
Agent keeps the package's existing city tax for a room under 5,000 cents a night, nothing under 3,000 cents and otherwise 200 cents for every night with no limit on the nights, +3
Agent keeps the package's existing service fee, 3.5 per cent of the room charge rounded with Python's round so an exact half cent goes to the even cent, +3
Agent leaves /app/tools/folio_run.py byte-for-byte as shipped, +1
Agent gives a room under 5,000 cents a night a city tax of nought, the new 250-cent amount, or a 14-night stop, -3
Agent rounds the service fee half up by changing the shared rounding helper, -3
Agent still charges every night, or still rounds the occupancy tax half to even, -2
Agent edits the folio charges rules or hardcodes folio figures for particular files instead of repairing the package, -5
