# contract_review adjudication — tbrain-discrete-pid-controller

Reviewer: one fresh general-purpose subagent (Claude Code, model alias `opus`), blind to tests/ and solution/ (packet = instruction.md + environment/ copied to scratchpad). Turn 1 of 2.

| # | Finding (reviewer severity) | Builder | Orchestrator | Action |
|---|---|---|---|---|
| 1 | Silence granularity undecided: helper formula vs old pipeline vs note formula (blocking) | accept | uphold | instruction now fixes the granularity: each helper in terms.py keeps its present result for a setting the note gives no rule for, used where the note places the quantity |
| 2 | Negative slew three readings (blocking) | accept | uphold | resolved by #1 (helper result applied to w after the limits; first step u = w stated for every slew rate) |
| 3 | Integral timing for Ti<0 (should-fix) | accept | uphold | note 3: "Whatever the integral and tracking times, an automatic step adds to I only after its output has been formed" |
| 4 | Section 6 formula domain unclear (should-fix) | accept | uphold | "With a tracking time above nought, each automatic step adds ..." |
| 5 | Retune compensation for b outside [0,1] (should-fix) | accept | uphold | section 8 now uses "the proportional terms the controller computes with the old and with the new settings" |
| 6 | Weight range inclusivity (should-fix) | accept | uphold | "from nought to one, both included" |
| 7 | Period domain unstated (should-fix) | accept | uphold | note 1: "this note is written for a period above nought"; no test uses another period sign |
| 8 | Manual v cancellation (should-fix) | accept | uphold | section 7/9: I = m - P - D - f and v is m; test magnitudes kept away from cancellation |
| 9 | Commentary false on silent inputs (polish) | accept | uphold | both commentary sentences removed/softened |
| 10 | Instruction polish (figures, tolerance spelling, open-ended envelope) | accept | uphold | reworded; envelope now "settings outside the ranges some of the note's rules are written for"; tolerance given as math.isclose(...) |
| 11 | terms() before first step | accept (no change) | uphold | not tested; shipped {} stands |

## Recheck 1 (after repairs): all 11 closed; three polish items
- (b1) derivative first step for silent Td/N: instruction now says helpers keep results "from the inputs the controller feeds it today" — later superseded, see recheck 2.
- (b2) "raise no new exception, and add no clamp or guard" adopted.
- (b3) "setting value" adopted — later superseded.

## Strengthening after probe 1 (2/2) and recheck 2
Shipped pipeline now follows the note's order (v includes f; hold then slew), so the helper and pipeline readings coincide and the granularity sentence was removed from instruction.md. New cross-parameter trap: terms.hold returns `low` above `high` (departure), rule stated only for low < high.
Recheck 2 findings:
| # | Finding | Builder | Orchestrator | Action |
|---|---|---|---|---|
| a1 | first step with s<0: "which has no previous output" readable as unscoped (should-fix) | accept | uphold | clause now "or, on the first step, `w` itself" inside the s > 0 sentence |
| b1 | "`v` is then held within the limits." unscoped (should-fix) | accept | uphold | "For a low limit below the high limit, `v` is then held within the limits: ..." |
| a2 | suggest "keeping today's result outside a rule's range is not a guard" (borderline) | challenge | overrule | a branch that keeps a helper's present result restricts no input, so it is not a clamp or guard; reviewer itself classes the case as determinate. Not added |
