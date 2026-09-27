# Final review recheck 3: tbrain-airport-gate-assignment

Scope: I checked the refreshed packet after the targets were strengthened. I read only inside `final-review-work/` and edited nothing there. I ran the checker on each reference plan, ran the shipped planner in memory to recompute the baseline costs, reran the grader on `solution/plans`, and rechecked the day copies.

## Findings

1. **OK: each reference plan is valid and costs exactly its new target.**
   - `tests/check_plan.py` gives the reference plans these costs:

     | Day | Reference cost | Target in `tests/targets.json` |
     |---|---:|---:|
     | day-1 | 7241380 | 7241380 |
     | day-2 | 9017700 | 9017700 |
     | day-3 | 10098740 | 10098740 |
     | day-4 | 15505590 | 15505590 |

   - Each plan has only the `stands` key.
   - The grader (`python3 -I -m pytest tests/test_outputs.py` with `STAND_PLANS=solution/plans`) passes 8 of 8 tests.
   - The new targets are 2.67, 1.48, 2.25 and 1.66 percent below the previous ones. That is consistent with a stronger search, and none is below a plan that exists.

2. **OK: the two targets files agree.** `tests/targets.json` and `environment/app/days/targets.json` are identical.

3. **OK: the `task.toml` numbers match the files.**
   - `verification_explanation` (`task.toml:15`) gives shipped-planner costs of 9077225, 12189855, 14519325 and 21326260. My recomputation from `planner/plan_day.py` gives the same values, and the new targets listed there match `targets.json`.
   - `difficulty_explanation` (`task.toml:13`) says "25-44 percent over target". The actual overshoots are 25.35, 35.18, 43.77 and 37.54 percent, so the range rounds correctly.
   - The counts (180-360 turns on 31-63 stands) are unchanged and still correct.

4. **OK: the method text is consistent between `solve.sh` and `task.toml`.**
   - The `solve.sh` header (lines 4-12) and `solution_explanation` (`task.toml:14`) describe the same method, and both say each target is the cheapest plan seen:
     - incremental cost updates;
     - a move-with-bump-back move;
     - a stand-exchange move over a growing time window;
     - restarts from the best plan, pooled with the best plans from trial runs;
     - temperature falling from 30000-60000 to 10-30 over 20-60 minutes, with several seeds per day.
   - The earlier four-move description has been replaced in both places, so no stale method text remains.
   - `solve.sh` still just copies the plans and runs the checker.
   - The method details (moves, temperatures, run times) cannot be verified from the files, but nothing in the packet contradicts them.

5. **Advisory: one difficulty claim cannot be checked from the packet.**
   - Citation: `task.toml:13`, which says "the last half to one percent needs a well-tuned search ... run for most of the time available".
   - This is a qualitative claim, and the packet contains no trial evidence for it. It is fine if the builder's trial data supports it.
   - Smallest fix (optional): keep it only if the trial results bear it out; otherwise soften it to "the targets sit below what short or single-move searches reach".

6. **OK: no regressions elsewhere.**
   - `tests/check_plan.py` and `environment/app/tools/check_plan.py` are byte-identical.
   - All four gzip day copies decompress to exactly the bytes of `/app/days/<day>.json`, and each SHA-256 matches `roster.json`. The day files did not change.
   - The file-format paragraph in `stand-rules.md` has been rewrapped with its wording unchanged, which resolves the cosmetic advisory from recheck 2.
   - `instruction.md` is unchanged and still accurate, since it does not quote target values.

## Verdict

accept
