# Contract review r2 — tbrain-bod5-dilution-data-reduction (reviewer D)

Scope: I read contract-review-packet-r2 instruction.md and environment/ only. The package source and README are unchanged from r1. The SOP gained 1.2 (last sentence), 2.5, 3.2 (now "reference controls"), 5.3 ("spent or not") and 7.2 ("before rounding"). The instruction's silence sentence now reads "the package's present calculation for it stays exactly as it is, applied to the quantities the SOP does define".

## r1 findings — status

| r1 | Topic | Status |
|---|---|---|
| F1 (blocking) | Seed factor with no usable control | **Closed.** 2.5 plus 3.2 give the mean seed rate over all controls. W: {10 mL, dep 1.0} and {20 mL, dep 1.0} give 0.075. The package's pooled ratio (0.0667) is now wrong, and the SOP governs it. |
| F2 (blocking) | G on rounded or unrounded | **Closed.** 7.2 says "before rounding". Check 174.8 gets G, with check_value 175.0. |
| F3 (should-fix) | RPD when one side is a bound | **Open, reshaped.** See N1. |
| F4 (should-fix) | RPD inputs rounded? | **Closed.** 1.2 now says "Every figure is worked out from unrounded figures". |
| F5 (polish) | `<` bottle may be spent | **Closed.** 5.3 says "spent or not". |
| F6–F8 (polish) | Tie rule, orderings, ranges | Unchanged and fine. The note about negative depletion in seed controls stands: it is excluded by 1.4 and so left open. |

## New findings

**N1. Should-fix (borderline blocking): the RPD formula when either side is `<` or `>`.** SOP 6.1 defines RPD on "measured BOD", which 5.1 defines only for `=` samples. So for a pair with a bound the RPD is "a figure without a definition", and the instruction then says "the package's present calculation for it stays exactly as it is". The present code is `abs(mine - theirs) / theirs * 100`, which divides by the parent and not by the mean. Two competent readings remain:
- (a) Bound pair: keep the parent-denominator formula on the unrounded section-5 values. `=`/`=` pair: SOP mean denominator.
- (b) Only the missing input is undefined. The SOP's mean-denominator formula still governs, fed with the section-5 values.

Counterexample: the duplicate is `<` 4.0 and the parent is `=` 5.3. (a) gives 1.3/5.3 = **24.528%, pass**. (b) gives 1.3/4.65 = **27.957%, fail**. The `pass` field is compared exactly, so this is a pass-flip. The text supports (a) literally ("stays exactly as it is"), and I think that is the intended restraint. However, domain instinct and 6.1's positive formula both pull toward (b), and neither the SOP nor the instruction says which part of 6.1 survives when its input is missing. One clause would close it, e.g. "where either sample is not measured, the RPD is the package's present figure computed from the two reported values before rounding". Direction also matters under (a): "theirs" is the sample named in `duplicate_of`, which the instruction does not restate. It is visible in the code.

**N2. Polish: silence scope is now effectively one site.** The instruction's generic silence paragraph, after 2.5, governs only N1. A reader who does not locate that site will read the paragraph as boilerplate. This is not a defect, just a note that the whole restraint load now sits on N1.

## One value per case

- Seed factor: yes in every mix, via 2.5.
- Bottle BOD, `=`/`<`/`>` values and the 5.4 tie: yes.
- Check value: yes, because at least one check bottle is usable. G is decided on the unrounded value.
- Blank depletion and B: yes.
- RPD `=`/`=`: yes. RPD with a bound on either or both sides: yes under the literal reading (a), but see N1 for the competing reading.
- Divide-by-zero: none possible in range. Usable BOD ≥ (2.5 − 0.9)/1 > 0, and bounds are positive.

## Witnesses (hand-worked)

- W1: SC {10 mL, 7.00→4.00} and {20 mL, 8.00→4.00}, both usable, give **0.25**.
- W2: all controls unusable, {10, dep 1.0} and {20, dep 1.0}, give **0.075**.
- W3: 30 mL, seed 2, 8.00→4.00, factor 0.25: (4 − 0.5)/0.1 = **`=` 35.0**.
- W4: 100 mL at 8.00→7.00 plus 200 mL at 8.00→1.00 (spent) give **`<` 2.5/(200/300) = 3.75**.
- W5: 10 mL and 20 mL, both 8.00→0.50, no seed, give **`>` 225.0**.
- W6: blanks −0.10 and 0.25 give **0.25, B**.
- W7: check mean 174.8 gives **check_value 175.0, qualifiers "G"**.
- W8: `=` 100 vs `=` 120 give **RPD 18.181818…, pass**.
- W9 (reading a): `<` 4.0 duplicating `=` 5.3 gives **24.528…, pass**. Under (b) it would be 27.957, fail.
- W10: 1234.5678 rounds to **1230.0**.

## Part 2 — Solver-path screen

**A) Pre-mortem.** A strong solver fixes the thresholds, the reference-control seed factor, the 4.1 operation order, the 5.3 bottle and constant, the blank max, the RPD mean denominator and 3-significant-figure half-away rounding. That is about 30 minutes of work. It self-checks with a SOP-derived reference and fuzzing, and everything closes in form. The one decisive step is the RPD denominator: a natural repair rewrites `duplicates()` to the SOP's mean denominator for every pair. Only a solver who follows the chain "measured BOD is defined only by 5.1, so a bound pair's RPD is undefined, so the present calculation stays exactly" keeps the parent denominator for bound pairs. Its own tests encode its own reading, so self-verification cannot catch it. I expect roughly half of strong solvers to miss this, and a careful re-read of the silence paragraph rescues the rest.

**B) Scores (5 = resists)**

- reference_unreachable: **1**.
- authority_incomplete_for_grading: **2**. N1 has a literal answer but a real competing reading.
- hidden_state_not_closed_form: **1**.
- restraint_traps: **3**. N1 is one site inside the RPD aggregate that the repair forces the solver to rebuild, reached by a definitional chain (5.1 "measured BOD"), and it goes against strong expert instinct. It partly fails the 0/8 screen because 6.1 is a competing positive formula. It counts as one trap, with contract risk.
- fuzz_blind_spot: **3**. Bound-pair duplicates are guaranteed in the grading set but are easy to under-sample, and a self-fuzzer shares the solver's own reading.

**C)** self_verification_resistance: **3**. prediction: **resists (weakly)**. At least one of two solvers probably rewrites the bound-pair RPD to the mean denominator. confidence: low-medium. decisive_reason: all resistance rests on the single N1 site, whose literal reading is defensible but whose competing reading is also defensible, so a pass-flip failure there may be read as a contract defect rather than difficulty.
