# Adversarial verifier review: tbrain-bottling-line-lot-sizing

Scope: `instruction.md`, `environment/app/docs/production-rules.md`, `tests/test_outputs.py` and `tests/check_plan.py`. I did not look at the reference solution. `tests/check_plan.py` is byte-identical to `environment/app/tools/check_plan.py`. The `tests/sites/*.json` files and `targets.json` are identical to the copies in `/app`. The submissions are in `adversarial-work/submissions/`, built by `submissions/make.py`. Each one has a `WHY.txt`. I ran every validity test with the command given in the prompt.

## Results

| Submission | Site | Rule broken / why valid | Expected | Observed |
|---|---|---|---|---|
| w01_cap_ignores_setup | dorset | R3: 72 x COL01 on L1 d0 = 45+864 = 909 > 900. It only fits if setup is ignored | fail | fail (909 > 900) |
| w02_cap_edge_plus1_two_runs | dorset | R3: COL01x3 + BER08x17 on L1 d2 = 451 > 450. Each run fits alone; only the sum is over | fail | fail (451 > 450) |
| w03_capacity_zero_day | dorset | R3: L1 d6 has capacity 0 | fail | fail |
| w04_ineligible_line | dorset | R1: LEM02 on L3, which LEM02 does not list | fail | fail |
| w05_duplicate_run | kent | R2: two LEM02/L1/d0 runs | fail | fail |
| w06_zero_batches | kent | R1: batches 0 | fail | fail |
| w07_negative_batches | kent | R1: batches -1 | fail | fail |
| w08_float_batches | kent | Format: batches 2.0 | fail | fail |
| w09_bool_batches | fife | Format: batches true | fail | fail |
| w10_string_day | fife | Format: day "0" | fail | fail |
| w11_day_out_of_range | fife | R1: day 20 (days = 20) | fail | fail |
| w11b_negative_day | tyne | R1: day -1 (Python's negative-index wrap) | fail | fail |
| w12_unknown_product | fife | R1: "col01" (wrong case) | fail | fail |
| w12b_unknown_line | tyne | R1: "L1 " (trailing space) | fail | fail |
| w13_duplicate_key | tyne | Format: "batches" appears twice in one run | fail | fail |
| w13b_dup_top_runs | kent | Format: "runs" appears twice at top level. The second copy would hide an illegal capacity-0 run | fail | fail |
| w14_bom | tyne | Format: UTF-8 BOM in front of the valid lot-for-lot plan | fail | fail |
| w14b_nan_extra | kent | Format: NaN in an ignored extra key | fail | fail |
| w14c_depth65 | fife | Format: 65 nesting levels | fail | fail |
| w14d_digits4301 | dorset | Format: 4301-digit integer in an ignored key | fail | fail |
| w14e_float_digits | kent | Format: 4302-digit float (fraction digits counted) | fail | fail |
| w14f_size | kent | Format: 2,000,001 bytes (valid plan padded) | fail | fail |
| w15_runs_not_list | dorset | Format: runs is an object | fail | fail |
| w15b_top_list | kent | Format: top level is a list | fail | fail |
| w15c_missing_key | fife | Format: run has no batches | fail | fail |
| v01_edges_extra_keys | dorset | VALID: L1 d0 at 897/900, L2 d0 at 894/900, L1 d2 exactly 450/450 counting setups; COL01 on L1 and L2 on the same day; extra keys at top level and inside runs; runs in reverse order; 4300-digit integer; 64 levels deep; float in an extra key | pass | pass |
| v02_empty_runs | tyne | VALID: `{"runs": []}` with surrounding whitespace (all backlog) | pass | pass |
| v03_lfl_all | all 4 | VALID: output of the shipped lot-for-lot planner | pass | pass x4 |
| v04_minus_zero_day_unicode | fife | VALID: day `-0`, line id written as a `\u` escape, non-ASCII extra key | pass | pass |
| v05_boundaries | kent | VALID: exactly 2,000,000 bytes, a float with exactly 4300 digits | pass | pass |

Cost cross-check: I wrote a separate cost function straight from the "Stock and cost" section (`submissions/indep_cost.py`). It gives the same cost as `evaluate` on all 7 valid plan files (for example lot-for-lot plans dorset 302907, kent 502671, fife 456116, tyne 634374, and an empty tyne plan 2162494). Stock arithmetic, backlog costs, holding costs and one setup cost per run all match the rules.

## Findings

No wrong submission passed its validity test, and no valid alternative failed. The grader matches the rules document on every edge I tried:
- capacity counts setup minutes and sums across products, with `<=` at the exact edge
- days with capacity 0
- line eligibility
- duplicate runs
- type checks that reject bool, float and string values
- day range, including negative days
- exact-match ids
- duplicate JSON names at every level
- the BOM, NaN, depth, digit and size limits, each at the boundary itself and one past it
- extra keys are ignored, and run order does not matter

Non-blocking notes (no fix needed):
1. `check_plan.py` calls `sys.set_int_max_str_digits(4300)` at import, which changes the whole process. It has no effect in practice, because `_digits` enforces the same limit first.
2. The kent and fife targets are both 150000, which looks like a placeholder. The prompt says targets are provisional and I did not judge whether they can be reached. They should be replaced with the certified best-found costs before submission.

## Verdict

accept. The grading logic is sound. The only open item is the provisional kent and fife targets, which were out of scope for this review.
