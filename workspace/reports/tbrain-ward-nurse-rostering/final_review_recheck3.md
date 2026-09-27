# Final review, third recheck: tbrain-ward-nurse-rostering

This is a targeted recheck after the targets were strengthened. I read only files inside the working directory and edited no task file. Scratch files went to the session scratchpad. See finding 1 for a cache directory my own test runs created in the packet.

## Checks

- **Each reference roster is valid and scores exactly its new target.** I ran `tests/check_roster.py` against `tests/wards/<ward>.json`:

  | Ward | Reference penalty | `tests/targets.json` | `environment/app/wards/targets.json` |
  |---|---|---|---|
  | ash | valid, 440 | 440 | 440 |
  | birch | valid, 1070 | 1070 | 1070 |
  | cedar | valid, 820 | 820 | 820 |
  | dale | valid, 1650 | 1650 | 1650 |

  - Each reference file is an object with only a `roster` key and one row per nurse: 16, 22, 28 and 36 nurses.
  - The grader suite on `solution/rosters` passes 8/8.
- **The two targets files agree.** `cmp` finds them byte-identical.
- **The grader copies are still identical to the agent's.** `tests/check_roster.py` matches `environment/app/tools/check_roster.py`, and the four ward files in `tests/wards/` match `environment/app/wards/`.
- **The shipped planner is unchanged.** It still produces valid rosters scoring 5313, 12003, 9002 and 12287, all above target.
- **`task.toml` is accurate against the files.**
  - `verification_explanation` (line 15): the planner scores 5313/12003/9002/12287 and the targets 440/1070/820/1650 both match. "The reference rosters sit exactly on the targets" holds.
  - `difficulty_explanation` (line 13): "7-12 times the target" holds. The ratios are 12.07x, 11.22x, 10.98x and 7.45x; ash at 12.07 rounds to 12. "16-36 nurses" holds.
    - "Pooled with the best rosters from trial runs" and "a short search stops above at least one of them" are statements about how the targets were made. No file can confirm them, but they are hedged and nothing contradicts them.
  - `solution_explanation` (line 14): the move set and "one to four hours" agree with the `solve.sh` comment. "Several seeds" no longer carries the old unsupported "40-minute". "Each target is the penalty of the cheapest roster seen" agrees with the reference rosters sitting exactly on target.
- **The `solve.sh` header is accurate.** Lines 9-12 add the pooling sentence consistently with `task.toml`. The script body is unchanged: it copies the rosters and runs the checker, which exits 0 on each reference.
- **Nothing else regressed.**
  - The file-format paragraph of `roster-rules.md` (lines 71-80) is rewrapped with the same words. The digit, byte-order-mark, byte, repeated-name and depth rules still read as in recheck 2.
  - `instruction.md` is unchanged; it points to the targets file and states no numbers.
  - The only file changes since `prior/final_review.md` are the ones listed in the brief, plus finding 1.

## Findings

1. **Should-fix (packaging, caused by this review): remove `tests/__pycache__/` before packaging.**
   - Location: `tests/__pycache__/check_roster.cpython-313.pyc` and `tests/__pycache__/test_outputs.cpython-313-pytest-9.1.1.pyc`, both dated 2026-09-26 13:49.
   - My own grader runs created these files when they imported the test module in place. `-p no:cacheprovider` does not stop Python writing bytecode.
   - `tests/Dockerfile` runs `COPY . /tests/`, and `tests/` has no `.dockerignore`. The files would therefore ship in the verifier image and in a ZIP of the packet.
   - They are harmless to grading, but they are hygiene debris a platform reviewer or the ZIP validator would flag.
   - I did not delete them, because this recheck is edit-nothing.
   - **Smallest fix:** `rm -rf tests/__pycache__` in the source task before zipping.
2. **Advisory: the rewrap dropped the final newline.**
   - Location: `environment/app/docs/roster-rules.md:80`.
   - The file now ends with `level.` and no trailing newline (`tail -c1` gives `2e`). Earlier snapshots ended with a newline.
   - This is cosmetic.
   - **Smallest fix:** add a final newline.

## Verdict

accept (after removing `tests/__pycache__/` from the source task before packaging)
