# tbrain-gnu-dc-reimplementation — contract_review adjudication

Reviewer: one independent task-visible session (Opus, general-purpose), packet = instruction.md + environment/ only.

Fairness mechanism: the reference ports GNU dc 1.4.1 and the bc number library, and matches the real binary on all 2135 generated cases (stdout and status). For each point the manual leaves open or contradicts, a variant of the reference implements the other reading (reports/dc-work/make_variants.py plus the later additions). A case is kept only if every applicable variant prints the same stdout as GNU dc. Where a convention is used constantly and a sentence can state it exactly, the instruction's "GNU conventions" list states it instead, and that variant no longer filters.

| # | Finding | Disposition |
|---|---|---|
| 1, 2 | No leading zero below 1; how zero prints | Stated in the conventions list |
| 3 | `f` order | Stated (top down) |
| 4 | Stack after an error; continuation | "Goes on with the next command" is stated. Stack effects are left open; variant `consumeonerror` drops every case where they matter |
| 5 | Fraction digits in non-decimal output | Stated (the smallest k with radix^k >= 10^n) |
| 6 | Output radixes above 16 | Integer part stated. The fraction layout is filtered by variant `bigbasefracspace`; zero and sign follow from the stated rules |
| 7 | Line splitting | Stated (69 characters + `\`, count restarts for each number, sign included) |
| 8 | Truncation toward zero | Stated |
| 9 | `^` scale contradicts the manual | Variant `raisescalek` drops every case where the manual's literal rule differs |
| 10 | `%` / `~` formula | Variants `remformula` and `divremformula` drop the differing cases |
| 11 | `v` of 0 or 1 | Variant `sqrt01scale` drops the differing cases |
| 12 | `-0` | Variants `negzero` and `raisezeroerror` drop the differing cases |
| 13 | Input digits at or above the radix | Stated (face value); variant `digitclamp` no longer filters |
| 14 | Scale of typed fractions in other radixes | Stated |
| 15 | Parsing details | Stated (optional `_`, digits, at most one `.`; `3.4.5`) |
| 16 | Comparisons on a short or non-numeric stack | Variant `cmpemptyfalse` changes no retained case. An empty or numeric register follows the documented `l` and `x` rules |
| 17 | Arrays | Unset element stated (pushes 0). An array-only register is filtered by `arrayregl0` |
| 18 | `Q` past the macro depth | "Q never makes dc exit" is stated. Top-level behaviour is filtered by variants `qtopexit` and `qstopsattop` |
| 19 | `?` with the script on stdin | Excluded from the cases |
| 20 | `a` on negative, large or empty values | Variants `aabs`, `fracintnoerr` and `aemptyempty` drop the differing cases |
| 21 | `Z` | GNU agrees with the manual (leading zeros are not counted even after the point); the reference matches GNU. No change |
| 22 | `k`/`i`/`o` with bad values | Variants `iclamp` and `fracintnoerr` drop the differing cases |
| 23, 24 | Option scope; `!<`-style comparisons | Stated |
| 25 | `|` scale when k > 0 | Variant `modexpscale0` drops the differing cases |
| 26 | Uppercase digits | Stated |
| 27 | Order of `-e`, `-f` and FILE arguments; `q` ends the run | Stated |
| 28 | Fairness claim | True once the rows above are applied |

Also settled by the manual, so not used as variants: `R` direction ("will make the topmost element the second-from top") and the 70-column limit ("split to fit within 70 columns").

Result: 2135 generated cases, **1476 retained**. The reference is at reward 1 and the stub at reward 0 (re-checked on the final set). An earlier blind skeleton solution, written against an older instruction, failed 17 of 23 tests on the 1542-case intermediate set. All eight wrong paths are killed by their target tests.

## final_review (same reviewer session)

First pass: **REJECT**, with four unstated rules the reviewer measured with its own variants:
- stack effects after a failed operation (317 cases);
- a conditional on an empty register pushing 0 (248 cases);
- `Z` of zero being 1 (36 cases);
- non-integer counts and indexes (5–11 cases).
All four were added to the conventions list, together with "`^` can leave a negative zero". The square-root claim in task.toml was corrected.

Recheck: **REJECT**, needing two wording fixes. `r` swaps strings and fails only with fewer than two values, and `:` with one value removes it. The size rule was corrected from 64-bit to "2^31 or more counts as -1", and the reference was updated to match GNU; it still matches on all 1476 cases.

Final: **ACCEPT**. The advisory point: GNU's exact cutoff is 2147483650, so 2147483648 and 2147483649 (and their negatives) wrap rather than counting as -1. No retained case uses these values, so the sentence was left unchanged rather than invalidating the running probe and the receipts; it is recorded as residual risk.
