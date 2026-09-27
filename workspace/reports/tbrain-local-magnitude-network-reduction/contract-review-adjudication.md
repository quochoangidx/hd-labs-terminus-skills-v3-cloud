# contract_review adjudication: tbrain-local-magnitude-network-reduction

Reviewer turn: `contract-review.json` (overall `accept_with_fixes`, SVR 3, prediction `collapses`).
Builder dispositions below; orchestrator rulings as relayed. Repair diff (instruction.md + environment/):
`authoring/cr-repair.diff`.

| Finding | Severity | Builder | Evidence | Action | Orchestrator |
|---|---|---|---|---|---|
| CR-1 decimal 3x ties disagree in float | should_fix | accept | `0.3 >= 3*0.1` False while decimal truth is a reading; `1.5 >= 3*0.5` exact | Verifier-side rule, no contract change: tie cases only binary-exact (1.5/0.5, 300/100); every other amplitude kept away from 3x by construction (jobgen draws sub-noise ratios in [1.05, 2.9], readings at >= 4x). `jobgen.family("readings")` now carries both exact ties | uphold |
| CR-2 off-table silence rests on the scope word "Between" | should_fix | accept | reviewer's reading that 3.3's "the network does not [interpolate on log distance]" could be read as a blanket ban | NPM-4 3.2 now says "The table runs from 10 km to 600 km, and this part gives no correction for a distance outside it." A definition, not disclosure of the kept step; manifest anchor for OFF_TABLE_KEPT moved to it | uphold |
| CR-3 only one restraint trap | should_fix (blocking per orchestrator) | accept | T1 (2.3) reads as a stated departure; every departure is differential-testable | T1 demoted to departure D9 (still isolated). New trap T3 STATION_GROUPING: NPM-4 1.2 now defines a recording as one sensor's share of an event at a station, and a site with separately processed broadband and strong-motion sensors sends two recordings of one station. 4.3 (mean of *its* readings) and 5.2/5.3 (contributing *stations*) then require pooling the readings per station and one vote in the median and the three-count; the shipped per-recording loop and a per-recording reference both get it wrong quietly. Recordings now carry one or two amplitudes (one sensor's horizontals); sample updated (CLDW single sensor). Instruction envelope names the input family "sites whose broadband and strong-motion sensors arrive as separate recordings". §4.3 screen: 0 flags (mined-candidate.json `T3_STATION_GROUPING`). Isolated: only `jobgen` family `shared_station` repeats a station (`trap_inputs()` asserts it) | uphold |
| CR-4 precedence phrase hard to parse | polish | accept | the rest of the paragraph never conflicts with keeping the calculation | Reworded to "For such a value, keep the present calculation; every other step it passes through still follows NPM-4." Composition meaning kept | uphold |
| CR-5 boundary built from non-Pythagorean pairs | polish | accept | hypot vs sqrt(x*x+y*y) can differ by an ulp | Verifier rule: table-end witnesses only at depth 0 (epi 10, 600) or exact pairs (8, 6); every other distance >= 1e-3 from 10 and 600 (`jobgen.EDGE_GAP`) | uphold |
| CR-6 shipped crash at epi 0 | polish | accept (note) | log10(0) in the shipped code for epicentral 0 | No change: after 3.1 the distance is >= 1 km (1.2 guarantee); distances below 1 km are outside section 1 and tier-3/open; a crash is never graded as preserved behaviour | uphold (note) |

## Witness cross-check

Reviewer witnesses W1–W8 recomputed with `solution/model.py` after the repair: W1/W2 change only
through CLDW's sample edit (CLDW now one sensor); W3–W8 unchanged (no repeated station, no
contract change on those paths). The model and the Oracle agree on all 560 fuzzed bulletins
(`authoring/fuzz-model-vs-oracle.json`, max |diff| 1.1e-13).

## contract_review recheck (`contract-review-recheck.json`, overall `accept`, nothing reopened)

| Finding | Severity | Builder | Evidence | Action |
|---|---|---|---|---|
| RC-1 "share one" awkward in 1.2 | polish | accept | wording only | Applied by the orchestrator before the skeleton probe ("have the same channel"); instruction_preflight and design-only precheck rerun on snapshot 096f2e09… (pass) |
| RC-2 T3 witness shapes | polish | partial | (a) unequal readings per recording, (b) two stations / three recordings -> null, (c) median shifted by a double vote are all in `tests/expected/shared_station.jsonl` (fixtures `shared-null` = RW1, `shared-median` = RW2, `shared-two`, plus generated 1+2 splits); sweep mutant c11-mean-of-recording-means and wrong paths t3-recording-is-a-station / t3-median-over-recordings are each rejected on that test alone | Declined only the "two-sensor station outside the table" cross: it would put T2 inputs into the T3 test, which the isolation rule (blueprint §4.2 rule 3; execution-profiles step 7) forbids, so a single over-repair would cost two tests |

## final_review (`final-review.json`, overall `accept`)

| Finding | Severity | Builder | Action | Orchestrator |
|---|---|---|---|---|
| FR-1 `.DS_Store` at the task root | should_fix | accept | Removed from the whole task tree before every gate; packaging (`preflight.sh --emit-zip`, task-zip-submit) strips it too; the snapshot hasher already skips it | uphold |
| FR-2 verification_explanation overclaims isolation of reverted departures | should_fix | accept | Last sentence rewritten: reverted departures fail their own test and the magnitude-wide ones fail most files; only the natural over-repairs (linear or clamped extrapolation, averaging every amplitude, per-recording magnitudes, median over recordings, mean of recording means) fail only their own test; "lower middle value" dropped from that list | uphold |
| FR-3 one-station table floor never reached | polish | accept | `fixtures.one_station()` (a one-station table, one event, one recording, null network ml) added to `fewer_than_three.jsonl`, sealed from model.py; tests/ now 145,502 bytes, under the 150 KB panel budget | uphold |
| FR-4 `-S` is an unstated constraint | polish | challenge | Image is stdlib-only, agent has no network, verification_explanation already says `python3 -I -S`; no change | overrule (no change) |
