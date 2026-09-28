# SUBMISSION — tbrain-local-magnitude-network-reduction

- Task: repair a regional seismic network's local-magnitude bulletin package so its station and network ML follow the network's processing manual NPM-4, while keeping the shipped calculation where the manual gives no rule.
- Category: Science / Earth
- ZIP: `workspace/submissions/tbrain-local-magnitude-network-reduction.zip`

# Metadata

- Does this task use an approved canonical base image? Yes — `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
- Did you use a Task Inspiration from the Task Gallery? No

# Rubrics

Agent forms the Wood-Anderson record amplitude as half the picker's peak-to-peak value at the manual's magnification of 2080 rather than Richter's 2800, +2
Agent uses the hypocentral distance from epicentral distance and event depth for the correction, the reported distance_km and the decision of which stations contribute, +2
Agent interpolates the -log A0 correction linearly in distance between the table's listed distances and returns the listed value at each listed distance, +2
Agent adds each station's correction as it stands in the station table instead of subtracting it, +1
Agent builds a station magnitude as the mean of its readings' channel magnitudes, whatever their channel codes, leaving out amplitudes below three times their channel's noise at every distance and at two-sensor sites alike, rather than taking the largest channel, +3
Agent forms the network magnitude as the median of the contributing stations, averaging the two middle values for an even count, +2
Agent reports a null network magnitude for an event with fewer than three contributing stations, +2
Agent keeps the package's existing log-distance end-segment correction for stations nearer than 10 km or beyond 600 km, fed with the hypocentral distance, while those stations stay out of the network magnitude, +3
Agent treats a site whose broadband and strong-motion sensors arrive as separate recordings as one station, pooling their readings into one magnitude shown on both rows and counting it once in the median and the three-station minimum, +3
Agent leaves tools/ml_bulletin.py byte-for-byte unchanged and makes every repair inside the mlnet package, +1
Agent swaps log10(distance) for distance throughout the correction's segment formula, so stations beyond the table get a linearly extrapolated correction, -3
Agent clamps, nulls or otherwise guards the correction or station magnitude for a station the table does not reach, -2
Agent keeps one magnitude per recording, so a two-sensor site is averaged per sensor or votes twice in the median and the three-station count, -3
Agent averages every amplitude a recording lists, noise-swamped channels included, -2
Agent rewrites the NPM-4 manual or the driver to fit the package instead of repairing the package, -5
