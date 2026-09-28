# Contract review r1: builder adjudication and redesign (2026-09-26)

Reviewed snapshot: the Phase 1 snapshot (design-only precheck receipt 0f90d2b5...).
Redesigned snapshot: d706c4c37b2b89c254e1ae3632dce4c13867039c9ebdda17344339d15ad0a80d (receipts/panel-precheck-design-only.json).
This is the one redesign step 3 allows.

| Finding | Builder | Disposition |
|---|---|---|
| F1 group membership of a member with no shift dose; the README 0.0 invites "count as zero" | accept | Removed the no-shift-dose state entirely, so the competing reading has nothing to attach to. 3.3's "a survey without a reading has no shift dose", 4.1's "a worker with no shift dose has no TWA" and 1.3's "mean of no figures is nought" are deleted, and the README row dose is simply the shift dose. Every member now has a shift dose, governed or today's, so 6.1 "mean of its members' shift doses" has a single reading. Nothing was disclosed in 6.1. The group trap T2 goes with it. The governed quiet-member case stays as departure D9b, whose natural wrong path is keeping the has-a-TWA filter. |
| F2 0.0 runs out of the rebuilt sampled time | accept (kept as trap T1) | Fixture moved to full-shift surveys with no below-threshold or at-threshold reading, so T1 is isolated from D2, D3 and the new trap T3. |
| F3 half-up on binary floats | accept | Chosen: unreachable. 4.1 yields a TWA exactly on a .x5 half only by float coincidence, since every half needs an irrational dose. Every graded fixture must sit at least 1e-6 of a tenth away from a half, using `model.near_rounding_edge` as the enforced predicate. No fuzz draw hit one (0 of 2,600 surveys skipped). Halves are therefore not graded either way; the manual sentence stays as the convention. |
| F4 preservation clause without a real silent case | accept | Real silent cases now exist. 3.3 is stated only for full-shift surveys (2.5: sampled time of at least three quarters of the shift), so any other survey's shift dose has no rule and keeps today's step. The silence clause states this as a rule plus boundary categories. Two named cases, each with a planned witness in `closure.silence.named_cases`: "a survey that sampled too little of its shift for the manual's rules on the shift dose to cover it" and "one whose dosimeter measured nothing at all". |
| F5 ceiling `>` vs impulse `>=` asymmetry | accept as a governed witness | Not counted as a trap; the witness stays: `[[1, 115.0]]` must not raise the ceiling flag. |
| Screen svr 2 / collapses ~0.7 | accept | Redesigned below. The re-score is in solver-path-screen.json. |

## Redesign

- **Dropped: T2** (group exclusion). It hopped through the same word as T1, and 1.3 disarmed it.
- **Added: T3, an "apply the formula everywhere" edge inside a function the solver has to edit.**
  - Departure D4 (projection to 480 minutes instead of the worker's shift) lives in `shift.py`.
  - The manual now bounds the repaired rule: 3.3 covers full-shift surveys only.
  - Below three quarters of the shift, the shipped step must stay: nought when nothing was sampled, otherwise scaled to 480 minutes when fewer than 480 minutes were sampled.
  - Two natural over-repairs, each rejected by the model: the own-shift projection applied to every survey (Opus's formula-everywhere edge), and an unprojected measured dose for the uncovered survey.
  - Keeping the shipped step means adding a branch in the rebuilt function.
- **Portfolio is now mixed:**
  - T1 is a definition hop on a bare value (the 2.2 floor) in `runs.py` over the `log` list.
  - T3 is a bounded-rule silent edge (2.5/3.3 plus the silence clause) in `shift.py` over the survey as a whole.
  - Different files, subtypes and instruction sentences. The T1 fixture is full-shift and the T3 fixture has no 0.0 runs.
- **Code split:** `exposure.py` became `runs.py` (sampled time and measured dose) and `shift.py` (projection). Shipped behaviour is unchanged.
- **No unrelated surface added.** New governed boundary: exactly three quarters counts as full-shift (witness D10).

# Contract review r2: dispositions (2026-09-26)

Reviewed snapshot: d706c4c3.... New snapshot: 74ce040a8268b465c45d151b2cf834d8db6aafccf3194a006d6d8dca20d7a05e.

| Finding | Builder | Orchestrator | Disposition |
|---|---|---|---|
| F1: which sampled time goes into the kept step for a survey that is not full-shift | accept | uphold | Closed at the value level with one clause in the composition sentence: "keeping that step comes first, and every figure it works from and every other step the figure passes through still follow the manual". The kept step now works from the manual's sampled time and measured dose, which is the model's reading (A). The reviewer's counterexample (shift 480, `[[120,88.0],[120,70.0]]`) gives 100 / 85.0 / action. The trap is not named. |
| F2: the kept step keeps 480 as both comparison and target | none (confirmation) | - | This is trap T3 as designed. The discontinuity at three quarters is intended. |
| F3: long-shift symptom pulls toward own-shift projection | accept | - | Narrowed to "people on ten- and twelve-hour shifts whose dosimeters ran most of the day". This is still true of full-shift surveys on long shifts and no longer covers the uncovered ones. |
| F4: half-up on floats | accept (unchanged) | - | Halves stay unreachable and are not graded. The generator and scorer skip any survey within 1e-6 of a tenth of a half; none has been hit so far. |
| F5: ceiling vs impulse comparison | none | - | Governed witness only. |

Reruns on the new snapshot: instruction_preflight rc=0 (516 words, 2 advisories), design-only precheck pass, fuzz pass on both seeds, departure-trap-checks pass, canonical smoke (Oracle output = model output, shipped differs). The skeleton scorer (authoring/score_skeleton.py) is validated in receipts/score-skeleton-validation.json.

# Skeleton cycle-1 (2/2 on claude-opus-5): the one allowed strengthening (2026-09-26)

Diagnosis (orchestrator, from the solvers' reports): T1 was a one-hop read of the salient 40.0 floor, and T3 was effectively named by the silence clause. New snapshot: 0be030db0040f36637d9acbd0aedd236084ef563373080da575861c40170b429.

- **Silence.** The instruction now carries only a value-level sentence: "Where the manual gives no rule for a figure that one of the package's steps works out, keep the figure that step works out today, from the figures the manual does define; every other step still follows the manual." No case is enumerated. The envelope no longer mentions three quarters. `closure.silence.named_cases` anchors the two bounded definitions in the manual, with witnesses.
- **T3 kept, with its bound moved out of the rule sentence.** 3.3 now speaks of "a partial survey". 2.5 defines that as at least three quarters of the shift and shorter than it. Below three quarters the shift dose has no rule, and today's 480 step stands.
- **T4 new, formula-everywhere kind.** 3.1 gives the reference duration "at a level L". 3.2 sums it "at the level it is counted at". 2.3 counts a reading at its own level only when it is "logged no higher than the ceiling level", and 5.1 defines that level as 115.0 dBA. Today's loop in runs.py counts a run at min(level, CEILING_DBA) before the threshold test; the D2/D3/D1 repairs force that loop to be rebuilt. The natural rewrite, using the logged level in 3.1, differs from the model.
- **T1 demoted.** It stays a governed family, not a counted trap.
- **Rerun receipts, all pass:** instruction_preflight (rc=0, 464 words), design-only precheck, fuzz on both seeds, departure-trap-checks, canonical smoke, score-skeleton-validation (T4 family added; each natural over-repair fails exactly its own family).
- **Risk.** T3 and T4 are both silent keeps, so one careful reading policy covers both. Each carries 1 soft 0/8 flag (contrary instinct, moderate). Self-score: svr 3.

# Contract review r3: dispositions (snapshot 0be030db..., after skeleton cycle-2 1/2)

| Finding | Builder | Orchestrator | Disposition |
|---|---|---|---|
| F1: "Add no exception, clamp or guard" sits beside the kept `min()` | acknowledge (fair as written) | no change | No edit. The verb is "add", and the value-level sentence keeps today's figure. Editing instruction.md now would stale the cycle-2 pair. The T4 test witnesses the kept clamp. |
| F2: kept legacy branch below 3/4 (trap T3) | none (confirmation) | - | Trap as designed. The r3 counterexamples go into the T3 and silent-case tests. |
| F3: "partial survey" means different things in the shift.py docstring and in 2.5 | acknowledge | no change (freeze) | The manual governs and the docstring is not an authority. environment/ is frozen. |
| F4: half-up on floats | unchanged | - | Halves stay unreachable. The sealing code asserts every graded job sits more than 1e-6 of a tenth from a half. |

Freeze from here on: instruction.md, environment/ and the shipped package stay byte-identical (orchestrator, cycle-2).

# final_review: dispositions (2026-09-27; snapshot 0467276c... -> 187a1af2...)

| Finding | Builder | Orchestrator | Disposition |
|---|---|---|---|
| F1: the kept short-survey step's sampled time was never discriminated | accept | uphold | Two workers were appended to `below_three_quarters`, named after every other survey so no earlier expectation moved. One is the reviewer's worker (shift 480, `[[120,88.0],[120,70.0]]` → 100.0 / 85.0 / action); the other mixes a 0.0 run with readings. The family now declares the paused input too, and the isolation predicate is unchanged otherwise. The counted-minutes mutant W18 (wrong path) and c11-kept-step-counted-minutes (sweep) each fail only test_survey_below_three_quarters_keeps_todays_projection. |
| F2: "ceiling makes over" is not separable within the limits | acknowledge | no action | Inherent: a reading above 115 dBA already makes the TWA at least 88.3. The impulse → over path is witnessed. |
| F3: exact key set not promised | accept | uphold | The README lists what each object holds, not that it holds nothing else. The comparison now requires every listed key and ignores further ones; alt-extra-report-keys scores 1 in the sweep. |
| F4: differential pair names constant per kind | acknowledge | no action | The candidate cannot see the pairs, and the sealed families already cover them. |

Explanations are updated to the new counts (37 surveys, 434 workers, 20 wrong paths, 29 mutants, 4 alternatives), and "per kept step" is reworded.
