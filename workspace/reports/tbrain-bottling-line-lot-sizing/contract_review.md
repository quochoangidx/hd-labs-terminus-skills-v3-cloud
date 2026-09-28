# Contract review: tbrain-bottling-line-lot-sizing

Scope: `instruction.md` and `environment/` only. I did not look at tests or the reference solution. All paths below are relative to `contract-review-work/`.

## Method

- Compared `environment/app/docs/production-rules.md` (rules) with `environment/app/tools/check_plan.py` (checker) clause by clause.
- Wrote an evaluator from the rules text alone (scratch, `/private/tmp/claude-501/lotsize-review/indep.py`). Ran it against `check_plan.evaluate` on 6,000 random plans over the four sites (278 valid, the rest invalid for mixed reasons). There were 0 disagreements in verdict or cost.
- Worked out 31 hand witnesses (listed below) and ran each one through `tools/check_plan.py`. All 31 agree.
- Ran the shipped planner on every site. Every plan it produces is valid: dorset 302,907, kent 502,671, fife 456,116, tyne 634,374. The empty plan for each site is valid and costs 1,473,137, 1,675,501, 2,100,406 and 2,162,494 respectively.

## Rule-by-rule comparison (item 1)

| Topic | Rules | Checker | Match |
|---|---|---|---|
| Run shape and types | rules:61-65: `day` and `batches` are JSON ints (not strings, floats or bools); `line` and `product` are strings; other keys are ignored | check_plan.py:89-91 (`type(x) is int` rejects bool; float and str are rejected) | yes |
| Known day, line and product | rules:29-30 | :92-97 | yes |
| Eligibility | rules:29-30 ("the product lists that line") | :98-100 | yes |
| At least one batch | rules:30 | :101-102 | yes |
| Duplicate (day, line, product) | rules:31 | :103-105. Only the triple counts, so the same product on two lines on one day is allowed | yes |
| Capacity and setup minutes | rules:32-36. Setup plus batches times minutes per batch, summed over each line and day, must be no more than the capacity; every run pays its own setup | :106, :109-111 | yes |
| Stock recursion, same-day ship, backlog | rules:42-46 | :112-115 | yes |
| Cost terms | rules:48-55: setup_cost per run, plus holding or backlog on end-of-day stock, every day | :108, :116 | yes |
| `family` and `name` unused | rules:14-15 | not read | yes |
| Top-level shape | rules:61 | :77-78 | yes |
| UTF-8, BOM, NaN/Infinity | rules:67-68 | :65-68, :21-22 | yes |
| At most 2,000,000 bytes | rules:68-69 | :60-61 (`>`) | yes |
| At most 4300 digits, counting fraction and exponent | rules:69-70 | :25-36 counts `isdigit` over the whole token | yes |
| No repeated names | rules:70-71 | :39-45 | yes |
| Depth of 64 or less, top level counts as 1 | rules:71-72 | :48-55, :69-70 | yes |

The checker enforces nothing that the rules leave out, and the rules state nothing that the checker ignores.

## Hand witnesses (item 3)

All of these were computed from the rules text and then checked with `tools/check_plan.py`. There were no disagreements.

1. dorset, day 2, L1 (capacity 450), COL01 × 33: 45 + 396 = 441 minutes, so valid. COL01's backlog falls from 2,193 to 1,596 batch-days (plus 14 + 7 held on days 2-3, and days 0-1 unchanged at 400 + 560). The cost is 1,473,137 − 87,720 + 64,842 + 200 = **1,450,459**. Checker: valid, 1,450,459.
2. The same run with 34 batches needs 453 > 450 minutes, so invalid. Checker: invalid.
3. dorset, day 6 (all lines at 0), L1 COL01 × 1 needs 57 > 0 minutes, so invalid. Checker: invalid.
4. dorset day 0 L1: COL01 × 20 (285) plus LEM02 × 27 (606) = 891 ≤ 900, so valid. With LEM02 × 28 the total is 909, so invalid. Checker agrees on both.
5. Two runs of (0, L1, COL01) × 1 are invalid even though 114 minutes would fit. Checker: invalid.
6. COL01 × 1 on L1 plus COL01 × 1 on L2, both day 0, is valid. Cost is +500 in setups; backlog falls by 2 on every one of 20 days × 40 = −1,600. Result 1,472,037. Checker: 1,472,037.
7. LEM02 on L2 (not in its `lines`) is invalid. `batches` of 0, true, 1.0, "1" or −1 are all invalid. Checker agrees on all six.
8. dorset, day 19, L1 COL01 × 20 (same-day shipping on the last day) only changes day 19's backlog, from 220 to 200. The cost is 1,473,137 − 800 + 200 = **1,472,537**. Checker agrees.
9. kent, day 19, L3 COL01 × 70 (30 + 840 = 870 ≤ 1,020): the backlog of 65 is paid back and 5 are held. The cost is 1,675,501 − 2,600 + 15 + 200 = **1,673,116**. Checker agrees.
10. tyne L2 is down on day 1, so ORA03 × 1 there is invalid. On day 19 L2 has 450 minutes: × 35 = 30 + 420 is valid (cost 2,159,294) and × 36 = 462 is invalid. Checker agrees.
11. File format:
    - An extra top-level key and an extra key inside a run are ignored (same cost as witness 8).
    - A repeated `day` key is invalid.
    - A BOM is invalid.
    - Depth 64 is valid and depth 65 is invalid.
    - `NaN` is invalid.
    - A 4,300-digit int is valid and a 4,301-digit int is invalid. `1.` followed by 4,299 zeros is valid.
    - A file just under 2 MB is valid and one over 2 MB is invalid.
    - A top-level list is invalid, and a non-object run is invalid.

    The checker agrees on all of these.

## Findings

1. **Blocking (precondition).** `environment/app/sites/targets.json` does not exist, but `instruction.md:1` and `environment/app/README.md:3` both refer to it. The task cannot be graded or attempted until it ships. Fix: add it with one integer per site, keyed `dorset`, `kent`, `fife`, `tyne`, and make sure the grader's copy is byte-identical. I could not assess whether the targets are achievable, because they are absent.
2. **Should-fix.** The targets are defined as "the cost of the best plan the planning office has found" (`instruction.md:1`), and the solver may only use the Python 3.13 standard library (`instruction.md:3`), which means no MILP solver. If a target comes from an exact solver or a long search, a stdlib local search may not be able to reach it with zero slack. Fix: confirm that every target is reachable within the agent timeout by a stdlib-only method, such as the reference solution run under the same constraints. Alternatively, set each target to that method's cost, or add a stated tolerance.
3. **Should-fix (minor).** `docs/production-rules.md:8` says "Each file in `sites/` is one bottling site", but `targets.json` will also sit in `sites/` (`README.md:3`). A solver that globs `sites/*.json` will try to load it as a site. Fix: change the sentence to "Each site file in `sites/` (`dorset.json`, ...)" or move `targets.json` out of `sites/`.
4. **Advisory.** `instruction.md:1` says the current planner's plans "pay for a changeover on almost every run". Under the rules every run pays its setup (`production-rules.md:35-36`), so "almost" hints that setups might carry over. Fix: "pay for a changeover on nearly every product nearly every day", or simply "run many small lots".
5. **Advisory.** `instruction.md:1` says the planner "fills exactly what that day is short of on the first line with room". The planner actually fills as much as fits on the first line with room and then spills onto later lines (`planner/plan_site.py:23-32`). This is harmless but slightly inaccurate. Fix: "...on the first of its lines with room, spilling onto the next".
6. **Advisory (no change needed).** Several edge cases are decided in the text and behave as documented:
   - End of horizon: there is no terminal penalty (`production-rules.md:50-55`, "Nothing else is charged"). Leaving late-horizon demand unfilled can therefore be optimal, and the checker behaves this way (witness 8).
   - Same-day shipping: stated at :44-45.
   - Backlog carry and payback: stated at :45-46.
   - Days with capacity 0: stated at :12. Every setup in the data is at least 30 minutes, so no run fits on those days.
   - Zero-batch runs: stated at :30.
   - Initial stock: stated at :15 and :43.
7. **Advisory.** `tools/check_plan.py:127` does not catch a missing plan file, so it produces a traceback instead of `invalid:`. It also exits with the traceback status rather than 1. This only matters if the grader relies on the checker's exit code or output format for a missing `/app/plans/<site>.json`. Fix (optional): catch `OSError` in `load_plan` and raise `PlanError`.
8. **Advisory.** A lone-surrogate escape (`"\ud800"`) and an overflowing float (`1e400`) are accepted in ignored keys. Both are allowed by the JSON grammar and affect no field that is scored. No change needed.

### Environment and instruction consistency (item 4)

- The paths line up. `/app/sites/{dorset,kent,fife,tyne}.json` exist. `/app/plans/` is created by `Dockerfile:7`. The image is Python 3.13 (`Dockerfile:1`), which matches `instruction.md:3`.
- Every site has `days` = 20 and demand lists of length 20.
- The goal is achievable in principle: the shipped planner's plans are valid on all four sites. The targets are presumably well below the planner's costs.

### Shortcuts and misleading content (item 5)

- The grader uses its own `check_plan.py`, sites and targets, so editing `/app/tools`, `/app/sites` or `targets.json` gains nothing.
- The empty plan is valid, but it costs 3-5 times the planner's cost, so it cannot pass a sensible target.
- I found no leaked reference plans or target-derivation hints.
- The only potentially misleading items are Findings 3-5.

## Verdict

accept with fixes. Ship `targets.json` (Finding 1) and confirm that the targets can be reached with the standard library alone (Finding 2). The rules document and checker agree exactly.
