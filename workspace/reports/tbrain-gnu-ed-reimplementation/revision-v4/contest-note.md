# Contest note for `#terminus-3-submissions` (fourth round)

**Task:** `tbrain-gnu-ed-reimplementation` (task id `fc57838e-86e3-431c-a65c-b8776a1f307e`)
**Axis / severity:** Correct Reference Solution, Major (findings 8–13, 16)
**Returned snapshot:** `59a910038fda9755816301c8a405245619650c29ba511233a4f9dce528da7507`

Seven of the fifty findings are contested. The other forty-three are answered by a change to
the task, including the two that were right and were mine: a graded `-v` invocation the
contract excludes, and a binary-file flag that never cleared.

## The contract passage

`instruction.md` binds the program: `/app/pyed/ed.py` must behave exactly like GNU ed 1.19 run
with `LC_ALL=C`, and every expected result in the suite comes from running that binary at
grading time. `/app/docs/ed-errata.txt` states where the program departs from its manual.

## The counterexamples

| Finding | Script | GNU ed 1.19 and the reference both give |
|---|---|---|
| 8 | `2,1a` on a two-line buffer | the append succeeds, `first inserted second` |
| 9, 13, 16 | `s/a*/X/g` on a buffer holding `a` | `X`, status 0 — the refusal needs a repeated zero-length match |
| 10, 12 | `g/./` with a backslash-only first list line, then `q` | each line printed twice, then the quit |
| 11 | `g/\<\>/p` | no output, status 0 — the expression compiles |

Findings 9, 13 and 16 read the errata's sentence "a substitution with the g suffix is refused
when its expression can match the empty string" as a rule about the expression. It is a rule
about what the program does: ed refuses when a zero-length match repeats at the same place,
which is why `s/a*/X/g` succeeds on `a` and fails on `b`. Both scripts are graded cases, and
the errata sentence now says so in those terms.

## How to reproduce

In the task's verifier image, run each script through `/usr/bin/ed` and through
`python3 /app/pyed/ed.py` in fresh copies of the same directory with `LC_ALL=C`, comparing
standard output, exit status and the files left behind. The runner and its results ship as
`revision-v4/receipts/returned-reference-matches-ed.json`.

## What was wrong on our side, and is fixed

- A case graded `ed -v` while the instruction lists six options and no others. The case is
  gone, and the errata says nothing grades `-G` or `-v` (findings 1–7, 17).
- The binary flag introduced two revisions ago was never cleared, so after any NUL-holding file
  a later empty read stripped the final newline from an ordinary text buffer. Loading a file now
  sets the flag from that file, and a wrong path keeps the old behaviour dead (findings 14, 15).
