# tbrain-local-magnitude-network-reduction (stopped 2026-09-27): reference only, do not submit

This is platform task `12e6eda4-8ced-4dcd-928d-7abc22b133a9`, the same slot that held gnu-sed before it was retired.

The task asks the agent to repair a seismic network's local-magnitude (ML) package so that it follows the network's manual, NPM-4. It has eight departures from the manual:

- magnification 2080;
- halving the peak-to-peak amplitude;
- hypocentral distance;
- linear interpolation of the distance correction;
- the station correction sign;
- the station mean;
- the network median;
- the three-station minimum.

It also has three traps:

- keeping the shipped off-table correction;
- the three-times-noise reading filter;
- pooling a site whose two sensors report separately.

## What is here

- `tbrain-local-magnitude-network-reduction.zip` holds the last uploaded bytes (rev9, sha1 `1961ee90…`). They are identical to `workspace/revision/12e6eda4-…/revisions/tbrain-local-magnitude-network-reduction-rev9.zip`.
- `SUBMISSION-…md` is the submission note and rubric for rev9.
- `../tbrain-local-magnitude-network-reduction/` is the task tree for rev9, the snapshot the platform measured.

## History

| Upload | Blocking stage | Result |
|---|---|---|
| v9 (first upload) | quality panel | 4 findings: 2 Sound Verifier, 2 Correct Reference (2 Major) |
| v10 (rev8) | quality panel | 2 findings, both Sound Verifier (1 Major, 1 Minor); the other four axes were clean |
| rev9 | difficulty | Quality panel passed. The difficulty run measured `base`, so the evaluation FAILED; `solvable` was True (4 Opus runs and 4 GPT-5.6 runs) |

## Why it was stopped

At `base`, fewer than 3 of the 8 runs failed. The task is not grandfathered: its first evaluation was 2026-09-24. Under the grading flow, BASE means stop, not harden.

The local signal pointed the same way:

| Probe | Result | Failures |
|---|---|---|
| Skeleton pair | 1/2 passed | the single miss was the off-table trap |
| rev8 re-probe | 2/2 passed | Opus 5 kept the off-table calculation both times |

The other two traps were never missed locally:

- The reading filter is a direct reading of rule 2.3.
- Pooling a two-sensor site follows from "station magnitude" plus the report layout.

The difficulty therefore rested on one trap. Opus 5 now reads the silence clause ("keep the present calculation") correctly.

## Lessons

- **One trap is not enough.** If the local signal comes from a single trap and the other traps are never missed, the platform result will be BASE. Before uploading, require at least two independent traps that some local runs miss.
- **Treat a spec-conformance repair as easy for frontier models.** When the manual states every rule explicitly and the code departs from it in named places, the model fixes each departure. Rules stated positively carry no difficulty; only a silence or restraint trap does.
- **Do not upload after a 2/2 re-probe.** A 2/2 after any repair round is a stop signal. It is not sampling noise: rev8 was uploaded after a 2/2 and came back BASE.
- **Two verifier techniques are worth reusing:**
  - A section-1 margin that keeps float and exact arithmetic in agreement at every threshold (v9 findings 2 and 3).
  - An accept/reject tolerance band instead of a single 1e-6 edge (v9 finding 4, v10 finding 2).
- **A panel return that lists a clean axis stays clean.** Correct Reference never came back after v9.

## Reusable parts

- `solution/model.py` is an independent ML model. `revision-v9/golden_precision_check.py` does a 50-digit decimal recomputation of every sealed value.
- `solution/seal.py` `numeric_discipline()` checks the section-1 margins in exact decimals.
- The sweep catalogs (`revision-v9/`, `revision-v10/sweep-catalog.json`) include C16 interaction mutants and a pair for the tolerance band.

All evidence is in `workspace/reports/tbrain-local-magnitude-network-reduction/`:

- `revision-v9/` and `revision-v10/`;
- `revision-ledger.json`;
- `quality-panel/`.

The probes are in `workspace/local-solve-probes/tbrain-local-magnitude-network-reduction-*`. The platform returns are in `workspace/revision/12e6eda4-8ced-4dcd-928d-7abc22b133a9/`.
