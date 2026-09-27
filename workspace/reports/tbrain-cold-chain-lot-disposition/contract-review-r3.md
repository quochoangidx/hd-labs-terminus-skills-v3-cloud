# Contract review r3: tbrain-cold-chain-lot-disposition

Packet read: `contract-review-packet-r3/instruction.md` and everything under `contract-review-packet-r3/environment/`. No other path was opened.

## What changed since r2

1. The SOP now defines the hold of a gap-opening reading as 0 (2.7).
2. 5.1 no longer weights the MKT by hold. Each reading is weighted by "the minutes from it to the next reading of its export (nought for the last ...)", which keeps gap spans in.
3. The chained-lot scoping is gone. 4.1 sums band time over every leg, and handovers are capped at 2,880 again.
4. Prior time is now built from release-certificate entries. Only "excursion entries" of 15 minutes or more count; shorter entries are "transients" (2.6, 2.9).
5. The silence clause is reduced to "the rest of the package's behaviour stays as it is".
6. In the package, `attribution.py` now has two constants (`LAST_READING_MINUTES`, `GAP_MINUTES`). One `held` list feeds both the band time and the MKT weights.

## Does r2 N1 still apply? No, it is closed.

N1 was about which value a gap-opener hold keeps under the silence clause, with a constant shared between two jobs. In r3:
- 2.7 gives the gap-opener hold a value (0), so the silence clause has nothing to preserve there.
- The package no longer shares the constant.
- The 1.4 "at least one pair ≤30 minutes" hint is gone.

It does not come back as a zero-weight MKT: every non-last reading's MKT weight is its spacing (≥1), and every export has ≥2 readings, so the total weight is > 0.

r2 N2 (the chained-lot trap) is withdrawn by the redesign. r1 F1–F5 remain closed: span containment is still in 1.4, and the other fixes still hold.

## Package defects (each with its SOP section)

| # | Site | Defect | SOP |
|---|---|---|---|
| D1 | `attribution.holds`, last reading | The last reading gets `LAST_READING_MINUTES` = 60. Its hold and its MKT weight are both 0. | 2.7, 5.1 |
| D2 | `attribution.holds`, gap opener | A gap opener's hold is the raw span. Its hold is 0, so it adds no band time. | 2.7, 3.1 |
| D3 | `disposition.dispose`, `weights += held` | The MKT is weighted by the band holds. The weight is the raw spacing to the next reading, gap spans included, with 0 for the last reading, so the MKT needs its own weight list. | 5.1 |
| D4 | `attribution.GAP_MINUTES = 60` | The gap threshold is 60. A gap is any interval over 30. | 2.4, 3.2 |
| D5 | `bands.band_of`, `low <= temp < high` | The upper limit is treated as out of range. The range is inclusive at both ends. | 2.1 |
| D6 | `bands.band_of`, `temp >= band.lower` | An above-range band's lower end is treated as inclusive (25.0 goes to `hot`). It is exclusive, so 25.0 goes to `warm`. Below-range bands are already right. | 2.5, 2.6 |
| D7 | `dispose`, `max(...)` over legs | Band time takes the max over legs. It should be the sum over every leg. | 4.1 |
| D8 | `dispose`, `remaining` | The certificate is ignored entirely. Prior time is the sum of entries ≥15 minutes; entries under 15 are left out. | 2.6, 2.9, 4.2 |
| D9 | `dispose`, `round(mkt, 1) > high` | The quarantine test compares the rounded MKT. It must compare the unrounded value. | 1.2, 6.2 |
| D10 | `report.hours`, `math.trunc` | Hours are truncated. They should round to the nearest hundredth, which also matters for negatives. | 1.2 |

These are already correct: `KELVIN_OFFSET` = 273.15, `math.fsum` weighted mean, `mkt_c` rounding with `round(.,1)`, loading, lot order, and the frozen test (strict `<` over every reading).

The instruction's symptoms cover D7, D8 (partially: it does not mention transients), D5, D9 and the MKT in general, D4, and D2 (the new "dropout ... booked as warm excursion time" symptom). The symptoms do not signal D1, D6, D10, the transient exclusion in D8, or D3's rule that gap spans stay in the MKT.

## Part 1: Contract review

**R1 (none, trap audit): 5.1 is written to diverge from the band hold on purpose.**
5.1: "weighted by the minutes from it to the next reading of its export (nought for the last reading of an export)". 2.7: "A reading that opens a logger gap ... ha[s] a hold of nought."

The package feeds one `held` list to both the band time and the MKT, and the new dropout symptom pushes toward zeroing gap holds. The natural single edit therefore also zeroes gap weights in the MKT. The rule sentence governs this explicitly. Nothing in the authority competes with it, and both readings come straight from the text.

Counterexample: `00:00,12.0` / `00:45,5.0` / `01:00,5.0`.

| MKT weight of the gap opener | MKT | Disposition |
|---|---|---|
| 45, per 5.1 | 10.7 | `quarantine` |
| 0, reusing the hold | 5.0 | `release` |

This is a fair restraint site. It is not a defect.

**R2 (none / polish, trap audit): transient certificate entries.**
2.9: "total length of the excursion entries". 2.6: "An excursion entry is an entry ... that lasts 15 minutes or more; a shorter entry records a transient."

The exclusion is reached through a defined-term chain. The definition sits in 2.6, next to "excursion reading", which a solver may skim. The README describes the certificate as "the list of entries" with no hint of the threshold, and the instruction's "already used up its hot allowance" symptom invites summing every entry. Nothing in the authority lists a competing rule, so the trap passes the text screen.

Counterexample: certificate cold `[14, 700]`, 16 minutes at 1.5.

| Entries counted | remaining.cold | Disposition |
|---|---|---|
| Excursion entries only (700) | 0.07 | `release` |
| All entries (714) | −0.17 | `reject` |

Polish: consider giving the certificate-entry definition its own numbered item. As placed, it is fair but easy to miss, and that is a legitimate source of difficulty rather than a contract hole.

**R3 (polish): the preamble promises markers that no rule carries.**
Preamble: "Some rules differ from common industry practice. Where they do, the rule says so". After the r3 edits no rule says so. Yet the 15-minute transient cut and the MKT weight that includes gaps are arguably non-standard. A reader could take the missing marker as a sign that these rules are standard, but that doesn't change any output, because the rules themselves are explicit.

Fix: drop the preamble's second paragraph, or mark one rule.

**R4 (none): the silence clause has no live target, which is harmless.**
"the rest of the package's behaviour stays as it is". Every figure in the report is now fully governed. The clause only protects input handling and the driver, and I found no SOP sentence it conflicts with. The left-open list is unchanged and is consistent with 1.4 and 1.5.

**R5 (none): exact conventions and ranges are complete.**
- Rounding: 1.2 rounds hours to the hundredth, and a whole number of minutes never lands halfway (5m/3). 1.5 keeps the MKT away from the limit and from halves.
- Boundaries: range inclusive (2.1), gap `>30` (2.4), entry `≥15` (2.6), unlogged `>120` (6.2), reject `<0` (6.1), frozen strictly `<` (2.8).
- Output: lot order and number format are stated.
- Ranges: every item in 1.4 has both ends, including the new entries (0–50 per band, 1–10,080 minutes each) and handover 0–2,880.
- Readings are confined to the span, so `band_of`'s fall-through is unreachable.

I found no remaining defect of blocking or should-fix severity.

### Hand-worked witnesses

Common record: range [2.0, 8.0], freeze 0.0, H 9880. Bands: cold [-10, 2) with 12 h, warm (8, 25] with 72 h, hot (25, 40] with 2 h. Each lot has one leg and no certificate unless stated.

| # | Input | Expected |
|---|---|---|
| W1 | `00:00,8.0` `00:30,8.0` `01:00,8.0` | band_hours all 0.0; remaining 12.0/72.0/2.0; unlogged 0.0; mkt 8.0 (not > 8.0) → `release` |
| W2 | `00:00,25.0` `00:20,5.0` `00:40,5.0` | 25.0 goes to warm; warm 0.33, hot 0.0, remaining warm 71.67; MKT 19.655 → 19.7 → `quarantine` |
| W3 | `00:00,12.0` `00:45,5.0` `01:00,5.0` | gap opener: hold 0, so warm 0.0, remaining warm 72.0; unlogged 0.75; MKT weights 45/15/0 → 10.71 → 10.7 → `quarantine` |
| W4 (dropout) | `13:00,30.0` `17:00,5.0` `17:10,5.0` | hot 0.0 (the gap is not excursion time); unlogged 4.0; MKT weights 240/10/0 → 29.64 → 29.6 → `quarantine` |
| W5 | `00:00` `01:01` `01:11` `02:11` `02:21`, all 5.0 | gaps 61+60, unlogged 121 min = 2.02 → `quarantine`; mkt 5.0 |
| W6 | legs A and B, each 19 readings of 10.0 every 10 min (180 min each), handover 2,880 | warm 6.0 (sum), remaining 66.0; unlogged 0.0 (handovers are not intervals); mkt 10.0 → `quarantine` |
| W7 | certificate cold `[14, 700]`; `00:00,1.5` `00:16,5.0` `00:26,5.0` | prior 700; cold 0.27 (16 min); remaining cold 4 min = 0.07; MKT 3.03 → 3.0 → `release` |
| W7b | as W7 with certificate cold `[15, 700]` | prior 715; remaining −11 min = −0.18 → `reject` |
| W8 | `00:00,8.1` `00:01,8.0` `00:30,8.0` `01:00,8.0` | warm 0.02 (hold 1); MKT weights 1/29/30/0 → 8.0017 → prints 8.0 but `quarantine` (unrounded > limit, beyond the 0.001 margin) |
| W9 | `00:00,-0.1` `00:10,4.0` `00:20,4.0` | cold 0.17; frozen → `reject`. A reading of exactly 0.0 is not frozen. |
| W10 | `00:00,5.0` `00:10,5.0` `00:20,30.0` (last reading) | last reading has hold and weight 0, so hot 0.0 and mkt 5.0 → `release`. The package today gives hot 1.0 and MKT 20.6. |

None of these needed a guess.

## Part 2: Solver-path screen

**A) Pre-mortem.** A strong solver reads the short SOP and the five small modules and lists the ten defects. The symptoms point it at the sum, prior time, the upper limit, the MKT, the gap threshold and gap holds. It then writes its own reference and targeted tests.

It could go wrong in three places:
1. After setting gap holds to 0, it keeps passing the same list to the MKT, which drops gap spans from the weights (D3). This is likely for a solver who patches `holds()` in place and never rereads 5.1's parenthetical.
2. It sums every certificate entry and misses the 15-minute excursion-entry definition, which sits under 2.6 and away from 2.9's use of it (D8).
3. It misses the exclusive lower end of above-range bands (D6), or truncation versus rounding (D10). A careful line-by-line diff catches both.

Its self-tests come from its own reading, so none of these misses would surface in self-verification. A solver that rebuilds each figure fresh from the SOP's definitions, instead of patching the package's shared lists, gets everything right. The contract is closed-form and unambiguous.

**B) Scores** (5 = strongly resists solving)

| Axis | Score | Why |
|---|---|---|
| reference_unreachable | 1 | A small closed-form reference follows directly from the SOP. |
| authority_incomplete_for_grading | 1 | I found no ambiguity. Every reported figure is defined, and every witness above works out without a guess. |
| hidden_state_not_closed_form | 1 | Everything is deterministic. |
| restraint_traps | 2 | (a) The MKT weight must stay while band holds are zeroed, inside the shared `held` aggregate the repair forces the solver to rebuild. It is stated explicitly in 5.1's rule sentence, so it gets partial credit. (b) Transient entries are a bare subtype excluded through a defined-term chain (2.9 then 2.6), with no competing enumeration. It counts. |
| fuzz_blind_spot | 2 | Gaps of 31+ minutes and 1–14-minute certificate entries show up often under random generation, but only against a correct oracle. A solver's own oracle carries its misreading. |

**C) Verdict**

- self_verification_resistance: 2
- prediction: collapses (both solvers fully solve) more likely than not. The residual risk is concentrated in D3 and the transient cut in D8.
- confidence: medium-low
- decisive_reason: the contract is now fully closed-form and unambiguous, so the only resistance left is two fair restraint sites (MKT weights that keep gap spans while band holds zero them, and transient certificate entries) that a solver rebuilding each figure from the SOP's defined terms will catch.
