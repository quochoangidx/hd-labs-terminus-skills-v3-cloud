# Domain-crux card (pattern-blind; written before the design was fixed)

Slug: tbrain-crop-hail-loss-adjustment
Date: 2026-09-28, builder H, task-batch 9 (builder_certified, CORE+ bar)

## Domain-native failure mode

A crop-hail insurer's claims office turns adjusters' field inspection sheets
into claim payments under its own numbered loss-adjustment procedure. For each
insured field of corn the adjuster counts sample plots (a length of row: plants
standing before the storm, plants dead or broken below the ear, leaf area the
survivors lost), records the growth stage on the storm day and any replanting.
The office averages the plots into a field stand loss and defoliation, turns
defoliation into yield loss through a stage chart, combines the two, applies the
policy's minimum loss and deductible option (straight or disappearing), prices
the payable loss against the field's liability, adds a replant payment, and pays
the claim only above a minimum. The package was written from the shape of the
inspection export, and carries slips a claims examiner meets in real adjustment
tools: plot averages taken over the plots that showed damage only, leaf loss
added on top of stand loss instead of on the surviving stand, an old chart
factor, a disappearing deductible that pays more than the loss, indemnities cut
off at the cent instead of rounded, and old policy figures (minimum loss,
straight deductible, minimum claim) from an earlier edition.

## What an expert has to judge

- Plot averaging: every plot laid across the field counts, not only the damaged
  ones; stand loss and defoliation are two separate averages.
- Leaf loss falls on the surviving stand only (no double count), and the stage
  chart decides how much of defoliation becomes yield loss.
- Deductible arithmetic: straight vs disappearing; the disappearing deductible
  never pays more than the loss.
- The procedure's stand-loss rule speaks of a plot the hail visibly thinned; the
  sheet also carries plots in lightly hit strips where a plant or two was lost to
  cutworms, planter skips or wind. The procedure counts every plot in the
  average but does not say what such a plot's stand figure is.
- The replant payment is written for a replanted field (a real replanting);
  growers also replant a washed-out corner or a drowned low spot, which the
  procedure lines up on the field's payment but does not price.
- A policy figure (minimum loss, minimum claim) changes by procedure edition;
  the claims package keeps its figures in one place that several steps read,
  and a figure the procedure sets for one step is not thereby set for another.

## Work surface and deliverable

A ~250-line synthetic Python package (`hailadj`) plus a fixed driver that reads
one job file (claims, each with its fields and sample plots) and prints a JSON
claim statement per claim. The authority is one numbered in-environment
procedure. The candidate repairs the package so the statements follow it.

## Why difficulty should survive removing incidental schema

The deliverable is a handful of integers per field and per claim. What stays
hard is how far each repaired rule reaches: which plots the stand-loss rule
speaks of, which replantings the replant rule prices, and which steps of the
package a changed policy figure actually moves. A solver that writes its own
reference from the procedure and fuzzes the package against it only learns what
its own reading of those reaches says.
