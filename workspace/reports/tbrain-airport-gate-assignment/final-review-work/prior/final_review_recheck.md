# Final review recheck: tbrain-airport-gate-assignment

Scope: I checked the refreshed packet against `prior/final_review.md` and `prior/final-review-adjudication.md`. I read only inside `final-review-work/` and edited nothing there. I ran both copies of `load_plan` on scratch files, reran the grader on the reference plans, and rechecked the day copies.

## Findings

1. **Resolved: the should-fix on `verification_explanation`.** `task.toml:15` now reads "keeps each day as a gzip-compressed copy of /app/days/<day>.json and fails if its SHA-256 or its stand, turn and transfer counts differ from a roster". This matches `tests/test_outputs.py:30-40`.

2. **Resolved: the advisory on "real" versus "synthetic".** `task.toml:13` now says "on a realistic apron layout".

3. **Resolved: the advisory on the byte-order mark.** `environment/app/docs/stand-rules.md:69` now says "no byte-order mark". Both copies of the checker refuse a file that starts with a BOM, with the message "Unexpected UTF-8 BOM".

4. **Should-fix: the new 4300-digit rule is broader than what the checker enforces.**
   - Citation: `environment/app/docs/stand-rules.md:69-70` ("no number of more than 4300 digits"); `tests/check_plan.py` and `environment/app/tools/check_plan.py`, `load_plan` (the `except (UnicodeDecodeError, ValueError)` clause).
   - The limit comes from Python's int-to-string conversion limit, so it applies only to integers. Both copies behave the same way:

     | Value in an ignored top-level key | Result |
     |---|---|
     | 4300-digit integer | accepted |
     | 4301-digit integer | refused |
     | `-` followed by 4300 digits | accepted |
     | `-` followed by 4301 digits | refused |
     | Float `1.` followed by 5000 digits | **accepted** |
     | 5000 integer digits followed by `.5` | **accepted** |
     | `1e` followed by a 5000-digit exponent | **accepted** |

   - So a file with a number of more than 4300 digits can still pass, which contradicts the stated rule. It has no effect on scoring, because numbers can only appear in ignored keys (a number in a stand list is already an unknown turn id). But it is exactly the kind of stated-but-not-enforced boundary the review checks for.
   - The integer case is also enforced only because the interpreter's default limit is 4300. The grader runs `python3 -I` (`tests/test.sh:15`), so the environment variable cannot change it there. The agent's copy of the tool, though, follows `PYTHONINTMAXSTRDIGITS`, and neither copy pins the limit.
   - Smallest fix: change the wording to "no integer of more than 4300 digits (a leading minus sign is not counted)". Optionally, call `sys.set_int_max_str_digits(4300)` in both copies so the limit does not depend on the interpreter's default.

5. **OK: the `ValueError` change is correct.**
   - The loader now catches `ValueError` instead of only `JSONDecodeError`. That covers `JSONDecodeError`, `UnicodeDecodeError` and the int-digit error.
   - It does not swallow `PlanError`. `PlanError` subclasses `Exception`, not `ValueError`, so the NaN and repeated-name hooks still raise their own messages.
   - Nothing else changed in a way that affects the checker. The two copies are still byte-identical.

6. **OK: no regressions elsewhere.**
   - `tests/targets.json` equals `environment/app/days/targets.json`.
   - Each gzip day copy decompresses to exactly the bytes of `/app/days/<day>.json`, and its SHA-256 matches the roster.
   - The reference plans cost 7439665, 9153275, 10331305 and 15767540, which equal the targets. The grader passes 8 of 8 tests on them.

## Verdict

accept with fixes
