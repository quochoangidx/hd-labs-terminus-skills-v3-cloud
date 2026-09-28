# Contract review r2: tbrain-crop-hail-loss-adjustment

Scope: `contract-review-packet-r2/instruction.md` and `environment/` only. The instruction is byte-identical to r1. The changes are in the procedure (1.1, 1.4, 3.1, 4.1, 4.2, 5.3, 6.2) and in two code comments (`plots.py`, `replant.py`).

## Status of r1 findings

**F1 (6.2 vs the replant clamp): closed.**
- New 6.2 says a field whose sheet records replanted acres has "one replant line on its statement; a replant line may be of any amount, nought included".
- The line is now always present as a key, and a 0 amount is explicitly legitimate. 6.2 no longer overrides the clamp.
- The comment in `replant.py` now reads "entered as nought", which removes the "not carrying a line" framing.
- The procedure sets no value for a field that is not a replanted field (below 100 tenths), so the preservation paragraph applies: keep replanted x 300 and zero it below 2500.
- Single values: `replanted: 5` gives 0, `replanted: 8` gives 0, `replanted: 9` gives 2700, and `replanted: 50` gives 15000.
- For replanted fields (100 tenths or more), 6.1 gives replanted x 300, which is at least 30000, so the kept clamp can never bite. There is one value.
- Residual polish: 6.2 still does not say in words that a replanted field's line *is* its 6.1 payment. The only other reading, today's calculation, gives the same number, so this is harmless.

**F2 (stand figure of a plot that is not hail-thinned): closed.**
- New 1.4 drops "cutworms, a planter skip or wind". It now says only "some plots ... show only a plant or two dead or broken; the sheet records every plot the same way", which no longer attributes that loss to something other than hail.
- The comment in `plots.py` is now "A share under the trace figure is entered as nought", in parallel with `replant.py`. That removes the "carrying" argument.
- 3.1 governs only hail-thinned plots. 3.2 requires one figure per plot but sets no value, so the value is kept from today's code: half_up(dead x 1000 / stand), zeroed below 50.
- Single values: `[100,8,0]` gives 80 (a full V6 field has loss 80 and payable 80); `[40,1,0]` gives 0; `[40,3,0]` gives 75.
- A domain reader who wants 0 now has no textual support. The remaining pull comes only from the 2.1 definition, which is legitimate restraint.

**F3 ("as a share of" operator): closed.**
- 3.1, 4.1, 4.2 and 5.3 are now written as explicit "times ... divided by", and 1.1 rounds on "divides ... or takes an average".
- Every rounding site now has one reading:
  - plot share: half_up(dead x 1000, stand)
  - averages: half_up(sum, n)
  - leaf: half_up(defoliation x pct, 100)
  - loss: stand + half_up(leaf x (1000 - stand), 1000)
  - indemnity: half_up(payable x per_acre x acres, 100), with acres in tenths
- Liability and the 6.1 replant payment involve no division and are exact.

The r1 witnesses are unchanged. The sample job gives total and paid of 1747360.

## New findings

- **N1 (polish): trailing "divided by 100 per cent" in 4.2.** The clause could be attached grammatically to the whole "stand loss plus ...". Read that way the result is nonsense (about 0.2 for a 190 stand), so no competent reader takes it. It is safer to put the division inside the leaf term: "plus its leaf loss times what remains ..., that product divided by 100 per cent".
- **N2 (polish): 1.1's rounding trigger narrowed from "share or percentage" to "divides or averages".** After the rewrite every rule that needs rounding contains an explicit "divided by" or "average", so nothing that should be rounded is left unrounded. There are no other gaps.
- There are no new blocking or should-fix findings.
- The preservation boundary is drawn with the procedure's defined terms: hail-thinned (2.1) and replanted field (2.2). No sentence in the authority now positively governs a case the instruction treats as silent.

## Solver screen (r2)

- **Pre-mortem.** The repairs still map one-to-one onto the complaint: averaging over all plots, R4 = 40, 4.2, straight = 100, the vanishing cap, half-up indemnity, minimum loss 80 and minimum claim 10000. The only places a solver can go wrong are:
  - the two constants in `figures.py` that are coupled through `STEPS`. `plot_trace` and `minimum_loss` both read 50, and `replant_trace` and `minimum_claim` both read 2500, so an edit to the `FIGURES` values drags the kept calculations along;
  - the urge to zero shares on plots that are not hail-thinned, and lines for small replantings, because of the 2.1/2.2 definitions.

  A careful strong solver that reads "every constant of the package at its value today" gets all of it right.
- **Scores (5 = resists):**

  | Measure | Score |
  |---|---|
  | reference_unreachable | 1 |
  | authority_incomplete_for_grading | 1 |
  | hidden_state_not_closed_form | 1 |
  | restraint_traps | 2 (the two coupled constants inside the rebuilt table, plus two unlabelled subtypes excluded by definition chains, now free of competing text) |
  | fuzz_blind_spot | 2 |
  | self_verification_resistance | 2 |

- **Prediction: collapses. Confidence: medium-high.**
- **Decisive reason:** the contract is now unambiguous, and every required fix is named in the complaint. The only resistance left is two restraint sites that a careful reader of the preservation paragraph handles on the first pass.
