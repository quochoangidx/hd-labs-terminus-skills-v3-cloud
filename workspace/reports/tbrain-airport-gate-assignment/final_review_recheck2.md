# Final review recheck 2: tbrain-airport-gate-assignment

Scope: I checked the refreshed packet against the "Recheck" section at the end of `prior/final-review-adjudication.md`. I read only inside `final-review-work/` and edited nothing there. I ran both copies of `load_plan` on scratch files, with `PYTHONINTMAXSTRDIGITS=0` set to confirm the environment variable does not change the result. I also reran the grader and the checker on the reference plans.

## Findings

1. **Resolved: the 4300-digit sentence now matches both checkers.**
   - Citation: `environment/app/docs/stand-rules.md` (File format: "no number in it may be written with more than 4300 digits (counting every digit, including those after a decimal point or in an exponent)"); `_digits`, `_int` and `_float` passed to `json.loads` as `parse_int` and `parse_float` in `tests/check_plan.py` and `environment/app/tools/check_plan.py`.
   - I tested seven forms in both copies: integer, negative integer, fraction, negative fraction, exponent, negative exponent with an uppercase `E`, and mixed integer, fraction and `e+` exponent.
   - Each form with exactly 4300 digits is accepted. Each form with 4301 digits is refused with "a number is written with more than 4300 digits".
   - The sign, the decimal point and the exponent marker are not counted, which agrees with "counting every digit".
   - A 5000-digit number inside a stand list is also refused with the same message.
   - `sys.set_int_max_str_digits(4300)` is pinned, and results did not change with `PYTHONINTMAXSTRDIGITS=0`. It is redundant in practice, because `_digits` runs before `int()` so Python's own limit is never reached, but it is harmless.

2. **OK: the copies are byte-identical.** `diff tests/check_plan.py environment/app/tools/check_plan.py` shows no difference.

3. **OK: the rest of the changed lines are correct.**
   - The hooks raise `PlanError`, which is not a `ValueError`, so it passes straight out of `json.loads` with its own message rather than being wrapped as "not valid JSON".
   - BOM, NaN, Infinity, repeated-name and depth handling are unchanged.
   - The rules now state the digit limit as its own rule next to the byte limit, and no longer present it as part of "standard JSON".
   - `task.toml` still says only "standard JSON within the stated limits", which remains accurate.

4. **OK: no regressions.**
   - Targets are identical in both copies.
   - All four gzip day copies decompress to exactly the bytes of `/app/days/<day>.json`, and each SHA-256 matches the roster.
   - The reference plans cost 7439665, 9153275, 10331305 and 15767540, which equal the targets, and the grader passes 8 of 8 tests on them.

5. **Advisory (cosmetic):** one line in the File format paragraph of `stand-rules.md` ("...those after a decimal point or in an exponent). No object in it may give the same name twice, and") is much longer than its neighbours. Rewrapping the paragraph would fix it. It does not affect correctness.

## Verdict

accept
