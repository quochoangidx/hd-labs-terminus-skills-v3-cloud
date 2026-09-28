# Domain-crux card (pattern-blind, written before the pattern catalog)

Slug: tbrain-cell-line-passage-doubling. Written 2026-09-26 by the builder before any trap design.

Who does this work: the cell-culture or cell-bank scientist (core facility, biologics QC)
who keeps the passage log of a line and signs off that cultures and banks are inside the
line's approved population-doubling window.

Real failure modes of a passage-log / PDL calculation (what goes wrong in practice):

1. Doublings from total instead of viable counts. PD = log2(N_harvest / N_seed) is meant
   on live cells; a trypan-blue count carries a viability.
2. The seed's viability belongs to the suspension the seed was drawn from (the parent's
   harvest, or the thawed vial), not to the culture's own harvest. Multiplying the seed by
   the culture's own harvest viability cancels the correction and looks right.
3. Cumulative PDL follows the lineage (parent chain), not the calendar. Summing every
   culture of a line in date order double-counts sister flasks and interleaved lineages.
4. A thawed vial carries the PDL and passage at which it was frozen, not the line's seed
   PDL and not the line's latest PDL.
5. Passage-number conventions differ between labs (does a thaw count as a passage?).
6. A culture that lost cells (harvest below seed) gives negative doublings; practice
   differs between clamping at nought and counting it. Cells do not get younger: a crash
   lowers the PDL figure but the line's in-vitro age should not drop.
7. Low-viability counts (a failed thaw or a crashed harvest) are unreliable; many SOPs
   refuse the viable count below a viability threshold.
8. Bank inventory: vials thawed must come off the bank they were frozen into; the bank's
   PDL is set by the vials actually left.
9. Senescence / limit flags judged against the approved maximum PDL with a warning band.

Crux (what an expert has to get right): which suspension each number belongs to, and
where the facility's rules stop, so that a repair of the viable-count and lineage
arithmetic does not also rewrite values the SOP deliberately leaves to existing practice.

Native artifact: a passage log (thaws, cultures, freezes) and the lineage report the
facility files: per culture passage, doublings, PDL and limit flag; per bank vials left and
bank PDL.
