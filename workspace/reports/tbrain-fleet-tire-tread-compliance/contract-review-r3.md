# Contract review r3 — tbrain-fleet-tire-tread-compliance (reviewer C)

Scope: packet r3 (`instruction.md` + `environment/`). The driver is byte-identical to r2.

What changed since r2:
- All tires are mounted new, so the "fresh" and "measurement" concepts are gone. Every reading shows 10–320 and every reading gets the offset.
- Drive/trailer removal depth is now 30.
- There are two new output keys, `km_left` and `regroove`. The standard does not mention either; only today's code (`wear.km_left`, `status.regroove`) defines them.

## Part 1 — Contract review

### Status of r2 findings
- The wear-bar and non-fresh traps are **gone (moot)**. The concepts no longer exist.
- The first-reading cap is **still in place** (§1.5).
- A negative worn figure is **still possible**, because later readings are not capped at `new_depth`. The rate rounds half-up. `km_left` is then 0 through today's `rate <= 0` branch.

### Findings

1. **blocking — rounding of `km_left`.** §1.1: "When a rule divides a figure, the result is rounded ... an exact half goes up". `km_left` is a division, but it is not a division by "a rule" of the standard. Under the instruction's paragraph 2 it is "worked out as today's code works it out", which is `round()`, i.e. banker's rounding. But `km_left` and `rate` both go through the same `rounding.divide`. A solver who fixes that helper to half-up changes `km_left` too. And a competent reader can take §1.1 as the shop-wide unit convention (distance "kept in whole kilometres", "rounded to the nearest whole unit it is kept in") and apply it to every km figure. Two readings, two values:
   - Counterexample: drive, new 63, mounted 0, readings (5000 km, 60) and (10000 km, 31), offset 0. Worn 32, distance 10000, rate 32. `km_left` = 1×10000/32 = 312.5, which gives **312** (banker's, today's code) or **313** (half-up).
   - Pulled variant: latest 27, same rate. −937.5 gives **−938** (banker's) or **−937** (half-up).

   This fails the 0/8 screen as a trap: §1.1 reads as a positive, general convention, and expert instinct points to half-up. It is a contract defect. Fix: say explicitly whether §1.1 reaches `km_left`, or give `km_left` its own rule.
2. **blocking/should-fix — regroove threshold.** Today's code is `latest >= REMOVAL + REGROOVE_MARGIN`, which uses the module constant `REMOVAL` (32), not `removal_depth(position)`. The comment reads "tenths of tread a regroove needs above the removal depth". The two readings:
   - A: the input is the removal depth, which §2.2 settles at 30, so the threshold is **50**. This is the "inputs which the standard does settle take the standard's values" clause.
   - B: `REMOVAL` is "the package's own constant at its present value", so the threshold is **52**.

   Counterexample: a drive tire with latest 50 or 51 gives regroove **true** (A) or **false** (B). The result also depends on implementation accident. A solver who edits `REMOVAL = 30` gets A. A solver who leaves `REMOVAL` alone and hard-codes 30/40 inside `removal_depth` gets B. I lean A, but the text does not force it, because nothing in the standard names regrooving. Fix: one sentence stating whether the regrooving check's reference is the §2.2 removal depth.
3. **OK — `km_left` inputs.** `latest` (§4.1), the limit (§2.2 via `removal_depth`) and `rate` (§4.3, rounded half-up) are all settled, so the inputs are unique. The `rate <= 0 → 0` branch is today's code and has to stay. Adding any other guard (e.g. clamping negatives for pulled tires) is barred by "Add no exception, clamp or guard".
4. **polish — steer regroove.** Always false (a labelled code branch). Unique.
5. **OK — everything else.** Rounding for `rate`, ranges, status, retread and ordering are all clean.

### Per-output-figure determinacy

| key | source | uniquely determined? |
|---|---|---|
| tire, position | given | yes |
| latest | §3.1/§4.1 (shown + offset) | yes |
| worn | §4.2 new − latest | yes (can be negative) |
| distance | §4.2 latest odometer − mounted_km | yes |
| rate | §4.3 + §1.1 half-up | yes |
| status | §2.2 + §5.1 | yes |
| retread | §6.1 (pull only, age < 2190 days, retreads < 2) | yes |
| km_left | today's code with standard inputs | **no**: rounding of halves (finding 1) |
| regroove | today's code with standard inputs | **no**: threshold 50 vs 52 at latest 50–51 (finding 2) |

### Witnesses (hand-worked)
- W1 sample (steer): latest 91, worn 85, distance 67812, rate 13 (12.53), in service, retread false, km_left 510000/13 = 39230.77 → 39231, regroove false.
- W2 rate half: new 100, mount 0, latest 99 at 4000 km → worn 1, 2.5 → **3** (today's code gives 2). At 20000 km: 0.5 → **1** (today's code gives 0).
- W3 drive/trailer removal boundaries: latest 30 → pull; 31 → watch; 46 → watch; 47 → in service. Steer: 40 → pull, 56 → watch, 57 → in service.
- W4 regroove, drive or trailer: latest 49 → false; 50 and 51 → **true under A / false under B** (guess); 52 → true. Steer 200 → false.
- W5 km_left half (finding 1): rate 32, latest 31, drive → 312 or 313 (guess). Watch, regroove false.
- W6 km_left pulled half: rate 32, latest 27 → −938 or −937 (guess). Pull.
- W7 km_left non-half: rate 32, latest 33 → 937.5 → 938 under either rounding (banker's rounds to the even 938). Rate 20, latest 34 drive → 4×10000/20 = 2000.
- W8 negative worn: new 60, first 60, latest 62 at distance 40000 → worn −2, rate −0.5 → 0 (half up to the larger), km_left 0 via `rate <= 0`.
- W9 retread: pulled, retreads 1, casing age 2189 days → true; 2190 days → false; retreads 2 → false; watch → false.

## Part 2 — Solver-path screen

A) A strong solver fixes the offsets, removal depths 40/30, `<=` for pull and watch, day-based retread with `<`, half-up rounding and new − latest from mounting. `km_left` and `regroove` then change silently through the shared helper and constants. Most solvers will patch `rounding.divide` once, so `km_left` becomes half-up. For regroove, results split on whether they edit `REMOVAL`. The solver's own tests encode its own reading, so it cannot detect the split. Failures here come from the unresolved contract, not from genuine difficulty.

B) Scores:
- reference_unreachable: 2
- authority_incomplete_for_grading: **4** (two ungoverned figures with split readings; this is a defect)
- hidden_state_not_closed_form: 1
- restraint_traps: 1. The km_left rounding and regroove sites fail the 0/8 screen and are counted as defects, not points. The `rate <= 0` branch is a written guard that is kept.
- fuzz_blind_spot: 2

C) self_verification_resistance: 2. Prediction: **resists, for illegitimate reasons.** At least one solver likely misses on `km_left` halves or on regroove at 50/51; otherwise the task collapses. Confidence: medium. decisive_reason: `km_left` rounding and the regroove threshold each have two defensible values that the standard does not settle and today's code does not pin down against the fixed standard inputs, so outcomes hinge on the grader's choice rather than on skill.
