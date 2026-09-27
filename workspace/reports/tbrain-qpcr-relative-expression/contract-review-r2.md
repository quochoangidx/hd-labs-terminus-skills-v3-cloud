# Contract review r2: tbrain-qpcr-relative-expression

Reviewer B. Packet read: `contract-review-packet-r2/instruction.md` and `environment/` (Dockerfile, .dockerignore, README, SOP QP-7, driver, `src/qpcrrel/*`, `examples/plate-demo.json`). Nothing else was opened. I treated this as a fresh contract.

## Status of r1 findings

- **r1 F1 (factor for fewer than 3 curve points): CLOSED.** SOP 2.5 now fits "through all of the gene's curve points where the gene has two or more of them". SOP 3.1 now says "A gene with fewer than two curve points has no standard curve, and its amplification factor is 2", and the "such a factor" qualifier on "no ceiling" is gone. The rule covers every curve-point count from 0 upward, and the ceiling is removed for every fitted gene.
- **r1 F2 (every reportable replicate an outlier): CLOSED.** SOP 4.1 now reads "the median of an even number of replicates is the lower of the middle two, so the median is always one of the replicates and is never an outlier". So at least one replicate always survives, and a detected sample always has a mean Ct. 5.4 and 6.3 are now consistent.
- **r1 F3 (how much present code the fallback reuses): CLOSED in effect.** The sentence now reads "the one the present package computes for it when its present code is run on the values the SOP settles". The exact scope of that reuse is still not spelled out. However, I could not find any value inside section 1 that the SOP leaves unsettled (see N3), so the sentence has nothing to apply to. It is kept only as a polish note.

## Part 1: Contract review

### Package defects (present code vs SOP)

| # | Site | Defect | SOP |
|---|---|---|---|
| D1 | `curve.curve_points` | Reads `Undetermined` standard wells as 40.0 (`NO_CALL_CT`). They should play no part. | 2.4 |
| D2 | `curve.curve_points` | Accepts a level when it has two or more wells of any kind. It should need two or more *determined* wells: a level of [20.0, Undetermined] is currently a point at 30.0. | 2.4 |
| D3 | `curve.amplification_factor` | `min(…, 2.0)` caps the factor at 2. | 3.1 |
| D4 | `plate.called` used by `replicates.detected` and `sample_ct` | Has no 10.00 floor for reportable replicates (the `<= 35` upper bound is right). | 2.2, 2.3 |
| D5 | `replicates.sample_ct` | Never rejects outliers: there is no lower-median test at more than 0.50 cycles. | 4.1, 4.2 |
| D6 | `replicates.sample_ct` | Returns 40.0 for a gene that is not detected. It should return no mean (`null` in the report). | 4.3, 6.2 |
| D7 | `expression.fold_change` | Uses the target's factor for every reference gene and averages the Ct shifts arithmetically. Each gene should use its own factor, combined by a geometric mean of the relative quantities. | 5.1, 5.2, 5.3 |
| D8 | `expression.result` | Nulls the fold change only on `ntc`. It should be null on any flag. | 5.4, 6.3 |

Not defects:
- `ntc.contaminated`, which uses `called`, i.e. `<= 35` with no floor, matches 2.6 as written.
- The flag logic in `flags_for` is right once D4 is fixed.
- Sample ordering and gene ordering already match 6.1 and 6.2.

These defects are coupled through shared helpers:
- `called` feeds both NTC contamination and replicate reportability.
- `replicates.mean_ct` feeds both curve points and sample means.

Changing either helper in place breaks the other consumer. See N1.

### Findings

**N1 (polish, which also works as a legitimate trap): a fix to a shared helper can leak into another rule.**
- Adding the 10.00 floor inside `plate.called` (the natural one-line fix for D4) makes an NTC at Ct 8.00 read as uncontaminated. That contradicts 2.6, which covers a Ct "at or below the cut-off cycle".
- Putting outlier rejection or reportable filtering inside `replicates.mean_ct` changes curve points. 2.4 says a curve point's Ct is "the arithmetic mean of the Cts of those determined wells", with no cut-off and no outliers.

The instruction lists "standard and NTC wells at any Ct the section allows" and "levels whose wells disagree with one another", so both couplings are exercised.

Counterexamples:
- An NTC at Ct 8.00: the SOP gives `contaminated: true`; the leaky fix gives false.
- A standard level [8.00, 8.20]: the SOP gives a point at 8.10; the leaky fix drops it.
- A standard level [20.0, 20.1, 21.9] (wells that disagree): the SOP gives a point at 20.6667; the leaky fix gives 20.05.

The governing sentences are explicit, so this is fair, not a defect.

**N2 (polish): the lower-median convention runs against instinct, but the SOP states it.**
Citation: SOP 4.1 "the lower of the middle two". An agent that reaches for `statistics.median` gets a different answer.

Counterexample: [20.00, 20.30, 20.90, 21.00].
- Lower median 20.30: outliers are 20.90 and 21.00, so the mean is **20.15**.
- Mean-of-middle median 20.60: the outlier is 20.00, so the mean is 20.7333.

The authority sentence is present and unambiguous, so no action is needed.

**N3 (polish): the silent-value fallback in the instruction now appears to have nothing to apply to.**
Citation: "Should a plate inside section 1 ever need a value the SOP has no rule for…"

I checked for any value the SOP leaves unsettled inside section 1 and found none:
- factor at 0 curve points, 1 point, 2 points, and 3 or more;
- curve-point Ct;
- reportability, including the 10.00 and 35.00 bounds;
- outliers;
- mean Ct, both detected and not detected;
- contamination;
- relative quantity, normalisation factor and fold change;
- flags, ordering and nulls.

The sentence's scope is still vaguely worded (whole function or helper?), but that only matters if some case reaches it. It is harmless as long as the author's reference doesn't rely on it anywhere. Recommendation: the author should confirm the reference never takes a present-code fallback branch. If it never does, the sentence can stay as insurance.

**N4 (polish): "sample" is not defined in the SOP.**
It is implied by the unknown wells' `sample` names, and 1.3 guarantees every sample has wells of every gene. I found no counterexample inside the limits.

Checked and found sound:
- No rounding (1.2).
- Every range has a floor and a ceiling: Ct 5–45, quantity 1e-3–1e8, slope -4.20 to -2.90, and all counts.
- The 10.00 and 35.00 bounds are both inclusive (2.2).
- The 0.50 tie is left open by 1.5. Cts have two decimals, so float noise cannot flip a true non-tie.
- Ordering and flag order are stated (6.1–6.3).
- 5.4 and 6.3 are equivalent: detected implies a mean exists.
- A slope through 2 or more points is always defined, because no two levels share a quantity (1.3).

### Hand-worked witnesses

| # | Input | Output the SOP implies | Guess? |
|---|---|---|---|
| W1 | Gene standards: q=1000 [20.00, 20.00]; q=100 [23.40, 23.20, Und]; q=10 [26.60, Und] | Points (3, 20.0) and (2, 23.3). The q=10 level has only 1 determined well, so it is not a point. Slope -3.3, factor **2.009233002565** (no ceiling). | no |
| W2 | Standards q=1e6 [8.00, 8.20]; q=1e5 [11.50, 11.50]; q=1e4 [14.80, 14.80] | Early Cts still count. Slope -3.35, factor **1.988416978008** | no |
| W3 | Gene with standards at only one level, [20.0, 20.1] (1 curve point); or with no standards | factor **2.0** | no |
| W4 | Replicates [20.00, 20.10, 20.20, 25.00, 26.00] | Median 20.20; 25 and 26 are outliers; mean_ct **20.10** | no |
| W5 | Replicates [20.00, 20.30, 20.90, 21.00] | Lower median 20.30; mean_ct **20.15** | no |
| W6 | Replicates [9.50, 20.00, 20.20] | Reportable [20.00, 20.20]; fewer than 3, so no outlier test; mean_ct **20.10** | no |
| W7 | Replicates [35.00, 35.20, Und] | mean_ct **35.0**; detected | no |
| W8 | NTC Ct 8.00 / 35.00 / 35.01 / Und | contaminated true / true / false / false | no |
| W9 | R1 has no standards (factor 2); R2 factor 10^(1/3); T factor 10^(1/3.6). Calibrator R1/R2/T = 20/22/25; sample = 21/22.5/23 | fold = T^2 / sqrt(2^-1 · R2^-0.5) = **6.157492431837**; flags [] | no |
| W10 | A reference gene is not detected in the calibrator | Every result on the plate: flags include `ref`; fold_change null; mean_ct of the target still reported where the target is detected | no |

No witness needed a guess.

## Part 2: Solver-path screen

**A) Pre-mortem.**
A strong solver diffs the eight defects against the SOP. Each one is a local, closed-form fix in six small files. It writes an independent SOP reference, perhaps 80 lines, fuzzes plates inside section 1, and compares the outputs.

Where it could slip:
- It could put the 10.00 floor into the shared `called` helper, so early NTCs stop counting as contamination.
- It could route curve points through a changed `mean_ct`, adding cut-off or outlier filtering.
- It could use `statistics.median` instead of the lower median.
- It could leave `len(cts) >= 2` counting undetermined wells.

Each of these contradicts an explicit SOP sentence. A reference built from the SOP rather than from the patched package catches all of them on the first fuzz run with early NTCs, early standards, or even replicate counts. The only real risk is a solver that tests its patch against itself. With no gaps in the contract left, a careful solver ends with the exact answer.

**B) Scores (5 = strongly resists solving).**
- reference_unreachable: **1**. The whole reference follows from the SOP alone.
- authority_incomplete_for_grading: **1**. I found no graded case the SOP leaves unsettled. r1 F1–F3 are closed.
- hidden_state_not_closed_form: **1**. Everything is visible and closed-form.
- restraint_traps: **2**.
  - Two sites qualify as shared-helper stops inside aggregates the repair rebuilds: the floor must not reach `called`'s NTC use, and outlier or cut-off handling must not reach `mean_ct`'s curve use.
  - Both have explicit positive rule sentences (2.4 and 2.6), and a self-written reference defeats them.
- fuzz_blind_spot: **1**. A fuzzer within section 1 that includes early and late NTCs and standards hits every defect.

**C)**
- self_verification_resistance: **1**
- prediction: **collapses**. Both of two strong solvers fully solve.
- confidence: high (0.8).
- decisive_reason: now that r1 F1–F3 are closed, every defect is a local fix governed by an explicit SOP sentence that a solver's own SOP-derived reference and fuzzer check directly. Only the shared-helper couplings could catch a solver, and a reference built from the SOP catches both.
