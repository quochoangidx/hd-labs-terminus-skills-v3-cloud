# Domain-crux card (pattern-blind, written before reading the pattern catalog)

Slug: tbrain-qpcr-relative-expression. Written 2026-09-27 by the builder before
opening the blueprint / pattern catalog.

Domain: a molecular-biology core lab reduces real-time PCR plate exports to a
per-sample, per-target relative-expression report.

Practitioner's crux (what a core-lab scientist actually gets wrong):

- Efficiency is per assay (per gene, per plate), taken from the standard-curve
  slope: amplification factor A = 10^(-1/slope), efficiency E = A - 1. The
  classic mistake is assuming A = 2 for every gene (plain 2^-ddCt), or reusing
  the target's factor for the reference genes.
- Reference-gene normalisation is a geometric mean of reference *quantities*
  (A_ref^dCt per gene), not an arithmetic mean of reference Ct values raised to
  one factor. The two coincide only when every reference has the same factor.
- Replicate handling: a replicate Ct is averaged across technical replicates
  after outlier rejection; "Undetermined" is not a Ct and must not be averaged
  as 40 or as 0; a well without amplification is a different fact from a well
  failing a spread check.
- NTC (no-template control) amplification below the lab's cut-off means the
  assay is contaminated on that plate; results for that target on that plate
  are not reportable, not merely flagged.
- A standard curve with too few dilution points or poor linearity gives an
  efficiency nobody should trust; the lab's SOP decides which points qualify.
- The calibrator (e.g. untreated control) has fold change 1 by construction,
  and every other fold change is relative to its replicate means.

Native artifact: plate export CSV (well, sample, target, Ct or "Undetermined",
role: unknown / standard with dilution / NTC) + plate map; output JSON report.

Failure mode worth a task: a report that looks plausible (fold changes near
the right order of magnitude) but is silently wrong because of per-gene
efficiency, geometric-mean construction, replicate qualification or NTC
handling. The hard part for an expert is the interaction: which replicates
qualify feeds the mean Ct, which feeds the quantity, which feeds the
normalisation factor and the calibrator ratio.
