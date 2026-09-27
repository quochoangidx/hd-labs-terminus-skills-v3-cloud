# SUBMISSION — tbrain-icpms-sop-data-reduction

- Task: repair an ICP-MS trace-metal data-reduction package so its batch report follows the laboratory's SOP, while keeping the shipped calculation wherever the SOP gives no rule.
- Category: Science / Chemistry
- ZIP: `workspace/submissions/tbrain-icpms-sop-data-reduction.zip`

# Metadata

- Does this task use an approved canonical base image? Yes — `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
- Did you use a Task Inspiration from the Task Gallery? No

# Rubrics

Agent fits each analyte's calibration line by ordinary least squares with a fitted intercept instead of forcing it through the origin, +2
Agent sets the blank level to the mean of every method-blank result in the batch wherever the blank sits in the run order, leaving non-detect blanks out of that mean, +3
Agent subtracts the blank level from the reading before multiplying by the dilution, so the reported amount is the corrected reading times the dilution, +2
Agent judges ND, J and the empty flag on the blank-corrected reading rather than on the diluted amount, with no tolerance added to either limit, +2
Agent passes a CCV when its recovery rounded to one decimal lies from 90.0 to 110.0 inclusive while still reporting the unrounded recovery, +2
Agent gives a bracketed sample or spike a ccv_ok of false when either the nearest CCV before it or the nearest CCV after it failed, +2
Agent computes a spike recovery from two results as the spike amount less the parent amount over the amount added, +2
Agent keeps the blank level the package computes today for an analyte whose blanks include no result, rather than inventing a level such as nought, +3
Agent leaves ccv_ok for a run with a CCV on only one side, or with none, to the check the package already makes, +3
Agent keeps the shipped recovery calculation for a spike whose spike or parent is a non-detect, since the SOP gives no rule for that value, +3
Agent emits every report list in run order and, within a run, in the order of the batch's analytes, with value null only for ND entries, +1
Agent leaves /app/tools/metalquant_run.py byte-identical to the shipped driver, +1
Agent sets the blank level to nought, or to some other new figure, when a batch has blanks but none of them is a result, -3
Agent applies the amount-added formula of section 7 to spikes whose spike or parent is a non-detect, -3
Agent clamps readings, corrected readings or amounts (below nought, above the top standard or at any cap), or adds another guard the SOP does not give, -2
Agent edits the SOP or the driver, or hardcodes report figures for known batches instead of computing them, -5
