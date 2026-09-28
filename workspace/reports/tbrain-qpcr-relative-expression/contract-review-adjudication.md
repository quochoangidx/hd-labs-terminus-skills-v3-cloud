
## Round 1: builder adjudication (redesign 1/1, after contract_review r1 svr 2 and the discarded skeleton cycle-1)

| # | Finding | Builder | Action |
|---|---|---|---|
| F1 | The 2-point factor has three readings (R1/R2/R3) | accept | The silent region is removed. SOP 2.5 now fits the standard curve through two or more curve points, and 3.1 gives factor 2 below two points, with no ceiling anywhere. The factor is governed for every gene, so the cap for 2-point curves (old trap TB) is dropped. |
| F2 | The all-outlier mean has three readings (21.0 / 40.0 / null) | accept | The SOP 4.1 median of an even count is now the lower of the middle two, so the median is always a replicate and never an outlier. The kept set can no longer be empty. The shipped 40.0 substitution stays a departure only for not-detected genes (4.3). Old trap TA is dropped. |
| F3 | "Values the SOP does settle" has no stated level | accept | Within section 1 every reported value is now governed. The silence sentence is value-level and unique: "the one the present package computes for it when its present code is run on the values the SOP settles". The manifest names no silent case. |
| F4 | Early NTC Ct and the 10.00 floor | accept (as intended) | 2.6 stays as it is: every NTC Ct at or below the cut-off contaminates, early ones included. This is now trap T2, where the shipped code is correct. |
| F5 | "sample" not defined | challenge | 6.2 and the README (`sample` on unknown wells) define it; 1.3 guarantees wells. No change. |
| F6 | Genes that are not on the plate map | challenge | Covered by "files that do not follow README" (tier 3). No change. |

Skeleton cycle-1 (0/2 raw) is discarded as ambiguity evidence (F2). Both solvers found TA and TB in one pass and kept legacy behaviour.

Redesign principle: no graded silent region. Both new traps are governed, uniquely derivable from the SOP, and sit where the shipped code is already correct. That keeps them off a list of places where the code breaks the SOP (which is what the reviewer produces) and off a search for places where the SOP stops short. The natural repair of a departure goes through a shared helper and breaks the correct site:
- T1: the shared `replicates.mean_ct` gives curve-point Ct (2.4: the plain mean of every determined standard well). Putting the 2.2 window or the 4.1 outliers into it changes the standard curve.
- T2: the shared `plate.called` (determined, at or below 35.00) gives NTC contamination (2.6). Putting the 2.2 10.00 floor into it clears an early NTC.
