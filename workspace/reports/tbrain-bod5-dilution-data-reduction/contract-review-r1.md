# Contract review r1 — tbrain-bod5-dilution-data-reduction (reviewer D)

Scope: I read instruction.md and environment/ only (SOP, README, package, driver, example, Dockerfile).

## Part 1 — Contract review

Visible defects in the package that the SOP clearly governs: the usable thresholds are 2.0/1.0 but should be 2.50/1.20 (2.3, 2.4); the seed factor is pooled Σdep/Σseed over all controls but should be the mean seed rate of usable controls (3.2); bottle BOD is dep/frac − corr but should be (dep − corr)/frac (4.1); the `<` bound uses the least-sample bottle and 2.0 but should use the most-sample bottle and 2.50 (5.3); the blank figure is a mean but should be the max (7.1); RPD divides by the parent but should divide by the mean of the two (6.1); rounding is `round(x,1)` but should be 3 significant figures, half away (1.2). Most of these line up with the complaints in the instruction. The goal is clear.

### Findings

1. **Blocking: seed factor when no seed control is usable.** The instruction says 1–6 controls come "in any mix of usable and unusable ones", so an all-unusable set is in range, and SOP 3.2 ("the mean seed rate of its usable seed controls") has no value then. The silence rule says to work it out "the way the package works it out today from the quantities the SOP does define". The package today computes a pooled Σdepletion/Σseed_ml over all controls. The SOP-defined quantity is the seed rate (3.1). A solver can reasonably land on either:
   - (a) the pooled ratio over all controls, which keeps today's formula;
   - (b) the mean seed rate over all controls, which applies today's "use all controls" fallback to the SOP-defined quantity.

   Counterexample: controls {seed 10, 8.00→7.00} and {seed 20, 8.00→7.00}, both with depletion 1.0 and so unusable. (a) gives 2/30 = 0.066667 and (b) gives (0.1+0.05)/2 = 0.075. The two readings then give different seed_factor, check_value and every seeded sample value. An agent that ends up with 0/0 and raises also has a case: the SOP leaves the figure undefined, and "Add no exception… guard" pushes the other way. The authority needs one sentence that fixes the fallback, or the grader must accept both.

2. **Blocking: does qualifier G compare the rounded or the unrounded check value?** SOP 1.2 says "A reported value (… the check value in section 7) is rounded to three significant figures". SOP 7.2 says "A check value below 175 or above 225 puts the qualifier G". SOP 1.5 only keeps the check value off 175/225 by 10^-6, and that does not close the gap. Counterexample: the unrounded mean is 174.8. Under the unrounded reading it is below 175, so G. Its rounded value is 175, so under the rounded reading there is no G. The same gap exists at 225.3 and on the high side. The package today compares the unrounded value, and a careful reader of 1.2 ("the check value … is rounded") may compare the rounded one. The SOP needs a sentence such as "limits are tested on the unrounded figure", or 1.5 needs to keep check values within half a unit of the third significant figure away from both limits.

3. **Should-fix: RPD for a duplicate pair where either side is `<`/`>`.** SOP 6.1 uses "measured BOD", which 5.1 defines only for samples with a usable bottle. The instruction says duplicates can involve a sample "whatever that sample's relation", so this case will be graded. Under the silence rule the natural answer is the package's current quantity, the unrounded bound value, fed into the SOP's mean-denominator RPD. A competing reading is also plausible: use the reported (rounded) value, or leave the duplicate out. Counterexample: A is `<` 3.75 and B is `=` 5.0. Using the bound gives RPD 28.571…, which fails. Using a different figure changes the outcome. The instruction's generic silence sentence probably settles this as the bound value, but it only works through a chain of inference. One explicit clause would remove the risk.

4. **Should-fix: RPD inputs rounded or unrounded.** 1.2 says "every RPD [is] reported exactly as worked out", but it does not say whether the inputs are the rounded reported values or the unrounded measured BODs. 6.1's "measured BOD" (5.1, the unrounded mean) points to unrounded, and the package already works that way. Close to a pass-flip at 25%: A = 100.04 and B = 128.62 (rounded 100 and 129) give different RPDs. 1.5 guards only near 25 itself. The reading is low-risk, but I am noting it.

5. **Polish: 5.3 "its bottle holding the most sample" includes spent bottles.** In a mixed sample (one spent bottle, one low-depletion bottle) the literal text picks the largest bottle even if it is spent. A domain expert might pick the largest non-spent bottle. The text is literal and the package already iterates over all bottles, so I read it as governed. Counterexample: spent 200 mL plus low-depletion 100 mL. Literal reading gives `<` 3.75, expert instinct gives `<` 7.5.

6. **Polish: the rounding tie rule.** 1.2 "half away from nought" is made moot by 1.5 (no ties within 10^-9). The authority is present, which is fine.

7. **Polish: the ordering conventions** (sample order, duplicate order, and `B` before `G`) all have an authority sentence in §8. The `>` and `<` tie-breaks have one in 5.4, and Python's `min`/`max` already take the first match. No issue.

8. **Ranges:** every numeric range has both a floor and a ceiling (volumes, DO, blank depletion, seed rate 0–0.3/mL). Seed rate's floor is "nought", but the instruction's §1.4 copy says "up to 0.3", which is consistent. A seed control with final > initial (negative depletion) conflicts with SOP 1.4's floor of nought. The instruction says bottles may have "a final DO above the initial one", and for controls that would breach 1.4, so such a batch is out of limits. That is fine but slightly confusing.

### Hand-worked witnesses

- W1 seed factor: SC {10 mL, 7.00→4.00} gives rate 0.3, and SC {20 mL, 8.00→4.00} gives rate 0.2, so the mean is **0.25**. The old package gave 7/30.
- W2 bottle BOD: sample 30 mL, seed 2 mL, 8.00→4.00, factor 0.25: (4.0 − 0.5)/0.1 = **35.0** reported `=` 35.0. The old package gave 39.5.
- W3 `<`: bottles of 100 and 200 mL, both 8.00→7.00: `<` 2.5/(200/300) = **3.75**.
- W4 `>`: bottles of 10 and 20 mL, both 8.00→0.50, no seed: `>` 7.5/(10/300) = **225.0**.
- W5 blanks: depletions −0.10 and 0.25 give blank **0.25**, which is qualifier `B`. The old mean of 0.075 gave no B.
- W6 duplicate: `=` 100 and `=` 120 give RPD 20/110·100 = **18.181818…**, so pass true. The old package gave 20.0.
- W7 check: 6 mL, no seed, 8.00→4.40 gives 3.6/0.02 = **180.0**, no G. Adding a second bottle with final 1.19 marks it spent and excludes it.
- W8 rounding: 1234.5678 gives **1230.0**, and 0.0123456 gives **0.0123**.
- W9, guessed: all seed controls unusable. See F1. I could not decide between 0.066667 and 0.075.
- W10, guessed: check mean 174.8. See F2. G or not depends on the reading.

## Part 2 — Solver-path screen

**A) Pre-mortem.** A strong solver reads the SOP line by line, diffs it against 6 short modules and fixes all seven visible defects in under 30 minutes. It writes its own reference from the SOP, fuzzes batches across §1 limits and self-checks with 1e-6 tolerance. The work is closed-form arithmetic with no hidden state. It can only go wrong on the left-open or ambiguous seams: the all-unusable-seed-control fallback (F1), which may get a NaN guard, a switch to the mean of all rates, or be left pooled; rounded-versus-unrounded G (F2); and bound-value RPDs (F3). The solver's self-tests share its own reading, so they cannot catch a mismatch there. Otherwise it fully solves.

**B) Scores (5 = resists)**

- reference_unreachable: **1**. A few dozen lines of arithmetic, and the full authority is visible.
- authority_incomplete_for_grading: **3**. F1 and F2 are real ambiguities, and that is a defect, not difficulty.
- hidden_state_not_closed_form: **1**.
- restraint_traps: **1**. The only "stop" site is keeping the pooled formula as the fallback in F1. It sits inside the seed-factor aggregate that the repair forces the solver to rebuild, so it would count, but its authority is a vague "the way the package works it out today" with a competing SOP-defined quantity, so it fails the 0/8 screen and counts as a contract defect instead. Everything else is written into rule sentences.
- fuzz_blind_spot: **2**. Near-limit values are promised, and a self-written fuzzer mirrors the solver's own reading.

**C)** self_verification_resistance: **2**. prediction: **collapses**, unless the grader happens to encode the minority reading of F1 or F2, in which case the failures come from the defect, not from difficulty. confidence: medium-high. decisive_reason: every defect is a visible, one-line diff against an explicit SOP, and the only resistance comes from under-specified fallback seams that should be fixed rather than counted.
