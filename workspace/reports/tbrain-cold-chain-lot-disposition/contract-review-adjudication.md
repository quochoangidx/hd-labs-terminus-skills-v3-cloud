# Contract review r1: builder adjudication (redesign 1/1)

Snapshot reviewed: fbc01d5d... Redesigned snapshot: 343eed152d91b3272a684f7ad6b1f22e5ebbb3cc6a2e67be5260d41b5b90b422.
The orchestrator ruled REDESIGN 1/1 (svr 2). The rows below are the builder's positions, one per finding. Orchestrator rulings are still to come.

| Finding | Builder | Evidence / action |
|---|---|---|
| F1 MKT 0/0 when no minute is attributed | **accept** | Reproduced: a two-reading, 45-minute export has zero weight under r1. Closed by range, not made a trap. SOP 1.4 now requires every export to hold at least one pair of stamps no more than 30 minutes apart, so every leg has a positive hold under 2.7 alone. `model.limit_breaches` checks this; the fuzz receipt shows 0 breaches. |
| F2 out-of-span reading, silence vs 2.6/3.2 | **accept** | The reviewer is right that the chain 2.6 -> 3.2 governs this case ("charged to no band"), so the old T2 was a contract conflict, not a trap. Removed: 1.4 now says "every reading of a job lies within the table's span", and 2.6 no longer mentions the span. The obligation is recorded in `removed_obligations` (OFF_TABLE_KEPT). |
| F3 silence clause has no target | **accept** | Redesigned so the clause has two verifiable targets. Both are figures the SOP names for every input but values only on a defined subdomain (below). The instruction's silence sentence is now value-level: "Where the SOP names a figure but gives it no value for some input ...". It names no case. |
| F4 README vs SOP decimal places | **accept** | SOP 1.1 now reads "given to at most one decimal place", matching the README. |
| F5 gap opener's MKT weight inferred | **partial** | The reviewer's chain (gap opener weight 0) followed from old 3.1, which attributed interval minutes and summed them into band time and weights. That rule is gone. 2.7 now gives every reading a hold, 3.1 and 5.1 consume the hold, and the gap opener's hold is deliberately unvalued. It is covered by the silence sentence, not by a reminder that would govern it. |
| Trap reading T1 (gap minutes) as a plain defect | **accept** | Correct under r1's wording. Replaced by TA (hold of a gap opener). The value is verifiably missing: 2.7 partitions readings into logged-interval openers, the last reading and the rest, and values only the first two. |
| Trap reading T2 as governed | **accept** | See F2; removed. |
| Trap reading T3 as a rule sentence (counts 0) | **accept** | Handover exclusion stays governed by 2.3. It is kept as a wrong path (G_flattened_weights) but no longer counted as a trap. |
| svr 2 / predicted collapse | **accept** | Redesigned the core (below); builder self-score is now 3 (solver-path-screen.json). |

## What changed

Departures (8, was 9):
- D1 changed: the last reading of an export holds nought (2.7). Shipped gives it one 60-minute window. This replaces "closing-reading attribution".
- D5 (273 K) dropped: shipped now uses 273.15, because its witness needed rounding-edge fixtures.
- D2, D4, D6, D7 and D8 are unchanged.
- D3 changed: 4.1 now carries band time for a chained lot (2.9).
- D9 changed: the logger-gap threshold is 30 (2.4, 3.2). Shipped used the shared 60-minute window constant for it.

Traps (2, each on a different node, kind and file):
- **TA: the hold of a reading that opens a logger gap** (attribution.py). The SOP is silent here because 2.7 gives every reading a hold, values only logged-interval openers and the last reading, and 3.1 and 5.1 consume the hold. Today's step is `min(span, LOGGER_WINDOW_MINUTES)` with the window at 60.
  - The natural over-repairs are: edit the shared window to 30 while fixing the gap threshold, hold the whole gap, or hold nought.
- **TB: the band time of a lot that is not chained** (disposition.py). 4.1 values band time only for a chained lot. 2.9 defines "chained" as no handover over 2,880 minutes, and 1.4 admits handovers up to 10,080. 4.2 and 6.1 consume the figure for every lot. The r1 sentence "the allowance belongs to the lot, not to a leg" was deleted. Today's step takes the largest leg figure.
  - The natural over-repair is to sum every lot's legs.

Reader test applied to each trap: "Does any SOP sentence, followed through definitions, decide this value differently from the shipped code?" No, for both. The chains are recorded in trap-screen.json.

## Receipts (snapshot 343eed15...)

- receipts/panel-precheck-design-only.json: pass
- receipts/instruction-preflight.txt: OK
- receipts/model-vs-oracle-fuzz.json: 600 jobs, 2,500 lots, all agree, 614 unchained lots, 1,536 lots with gaps, 0 limit breaches
- receipts/departure-trap-checks.json: pass. Every departure differs, unpatched and reverted. The unpatched package matches the model on TA and TB. Each over-repair differs from the model. The trap-free sweep agrees.
- receipts/canonical-image-smoke.txt: Oracle equals the model in the image
- trap-screen.json
- solver-path-screen.json

# Contract review r2: builder adjudication

Snapshot after r2 repair: 23db7d6ea56902953ed0b37913b9aef2fd6356f98d0bce654f980aed21c91480. r2 closed r1 F1–F5 and scored svr 3 ("resists, weakly").

| Finding | Orchestrator | Builder | Action |
|---|---|---|---|
| N1 shared 60-minute constant makes the kept gap-opener hold ambiguous (60 / 30 / 0) | uphold | **accept** | Shipped `attribution.py` now has two constants. `HOLD_CAP_MINUTES = 60` is used only by `holds()` ("the longest stretch one logger reading is credited with"). `GAP_MINUTES = 60` is used only by `unlogged_minutes()`. The gap departure is fixed by setting `GAP_MINUTES = 30`. The kept value is `min(span, HOLD_CAP_MINUTES)`, i.e. `min(gap, 60)`, which is uniquely what today's step does. The 1.4 closure now reads "with at least one logged interval (2.4)", replacing the bare 30-minute-pair clause that hinted a gap opener holds nought. No sentence names the gap-opener case. |
| N2 chained-lot bound vs "allowance belongs to the lot" instinct | narrow | **accept** | No cue added; 4.1 unchanged. The silence sentence governs. |
| N3 kept hold feeds band time as well as MKT | acknowledged | **accept** | The model and Oracle apply the kept hold in both 3.1 and 5.1 (TA mutants differ on band_hours, remaining_hours and mkt_c). No text change. |
| N4 handover minutes never counted | acknowledged | **accept** | No change. |

Wrong path "shared window set to 30" became **TA_hold_cap_set_to_30**. It is still killed by the TA job and by the TA skeleton family only.

Receipts refreshed on 23db7d6e: model-vs-oracle-fuzz (600 jobs / 2,500 lots agree, 0 limit breaches), departure-trap-checks (pass), panel-precheck-design-only (pass), instruction-preflight (OK).

New skeleton scorer: authoring/score_skeleton.py, 12 seeded families, run in image tbrain-cold-chain-lot-disposition:skeleton.
- The Oracle passes all 12 families (receipts/score-skeleton-oracle.json).
- The unpatched package fails all 12 (receipts/score-skeleton-unpatched.json).
- Each trap over-repair fails only its own trap family (receipts/score-skeleton-trap-mutants.json). The one exception is the governed G_flattened_weights path, which also fails TB, because TB lots have long handovers.

# Strengthening 1/1 (after skeleton cycle-1 2/2)

Snapshot: b2fbee1a4c13c8faed748b636ed119880a1fe78e98de37e0e9bd9ebf11afde3a. Image tbrain-cold-chain-lot-disposition:skeleton2 (sha256:3387fd0f1c0e7afffb5a8ee077db84f934a6347a2e1db009d8b9444527765f97).

Cause of 2/2: the old silence sentence ("where the SOP names a figure but gives it no value") read as a checklist. Both solvers enumerated the partitions of 2.7 and 4.1 and kept TA and TB by name.

What changed (the causal core is unchanged: holds -> band time / MKT -> disposition, plus certificate -> remaining allowance):
- **Silence clause.** No silent target remains. P2 now reads "Leave alone whatever the SOP does not govern: the rest of the package's behaviour stays as it is ...", followed by the unchanged tier 3.
- **TA dropped** (gap-opener hold kept at min(span, 60)). A gap opener's hold is now governed: nought (2.7). The shipped band time charges it the whole spacing, so this is now departure D5.
- **TB dropped** (unchained lot keeps max). The "chained lot" concept is removed, and 4.1 sums over every leg again (D3). Handovers are back to 0–2,880.
- **D6 dropped** (unweighted MKT). The shipped MKT already weights each reading by holds(), which gives the minutes to the next reading. That is the SOP 5.1 weight for every reading but the last.
- **D1 changed.** The last reading holds nought, which affects both the hold and the MKT weight.
- **Certificate format.** It now lists entries (`certificate`: band -> list of minutes). The shipped package still ignores it (D4).
- **New TX (apply-everywhere edge, already-correct code).** 2.7 defines "hold" (logged-interval length; gap opener and last reading nought), and 3.1 charges it to bands. 5.1 defines its weight in its own words: the minutes to the next reading, gaps included. The shipped holds() is the MKT weight and is named after the band term. The natural fix for D5 writes 2.7 into holds(), which silently breaks the MKT the solver never opened. Both cycle-1 solvers fed holds() straight into the MKT weights.
- **New TY (definition hop in a newly written aggregate).** 4.2 subtracts "prior time". 2.9 defines prior time as the total of "excursion entries", and 2.6 defines those as entries of 15 minutes or more (shorter ones record transients). The natural new sum takes every entry.

Departures (8): D1 last reading, D2 band ends, D3 carry sum, D4 prior time, D5 gap-opener band time, D7 unrounded compare, D8 hours rounding, D9 30-minute gap threshold.

Receipts (b2fbee1a):
- panel-precheck-design-only: pass.
- instruction-preflight: OK.
- model-vs-oracle-fuzz: 600 jobs, 2,500 lots agree; 1,559 lots with gaps, 971 with transients, 0 breaches.
- departure-trap-checks: pass. Every departure differs unpatched and when reverted; the unpatched holds() equals the 5.1 weights; the TX, TY and G over-repairs differ and agree on the trap-free sweep.
- score-skeleton2-oracle: 12/12 pass.
- score-skeleton2-unpatched: all 12 families fail.
- score-skeleton2-mutants: each trap over-repair fails only its own family.
- trap-screen: TX 0 hard / 1 soft, TY 0 hard / 0 soft.
- solver-path-screen: svr 3.
