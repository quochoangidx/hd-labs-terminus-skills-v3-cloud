# Final review: tbrain-airport-gate-assignment

Scope: I read `instruction.md`, `task.toml`, `environment/`, `tests/`, `solution/` and `prior/`, and I ran the checker and the grader (pytest with `STAND_PLANS` pointed at scratch plan sets). I did not edit any file.

## Findings

1. **Resolved (no action): the earlier contract findings were fixed as the adjudication says.**
   - Duplicate names: `environment/app/tools/check_plan.py:23-29` (`_no_repeats` passed as `object_pairs_hook`, line 49) now rejects a name that appears twice in one object, and `environment/app/docs/stand-rules.md:70-71` states the rule for every object. The old "given at most once" wording is gone. In my run, a file with a repeated `"stands"` key failed its validity test.
   - Diagonal and remote walking charges: `stand-rules.md:55-58` now says the diagonal entry is charged and is not zero, and that remote walking entries are charged on top of the bus charge. This matches `check_plan.py:104-112`. All four days have non-zero diagonals.
   - Adversarial findings: NaN and Infinity are rejected (`check_plan.py:19-20,49`; stated at `stand-rules.md:69`). The 2,000,000-byte limit is stated (`stand-rules.md:69-70`) and enforced (`check_plan.py:44`). In my run a NaN file failed, a file of 2,000,001 bytes or more failed, and a file of exactly 2,000,000 bytes passed.

2. **Should-fix: `verification_explanation` describes a day storage the verifier does not use.**
   - Citation: `task.toml:15` ("keeps each day in small files with a roster of counts and a checksum and fails if they do not reassemble exactly"), compared with `tests/test_outputs.py:30-40` and `tests/days/`.
   - The verifier stores each day as one gzip file (`tests/days/day-N.json.gz`). It checks the file against `roster.json` (SHA-256 plus the stand, turn and transfer counts). Nothing is split and nothing is reassembled.
   - Smallest fix: "The verifier keeps each day as a gzip-compressed copy of `/app/days/<day>.json` and fails if its SHA-256 or its stand, turn and transfer counts differ from a roster."

3. **Advisory: `difficulty_explanation` contradicts itself about the data.**
   - Citation: `task.toml:13`. It opens with "on a real apron layout" and later says "The days are synthetic but modelled on a three-pier terminal".
   - Smallest fix: change "on a real apron layout" to "on a realistic apron layout" (or "a three-pier apron layout").

4. **Advisory: a UTF-8 byte-order mark is rejected, and the rules do not say so explicitly.**
   - Citation: `environment/app/docs/stand-rules.md:69`; `check_plan.py:49` (`json.loads` on a str that starts with U+FEFF raises "Unexpected UTF-8 BOM").
   - RFC 8259 says JSON text must not start with a BOM, so "standard JSON in UTF-8" arguably covers this already. Agents writing with Python's `json.dump` will never produce one.
   - Smallest fix (optional): add "with no byte-order mark" to line 69.

5. **OK: the contract matches the grader.**
   - Every check in `check_plan.py:58-100` is stated in the rules with the same boundaries:
     - size ≤ stand size;
     - international turns only on international stands;
     - same-stand gap is `depart + buffer <= arrive`: a turn arriving at 25 after a departure at 10 with a 15-minute buffer is valid, and one arriving at 24 is not;
     - wingtip pairs use a strict half-open overlap with no buffer, and only size-3 turns clash: an arrival at the other's departure minute is valid, one minute earlier is not;
     - unknown stand or turn ids, non-string ids, a turn placed twice and a missing turn are all rejected;
     - extra top-level keys are ignored, and a stand may be omitted or given an empty list.
   - File-format rules are stated with the same boundaries: at most 2,000,000 bytes; UTF-8; no NaN or Infinity; no repeated names; depth at most 64 counting the top-level object. A file nested exactly 64 levels deep passed and one nested 65 levels failed.
   - I found no rule that is stated but not enforced.

6. **OK: the grader's copies match the agent's.**
   - `tests/check_plan.py` is byte-identical to `environment/app/tools/check_plan.py`.
   - `tests/targets.json` equals `environment/app/days/targets.json`.
   - Each `tests/days/day-N.json.gz` decompresses to exactly the bytes of `environment/app/days/day-N.json`, its SHA-256 matches `roster.json`, and the stand, turn and transfer counts (31/180/715, 42/240/1007, 52/300/1192, 63/360/1413) match.

7. **OK: the reference passes exactly on target.**
   - The checker gives the reference plans costs of 7439665, 9153275, 10331305 and 15767540, which equal `tests/targets.json`. The grader passes 8 of 8 tests on them.
   - The shipped planner's costs (9077225, 12189855, 14519325, 21326260; 22.0 to 40.5 percent over target) match `task.toml:13,15`.

8. **OK: the grader rejects wrong work and accepts valid work.** Results from running the grader on each case:

   | Case | Result |
   |---|---|
   | Reference plans | 8/8 pass |
   | Shipped planner's plans | 4 fail, all target tests |
   | Reversed stand and item order plus an extra top-level key | 8/8 pass |
   | Missing day-1 file | both day-1 tests fail |
   | One turn dropped | both day-1 tests fail |
   | Size-3 turn on a small stand | both day-1 tests fail |
   | Repeated name | both day-1 tests fail |
   | NaN | both day-1 tests fail |
   | File over 2 MB | both day-1 tests fail |
   | Nested 65 levels | both day-1 tests fail |
   | Valid day-1 plan above target | only the day-1 target test fails |

   The grader reads only `/app/plans/*.json` as data (`test_outputs.py:43-50`) and uses its own checker, days and targets. Editing anything else under `/app` cannot change the grade.

9. **OK: grading is deterministic and isolated.**
   - Nothing depends on time, randomness, the network or test order.
   - `test.sh` runs `python3 -I` from a temporary directory with `-p no:randomly`.
   - The verifier environment is separate and has no network (`task.toml`), and no `/app` code runs.
   - The test and reference dependencies are pinned in `tests/Dockerfile` and are not in the agent's image.

10. **OK: the instruction matches the environment.**
    - All paths named in `instruction.md` exist.
    - `/app/plans` is created by the image.
    - Python is 3.13 (`environment/Dockerfile:1`).
    - The category and subcategory (Operations / Logistics) fit the task.
    - `solution/solve.sh` copies the plans and runs the checker. Its description of the annealing matches `solution_explanation`.

## Verdict

accept with fixes
