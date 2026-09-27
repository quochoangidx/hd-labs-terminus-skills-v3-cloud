# Contest note for `#terminus-3-submissions` (second round)

**Task:** `tbrain-gnu-ed-reimplementation` (task id `fc57838e-86e3-431c-a65c-b8776a1f307e`)
**Axis / severity:** Correct Reference Solution, Major (findings 4–24) and Minor (52)
**Returned snapshot:** `69e5a50c55efc1da5b21e81a370dc5c932678bedbe59594d59181d446cb98228`

These findings also appeared in the first round under different numbers. They were disputed
then, the dispute was not carried into the channel, and they came back. The evidence below is
reproducible in the task's own verifier image.

## The contract passage

`instruction.md` binds the program, not the manual: `/app/pyed/ed.py` must behave *exactly like
GNU ed 1.19 run as `ed [OPTIONS] [FILE]` with `LC_ALL=C`*, producing the same standard output
byte for byte, the same files and the same zero-or-not exit status. Every expected result in the
suite is produced by running that binary at grading time.

## The counterexample

Each finding supplies a script. Running all of them through GNU ed 1.19 and through the
reference the panel judged gives identical standard output, exit status and files in **all 22
distinct scripts**, with no exceptions:

| Finding | Script | GNU ed 1.19 and the reference both give |
|---|---|---|
| 4 | `f foo` | `foo\n` |
| 5, 9 | `'a=` with no mark set | `0\n`, status 0 |
| 6, 12, 20 | `s/\{2\}/X/p` on `{2}` | `?\n`, non-zero |
| 7 | `s/\<./X/g` on `ab` | `XX` |
| 8 | append, `1j`, `u` | `?` on the undo |
| 10 | `1s/[-a]/X/p` on `0` | `?\n` |
| 11, 17, 18 | `-E`, `s/a^b/X/` on `a^b` | `?\n` |
| 13 | `'aa` on an empty buffer | the append succeeds |
| 14 | `1,2m2` | the move succeeds |
| 15 | `s/a/b/` then `0x` | the cut buffer holds `a` |
| 16, 52 | `g/a/s/a/b` followed by `p` | the substitution takes the rest as replacement |
| 19 | `'ax` with no mark set | the put succeeds at 0 |
| 21 | `g/z/p` matching nothing, then `u` | `?` on the undo |
| 22 | `g/a/` with a backslash-only list | both lines print |
| 23 | empty `1i`, then `p` | `x` |
| 24 | `ka`, `s/x/y/`, `u`, `'ap` | `x` |
| 51 | `-pfoo` | prompt `foo` |

## How to reproduce

In the task's verifier image, which installs GNU ed 1.19, run each script through `/usr/bin/ed`
and through `python3 /app/pyed/ed.py` in fresh copies of the same directory with `LC_ALL=C`, and
compare standard output, exit status and the files left behind. The runner and its results ship
with the revision as
`workspace/reports/tbrain-gnu-ed-reimplementation/revision-v2/receipts/returned-reference-matches-ed.json`.

## What the revision changes anyway

The task now ships `/app/docs/ed-errata.txt`, which states each place where GNU ed 1.19 departs
from its own manual, including every behaviour listed above. The instruction points at it and
says the program decides where the two disagree. So the required behaviour is documented for the
candidate and for the reader rather than only inferable from running ed, and each script above is
also a graded case.

The findings that were right are fixed, not disputed: the binary-file newline rule from the
manual's Limitations section, an option written after FILE, a bare `-p`, the package audit that
rejected data files, and the import guard that treated installed packages as standard library.
