# Contest note for `#terminus-3-submissions` (fifth round)

**Task:** `tbrain-gnu-ed-reimplementation` (task id `fc57838e-86e3-431c-a65c-b8776a1f307e`)
**Axis / severity:** Correct Reference Solution, Major (finding 7)
**Returned snapshot:** `9d7ea2b313258f63d8f70d1b4ad486bc07a014b1596cc8944fefa7fce2623b88`

One of the twenty-five findings is contested. The other twenty-four are answered by a change
to the task: three reference defects (the binary-buffer newline state, twice, and a matcher
that recursed once per repetition), two errata sentences that were wrong about the program,
one program behaviour the errata lacked, seventeen coverage gaps and one overstrict check.

## The contract passage

`instruction.md` binds the program: `/app/pyed/ed.py` must behave exactly like GNU ed 1.19 run
with `LC_ALL=C`, and every expected result in the suite comes from running that binary at
grading time. The manual (section 7) says the delimiter of `s` may be any character other
than space or newline, except those used by the repeat form (`g`, `p`, `r` and digits).

## The counterexample

Finding 7 says the reference accepts `sgxgyg` and changes `x` to `y`. It does not. In the
task's verifier image, with a buffer holding one line `x`:

| Script | GNU ed 1.19 | Returned reference |
|---|---|---|
| `sgxgyg` then `p` | `?` then `x`, status non-zero | the same |
| `spxpyp`, `srxryr`, `s3x3y3` | `?` then `x` | the same |
| `slxlyl`, `snxnyn`, `saxaya` | `y` | the same |

The reference parses the repeat form before it looks for a delimiter, as the program does, so
`g`, `p`, `r` and digits never become delimiters. The scripts are now graded cases, so the
point is pinned rather than argued (`tests/cases/substitute.jsonl`).

## How to reproduce

In the task's verifier image, run each script through `/usr/bin/ed` and through
`python3 /app/pyed/ed.py` in fresh copies of the same directory with `LC_ALL=C`, comparing
standard output, exit status and the files left behind. The runner and its results ship as
`revision-v5/receipts/returned-findings-3-5-6-7-refuted.json` (rows F7, F7b to F7i).
