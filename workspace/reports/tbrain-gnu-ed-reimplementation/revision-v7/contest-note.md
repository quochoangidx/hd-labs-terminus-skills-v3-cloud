Task fc57838e-86e3-431c-a65c-b8776a1f307e (tbrain-gnu-ed-reimplementation), evaluation 7: five findings contested

Finding 12 (Correct Reference Solution, Major): "The bracket-expression parser treats a first-position hyphen as a range operator."
- The finding's own scripts, run on a file holding `.` with regular-file stdin through `/usr/bin/ed` (GNU ed 1.19) and the submitted reference in the verifier image:
  - `g/[-a]/p` then `Q`: both print `2\n` and exit 0.
  - `s/[-a]/X/` then `Q`: both print `2\n?\n` and exit 1.
- `bracket()` consumes the leading `-` as an item before it looks for a range, so `.` is never in the set. This is the second round with the same claim; the graded cases `[-a]` and `[a-]` stay.
- Receipt: revision-v7/receipts/returned/reference-findings-12-13-14.json

Findings 15 (Correct Reference Solution, Major) and 24 (Sound Verifier, Major): the cut-buffer content after a successful s.
- Both scripts observe the cut buffer through `x` (`s/foo/bar/` then `x`, or `0x`). The instruction says: "The commands `l`, `z`, `x`, `y`, `G`, `V`, `P`, `h`, `H` and `!`, and the `l` suffix, never appear in a script."
- Without `x` and `y`, no contract-valid script can observe the cut buffer, so its content after s is outside what the task grades. The verifier's own domain check (tests/scope.py) rejects both scripts.
- Receipt: revision-v7/receipts/returned/cut-buffer-scripts-out-of-domain.json

Finding 9 (Coherent Contract, Major): "generated.py puts slxlyl in S_REPEATS".
- tests/generated.py holds no `slxlyl`, and its S_REPEATS table holds no `l`.
- The one `slxlyl` was a committed case in tests/cases/substitute.jsonl. There `l` is the s delimiter (`s` `l` `x` `l` `y` `l`: replace x with y), not a suffix, and GNU ed 1.19 runs it that way.
- The row was removed anyway, so the misreading cannot recur.

Finding 25 (Sound Verifier, Minor): "No targeted case observes whether W preserves an already established default filename."
- We scored the implementation the finding describes (W makes its file the default filename) against the returned verifier. It failed test_generated_3 and test_generated_8: their generated scripts W to other.txt and then write with a bare w, so the wrong default filename changes the files left behind.
- Receipt: revision-v7/receipts/returned/W-sets-default-filename.json (reward 0, bound to the returned snapshot). Two targeted cases were added anyway.
