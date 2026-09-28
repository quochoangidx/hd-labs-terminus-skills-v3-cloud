# SUBMISSION — tbrain-occupational-noise-dose-survey

- Task: Repair a hearing-conservation programme's noise-dosimetry survey package so its worker and similar-exposure-group dose, TWA and status report follows the programme's noise survey manual.
- Category: Operations / Compliance
- ZIP: `workspace/submissions/tbrain-occupational-noise-dose-survey.zip` (sha256 ca750008a84e5574ba9f27d86b72592ea5b4979a1c158e426400083d0264feef)

# Metadata

- Does this task use an approved canonical base image? Yes — `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
- Did you use a Task Inspiration from the Task Gallery? No

# Rubrics

Agent works reference durations from the programme's 85 dBA criterion and 3 dB exchange rate instead of the federal 90 dBA and 5 dB figures still in the package, +2
Agent counts a reading logged exactly at the 80.0 dBA threshold level toward the measured dose, +2
Agent makes sampled time the length of every reading of 40.0 dBA or more, so quiet readings below the threshold enter the projection while runs logged at 0.0 stay out, +2
Agent projects a partial survey, one that sampled at least three quarters of the shift, to the worker's own shift length rather than to 480 minutes, and leaves a survey of the whole shift or longer at its measured dose, +2
Agent reports the TWA as 85 + 3 log2(D/100) rounded to the nearest tenth of a decibel, giving no TWA for a shift dose of nought, +2
Agent puts workers in the action band from 82.0 dB and over the limit above 85.0 dB on the reported TWA, keeps a worker flagged for the ceiling or for impulse "over", and treats a 140.0 dBC peak as an impulse, +2
Agent takes each group's dose as the plain mean of its members' shift doses, a quiet member's nought included, and judges the group's TWA and status on that dose alone, without inheriting a member's ceiling or impulse flag, +2
Agent keeps the package's existing 480-minute scaling for a survey that sampled less than three quarters of its shift, fed by the manual's sampled time and measured dose, and keeps nought for a survey that measured nothing, +3
Agent keeps counting a reading logged above the 115.0 dBA ceiling level at the ceiling level when the rebuilt dose loop sums the measured dose, while still flagging that worker for the ceiling, +3
Agent leaves /app/tools/noisedose_run.py byte-for-byte as shipped, +1
Agent projects every survey shorter than the shift to the worker's shift, ignoring the three-quarter bound that defines a partial survey, -3
Agent reports a survey below three quarters of its shift at its unprojected measured dose instead of the package's existing scaling, -3
Agent evaluates the reference duration at the logged level for readings above 115.0 dBA, dropping the ceiling-level step when rewriting the dose loop, -3
Agent rounds the reported dose instead of reporting it as worked out, -2
Agent edits the noise survey manual or hardcodes report figures for particular surveys instead of repairing the package, -5
