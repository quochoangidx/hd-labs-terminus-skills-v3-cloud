# Contract review r1: tbrain-qpcr-relative-expression

Reviewer B. Packet read: `instruction.md`, `environment/` (Dockerfile, .dockerignore, README, SOP QP-7, driver, `src/qpcrrel/*`, `examples/plate-demo.json`). Nothing else was opened.

## Part 1: Contract review

### Deviations a reader finds in the present code (for context)

These are the SOP rules the present code breaks. A second engineer would find the same list, so none of them is a clarity problem:

1. `curve.py` scores `Undetermined` standards as 40 and counts single-well levels as points, which breaks 2.4.
2. It fits a curve from 2 points, where 2.5 needs 3 or more.
3. It clamps the factor at 2, which breaks 3.1.
4. `replicates.reportable` uses `< 35` and has no 10.00 floor, which breaks 2.2.
5. `kept` drops outliers only when exactly one is stray, which breaks 4.1.
6. `mean_ct` returns 40 for a gene that is not detected, which breaks 4.3.
7. `ntc.contaminated` treats any determined well as contamination, which breaks 2.6.
8. `fold_change` uses the target's factor for the reference genes and an arithmetic mean of the shifts, which breaks 5.1 and 5.2.
9. `result` nulls the fold change only on `ntc`, which breaks 5.4 and 6.3.

### Findings

**F1 (blocking): the factor for a gene with exactly 2 curve points (or with 0–1 curve points but several raw levels) can be read three ways.**
Citations:
- SOP 2.5: "fitted through the gene's curve points where the gene has three or more of them"
- SOP 3.1: "10^(-1/s), where s is the slope of the gene's standard curve … with no ceiling"
- SOP 1.4: "Wherever a gene has two or more curve points (2.4), the least-squares slope through them lies from -4.20 to -2.90"
- instruction: "that value stays whatever the package's present code makes of it, taking as its inputs the values the SOP does settle"

A gene with fewer than 3 curve points has no standard curve, so the SOP is silent on its factor. The present code's fallback is `amplification_factor(standards)`: raw wells go in, the code builds its own `curve_points` (Undetermined read as 40, single-well levels kept), then applies `<2 → 2.0` and the `min(…, 2)` clamp. The reader can't tell which of these is meant:
- (R1) Run the whole present function on the raw standards.
- (R2) Run the present logic on the SOP's curve points, since the SOP does settle those (2.4). That gives 2.0 when there are fewer than 2 points, and `min(10^(-1/s), 2)` when there are exactly 2.
- (R3) Drop the clamp everywhere. Readers will be pulled toward this by 3.1 "no ceiling", by the instruction's "Add no … clamp", and by 1.4, which gives 2-point series slopes down to -2.90 (factor 2.21). That makes a factor above 2 look like an expected input.

Counterexample, one gene:
- q=1000 has Ct [20.00, 20.00].
- q=100 has Ct [23.30, 23.30].
- q=10 has a single well at Ct 27.00.

Results:
- R1: 3 present points, slope -3.5, factor 1.930698 (under the clamp).
- R2: 2 SOP points, slope -3.3, 10^(1/3.3)=2.009233, clamped to **2.0**.
- R3: **2.009233**.

This single gene gives three different outputs. The instruction's test list says plates include "dilution series of up to eight levels of one to four wells", "standard series with `Undetermined` wells" and "amplification factors on both sides of 2", so this case will almost certainly be graded. Fix: add an instruction or SOP sentence saying what a gene with fewer than three curve points gets. For example, say that it gets the present code's factor computed from its curve points, with the present ceiling kept. Or put "fewer than three curve points" on the left-open list.

**F2 (blocking): the mean Ct is undefined when every reportable replicate is an outlier (even counts only).**
Citations:
- SOP 4.1: "each of those replicates that lies more than 0.50 cycles from their median is an outlier. The median of an even number of replicates is the mean of the middle two."
- SOP 4.2: "the arithmetic mean of the sample's reportable replicates of that gene that are not outliers"
- SOP 6.3: "A result has a fold change exactly when it has no flag."

Take reportable replicates [20.00, 20.00, 22.00, 22.00]. The median is 21.00 and all four wells sit 1.00 away, so all four are outliers. The sample is still detected (2.3), so it gets no `nd` flag, and 6.3 then requires a fold change. That means a mean Ct must exist, but 4.2 averages an empty set. The SOP is therefore silent here, and the instruction's fallback leaves three readings:
- (a) The present `kept`, fed SOP-reportable replicates, sees more than one stray and keeps them all. Mean = **21.0**.
- (b) The SOP settles the outlier set as empty, and the present `mean_ct` on an empty set returns **40.0**.
- (c) The natural reading is `null`, which contradicts 6.3.

Variant: [20.00, 20.20, 21.80, 22.00] gives the same three readings. This case is not on the left-open list, and "replicate sets with one or several wells far from the rest" suggests the plates include it. Fix: add it to the left-open list, or add a rule to the SOP.

**F3 (should-fix): the boundary of "values the SOP does settle" isn't defined.**
The instruction's key sentence ("taking as its inputs the values the SOP does settle") doesn't say at what granularity the present code is reused: whole function, helper, or intermediate value. F1 and F2 both come from this gap. One sentence naming the silent cases and how each should be computed would close it.

**F4 (polish): nothing says whether early NTCs contaminate, though the rules decide it.**
SOP 2.6 says "a Ct at or below the cut-off cycle". An NTC at Ct 8.00 therefore contaminates, even though 2.2 calls a Ct under 10 a "baseline or saturation fault" for unknowns. The rule is positive and clear, but a solver might carry the 10.00 floor over by analogy. The rule is written into the sentence, so this is fine; it is noted only because the instruction lists "late or early" NTCs.

**F5 (polish): "sample" is never defined in the SOP.**
6.2 says "every sample". The only source is the sample names on unknown wells, and 1.3 guarantees every sample has wells for every gene, so no counterexample exists within the limits.

**F6 (polish): genes in wells but not on the plate map fall outside README/1.3.**
They are open by "files that do not follow README" only by implication. No action needed.

Checked and found sound:
- Rounding: 1.2, none.
- Ordering: 6.1 and 6.2 (code-point order is Python's default `sorted`).
- Flag order: 6.3.
- The cut-off is inclusive: 2.2 "up to and including".
- The 0.50 tie is open by 1.5. Because Cts have 2 decimals, float noise can't flip a true non-tie.
- Every numeric range has a floor and a ceiling: Ct 5–45, quantity 1e-3–1e8, slope -4.20 to -2.90, and all the counts.
- References use their own factors (5.1) and a geometric mean (5.2).
- Standards use every determined Ct, with no cut-off (2.4).

### Grounded witnesses (worked by hand from the contract)

| # | Input | Output implied | Guess? |
|---|---|---|---|
| W1 | Gene with levels 1000/100/10, each [20,20]/[23,23]/[26,26] | slope -3.0, factor 10^(1/3) = 2.154434690 (no ceiling) | no |
| W2 | Replicates [20.00, 20.10, 20.20, 25.00, 26.00] | median 20.20; 25.0 and 26.0 are outliers; mean_ct 20.10 (present code gives 22.26) | no |
| W3 | NTC Cts: 37.00 / 35.00 / 8.00 / Undetermined | contaminated: false / true / true / false | no |
| W4 | Replicates [9.50, 20.00, 20.20] | reportable [20.00, 20.20] (n=2, no outlier test), mean 20.10 | no |
| W5 | Replicates [35.00, 35.20, Undetermined] | reportable [35.00], mean_ct 35.0 | no |
| W6 | Reference not detected in sample; target fine | flags ["ref"], fold_change null, mean_ct = target mean (number) | no |
| W7 | R1 has no standards, so factor 2.0; R2 factor 10^(1/3); T factor 10^(1/3.6)=1.895736. Calibrator R1/R2/T = 20/22/25, sample 21/22.5/23 | RQ_R1 = 0.5, RQ_R2 = 2.1544^(-0.5), RQ_T = 1.8957^2. fold = RQ_T / sqrt(RQ_R1·RQ_R2) = 6.157492432 | yes for R1's 2.0 (silent fallback); R1 has no points, so every reading agrees |
| W8 | Gene with no standards | factor 2.0 | fallback, but every reading agrees |
| W9 | F1 gene (2 SOP points plus a single-well level) | 1.930698 / 2.0 / 2.009233 | **guessed** |
| W10 | Replicates [20, 20, 22, 22] | mean 21.0 / 40.0 / null | **guessed** |
| W11 | Calibrator row, no flags | fold_change 1.0 | no |

## Part 2: Solver-path screen

**A) Pre-mortem.**
A strong solver reads SOP QP-7, compares it rule by rule with the six small modules, and fixes the nine deviations listed above. None of them needs more than a reading of the SOP. It then writes an independent reference from the SOP, fuzzes plates within the section 1 limits, and diffs the two outputs. The core path is short and closed-form, and self-checking against its own SOP reference will catch almost every slip: the cut-off being inclusive, the 10.00 floor, multi-outlier removal, per-gene factors, the geometric mean, and fold changes nulled on any flag.

The only places it can go wrong are the silent cases, and there its own reference shares its reading, so fuzzing can't catch the mistake:
- The 2-point factor (F1). Most likely it drops the clamp everywhere (R3) or runs present `curve_points` on raw wells (R1).
- The all-outlier even set (F2). It could return null, 40, or the mean of all.

Whether it passes depends on which reading the hidden reference picked, not on engineering skill.

**B) Scores (5 = strongly resists solving).**
- reference_unreachable: **2**. The reference can be derived from the SOP plus the visible present code.
- authority_incomplete_for_grading: **4**. F1 and F2 are graded cases with 2–3 defensible outputs. This is a defect, not difficulty.
- hidden_state_not_closed_form: **1**. All state is visible: the present code and the SOP.
- restraint_traps: **1**.
  - Keeping the `min(…,2)` ceiling for 2-point genes sits inside `amplification_factor`, which the repair has to rebuild, and it is excluded only by the 3.1→2.5 "standard curve" definition chain, so it would qualify. It fails the 0/8 screen, though. 1.4 is a competing positive statement about 2-point slopes, which reach a factor of 2.21. 3.1 "no ceiling" and the instruction's "Add no … clamp" give strong contrary instinct. So it is contract defect F1, not a point.
  - The `<2 points → 2.0` fallback is natural and every reading agrees on it, so it is not a trap.
- fuzz_blind_spot: **2**. A self-written reference covers the settled rules. It is blind only on the silent cases, where it shares the solver's reading.

**C)**
- self_verification_resistance: **2**
- prediction: **collapses** on the engineering. Any resistance measured would come from the F1/F2 ambiguities, which would make it an invalid difficulty signal.
- confidence: moderate (0.6).
- decisive_reason: every settled rule is a short, visible, closed-form fix a solver can check against its own SOP reference, and the only places it can fail are contract gaps (the 2-curve-point factor and the all-outlier even replicate set), which have to be closed rather than counted as difficulty.
