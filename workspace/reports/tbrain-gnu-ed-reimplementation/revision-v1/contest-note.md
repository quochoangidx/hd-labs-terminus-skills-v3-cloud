# Contest note for `#terminus-3-submissions`

**Task:** `tbrain-gnu-ed-reimplementation` (task id `fc57838e-86e3-431c-a65c-b8776a1f307e`)
**Axis / severity:** Correct Reference Solution, Major (findings 1–13, 15–19) and Sound
Verifier, Minor (findings 76, 104)
**Returned snapshot:** `0bd83f1dd850bc96541c32e47836703e7fe287578fbdfda5990952d3c9ee63f2`

## The contract passage

`instruction.md`, first paragraph: the program must behave *exactly like GNU ed 1.19 run as
`ed [OPTIONS] [FILE]` with `LC_ALL=C` and the same standard input*, producing the same standard
output byte for byte, the same files, and a zero exit status exactly when GNU ed's is. The
verifier takes every expected result from that binary at run time. So the binary, not a reading
of the manual, decides what the reference must do.

## The counterexample

Each finding names a script. Running every one of those scripts through GNU ed 1.19 in the
verifier image, and through the reference the panel judged, gives the same standard output, the
same zero-or-not exit status and the same files in 21 of the 22 cases. Only finding 14 differs,
and that one is repaired in this revision.

| Finding | Script | GNU ed 1.19 | Reference |
|---|---|---|---|
| 1, 7, 18 | `a`/`one`/`.`/`W out`/`q` | `4\n`, status 0 | same |
| 2 | `a`/`one`/`.`/`g/x/p`/`u`/`Q` on a regular file | `?\n`, non-zero | same |
| 3, 6 | `'a=`/`Q` with an empty buffer | `0\n`, status 0 | same |
| 4 | `g#[-a]#p` against the line `/` | no output | same |
| 5 | `f target`/`Q` | `target\n` | same |
| 8, 19 | `s/\(a\|aa\)a\?/<\1>/p` on `aa` | `<a>\n` | same |
| 9 | `s/foo/bar/`/`x`/`,p` | `4\nbar\nfoo\n` | same |
| 10 | `g/a/s/a/b\`/`p` | `2\np\np\n` | same |
| 11 | `-E`, `s/a^/X/` on `a^` | `?\n3\n`, non-zero | same |
| 12 | `'ap` with no mark set | `?\n`, non-zero, no hang | same |
| 13 | `-E`, `s/(a|aa)(a?)/[\1]/p` on `aa` | `[a]\n` | same |
| 15 | `g/x/` with an empty command list | `x\n` | same |
| 16 | `1s/a/A/`/`1j`/`u`/`,p` | `4\n?\nA\nb\n` | same |
| 17 | `1m0`/`q`/`q` | `2\n?\n` | same |

Findings 76 and 104 concern invocation forms: GNU ed 1.19 accepts `-Es`, `-pfoo` and `-G`, and
it applies an option written after FILE (`ed f.txt -s` prints no byte count). The reference does
the same. The instruction also says each option comes as its own argument before the optional
FILE, so those forms do not occur in graded runs; requiring a rejection would contradict the
binary the contract names.

## How to reproduce

In the verifier image (`tests/Dockerfile`, which installs GNU ed 1.19), for each script run
`/usr/bin/ed` and `python3 /app/pyed/ed.py` in fresh copies of the same directory with
`LC_ALL=C`, and compare standard output, exit status and the files left behind. The runner and
its results are kept with the revision as
`workspace/reports/tbrain-gnu-ed-reimplementation/revision-v1/receipts/returned-reference-matches-ed.json`.

## What the revision does anyway

Every script above is now a graded case, so the behaviour each finding questions is pinned to
GNU ed 1.19 rather than argued about. Finding 14 was real and is fixed: a multi-character
collating element or equivalence class is an error in the C locale, and the same probe exposed
three further bracket and interval rules the reference had wrong, all now corrected.
