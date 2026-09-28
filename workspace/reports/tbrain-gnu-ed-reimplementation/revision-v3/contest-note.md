# Contest note for `#terminus-3-submissions` (third round)

**Task:** `tbrain-gnu-ed-reimplementation` (task id `fc57838e-86e3-431c-a65c-b8776a1f307e`)
**Axis / severity:** Correct Reference Solution, Major (findings 6, 19, 24)
**Returned snapshot:** `68890de1633b39b51de23e82147974c5e43de42adf79d8473bcb7e9b1462229b`

Only three findings from this round are contested. The other forty-nine are answered by a
change to the task, including eleven that were raised because entries in the errata this task
ships were themselves wrong.

## The contract passage

`instruction.md` binds the program: `/app/pyed/ed.py` must behave exactly like GNU ed 1.19 run
with `LC_ALL=C`, and every expected result in the suite comes from running that binary at
grading time.

## The counterexamples

| Finding | Script | GNU ed 1.19 | Reference |
|---|---|---|---|
| 6 | `g/[-a]/p` on a file holding `0` | prints nothing, status 0 | identical |
| 19 | `,2p` on a four-line buffer | prints the first two lines | identical |
| 24 | `sgxgyg` | `?`, the line unchanged | identical |

Finding 6 also agrees with the manual: a hyphen first in a bracket expression is literal, and
the reference treats it that way. Finding 19 matches the documented comma default. Finding 24
matches the documented delimiter restriction.

## How to reproduce

In the task's verifier image, run each script through `/usr/bin/ed` and through
`python3 /app/pyed/ed.py` in fresh copies of the same directory with `LC_ALL=C`, comparing
standard output, exit status and the files left behind. The runner and its results ship as
`workspace/reports/tbrain-gnu-ed-reimplementation/revision-v3/receipts/returned-reference-matches-ed.json`.
All three scripts are now graded cases.

## What was wrong on our side, and is fixed

- The instruction said the files are ASCII text while the corpus supplied NUL-holding fixtures.
  The stated domain now admits them (findings 1, 2, 4).
- Three errata entries were wrong: an unset mark resolves to zero only while the buffer is
  empty, a change clears a mark and undo restores it, and a backslash-only first global-list
  line is a continuation whose empty segment prints. Rewritten from execution, each pinned by a
  case (findings 5, 7–9, 11–15, 18, 22).
- Six behaviours that kept being read as defects are now documented: the `?` notification goes
  to standard output, `=` accepts a reversed range, the first branch supplies the capture, `-G`
  and `-v` are accepted, a `g` substitution whose expression can match empty is refused, and a
  backslash does not continue a regular expression (findings 3, 10, 16, 17, 20, 21, 23).
- The package audit rejected a Python shebang (findings 27, 38).
