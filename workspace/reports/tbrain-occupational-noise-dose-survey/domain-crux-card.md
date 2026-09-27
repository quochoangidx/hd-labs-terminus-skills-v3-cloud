# Domain-crux card (pattern-blind, written before the pattern catalog)

Slug: tbrain-occupational-noise-dose-survey
Date: 2026-09-26, builder A, task-batch 6 (builder_certified)

## Domain-native failure mode

An industrial hygienist's noise-survey tool turns personal dosimeter logs into a
programme exposure report. The programme (a fictional employer hearing
conservation programme, manual HC-4) is stricter than the federal rule the tool
was first written for: an 85 dBA criterion with a 3 dB exchange rate instead of
OSHA's 90 dBA / 5 dB, an action level at 82 dB, a limit above 85 dB. The tool
still carries the federal constants and several bookkeeping slips a real
programme tool accumulates: a threshold test that drops a reading sitting
exactly on 80 dBA, sampled time that only counts readings loud enough to add
dose, partial surveys projected to eight hours instead of the worker's own
shift, a TWA truncated rather than rounded, a group figure made by averaging
decibels, a 140 dBC peak not counted as an impulse.

## What an expert has to judge

- Sampled time versus dose: every minute the dosimeter measured is sampled
  time, including quiet minutes below the threshold that add no dose, while
  minutes the dosimeter did not measure (it logs 0.0 then) are not. Projection
  to the shift divides by sampled time, so getting the denominator wrong moves
  every partial-survey dose.
- A dose of nought is a real measurement (a quiet worker), a survey with no
  reading is no measurement at all. A similar-exposure group averages the
  doses its members actually have: the quiet worker lowers the mean, the
  unworn dosimeter does not take part.
- Energy-based averaging: a group is judged on the mean dose, not the mean of
  decibel TWAs.

## Work surface and deliverable

A ~200-line Python package (`noisedose`) plus a fixed driver that prints a JSON
survey report (per worker: dose, TWA, status, ceiling, impulse; per group: dose,
TWA, status). The authority is one numbered in-environment manual
(`/app/docs/noise-survey-manual.md`). The candidate repairs the package so the
report follows the manual.

## Why difficulty survives removing incidental schema

The two places where the repair has to stop are both inside aggregates that a
departure forces the solver to rebuild (sampled time; the group mean), and
both are decided by definitions two hops away (a reading is a run at 40.0 dBA
or more; a survey without a reading has no shift dose). The JSON shape is
incidental: the same judgement is needed in any report format.

## Native artifact

A per-shift dosimeter run log (`[minutes, level]` runs as exported by a
dosimeter's time history) and a peak-hold list, which is how real dosimeter
exports look once reduced to runs.

## Two disjoint natural-but-wrong repairs

1. Fix "sampled time counts sub-threshold readings" by moving the sampled-time
   sum ahead of the threshold test, so runs logged at 0.0 become sampled time
   and shrink every projected dose.
2. Fix "the group figure averages decibels" by averaging every member's
   reported dose, so a member whose dosimeter logged nothing enters the mean
   as 0.0; or keep the old `twa is not None` filter, which also throws out the
   quiet members whose 0.0 dose is real.

## Addendum after contract_review r1 (redesign)

The group-exclusion trap is dropped (F1): every survey now has a shift dose. The
second place the repair has to stop is the projection rule's own domain. The
programme projects only a full-shift survey (sampled time at least three
quarters of the shift) to the worker's shift, and gives no rule for a shorter
survey, whose figure keeps the package's existing step. The natural repair
applies the new projection to every survey.
