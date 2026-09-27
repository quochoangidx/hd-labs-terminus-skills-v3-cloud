# tbrain-gnu-ed-reimplementation — revision v5

**Returned snapshot** `9d7ea2b313258f63d8f70d1b4ad486bc07a014b1596cc8944fefa7fce2623b88`
(byte-identical to the rev4 archive; the live tree had not drifted)
**Return** pre-difficulty gate again: 25 blocking findings, down from 50.

## What the evidence showed

| Platform claim | Raw evidence | Root-cause class | Decision |
|---|---|---|---|
| 1, 2: binary-buffer newline state | GNU ed `io.c` keeps one remembered `unterminated_line` node; the reference kept a per-line flag and moved it onto the new last line; 13 of 60 neighbouring scripts differed | reference defect, third round on this corner | backed: reference follows the source model; errata 21 restated; 58 cases |
| 4: RecursionError on `a\{2000\}` | reproduced; `s/a*/X/` on 2,000 chars also died, `y*z` on 70,000 chars was quadratic | reference defect | backed: matcher compiled to a program walked with a per-search memo; 126k random searches agree with the old engine; 13 long-line cases |
| 3, 5: `q` after an empty continuation line; `2,1a` | GNU and the reference agree on both; the errata sentences were wrong | errata defect | backed: entries 3 and 18 reworded, cases pin them |
| 6: empty `a` clears undo | GNU and the reference agree; the errata lacked the entry | errata gap | backed: entry 14 added, cases for a, i, c |
| 7: `sgxgyg` accepted | GNU and the reference both print `?` | not a defect | disputed, contest note prepared, scripts graded |
| 15: INT_MAX line length | no line-length bound in the instruction | domain gap | backed: "no line is longer than a hundred thousand bytes" |
| 8: no directory fixtures | `workdir()` could not create `sub/x` | verifier gap | backed: fixtures may hold a directory part, snapshot walks the tree, 7 cases |
| 19: ELF magic in a data file rejected | reproduced on the returned audit | overstrict static check | backed: audit removed; the run-time launcher the instruction names is the enforcer |
| 9–14, 16–18, 20–25 | no case in the returned corpus; the panel had left four files unread | coverage gap + packet size | backed: 27 cases in the family files the panel reads; corpus cut under the panel's total budget |

Probing the repeat boundary also showed GNU ed refuses a count above 32767 (`RE_DUP_MAX`):
errata entry 11, four cases.

## The corpus

| | v4 | v5 |
|---|---|---|
| cases | 1,816 | 955 |
| case files, total | 250 KB | 109 KB |
| largest case file | 41 KB | 7 KB |
| platform-visible tests | 25 | 21 |

The four generated buckets of 268–285 scripts were replaced by two of 40, chosen by which of
the wrong-path mutants each script kills (every mutant a generated script could kill keeps at
least four killers). Every focused family grew; every errata entry and every v5 finding names
its cases in `evidence/errata-map.json` and `evidence/coverage-map.json`, checked by
`check_coverage_map.py`.

## Results

| Run | Result |
|---|---|
| Strict preflight with determinism | Oracle 1, NOP 0, noexec Oracle 1, three runs identical |
| Wrong paths | 16 of 16 rejected on their own witness (4 new this round) |
| Probe scripts of this round | 221 of 221 agree with GNU ed 1.19 |
| Panel precheck (`builder_certified`, full) | pass |
| Revision ledger | 25 findings answered with snapshot-bound evidence |

## Gates bought

- `panel_precheck.py` `panel_unread_budget`: more than 150 KB of text under `tests/` or
  `solution/` blocks, because the panel stops reading a packet at roughly that size.
- Every snapshot hasher skips `.DS_Store` and `._*`: a Finder file that appeared mid-run made
  every receipt of the round unbindable once.

## Final state

| Item | Value |
|---|---|
| Repaired snapshot | `b5bece5464a3a8c76f4544975e7b8d889797d174f5ccd3ce641b91de19d6e20d` |
| Upload archive | `revisions/tbrain-gnu-ed-reimplementation-rev5.zip`, sha256 `53a8c855b11d4719154bec5f64e0ce0fd297164c8418d18b089858601d89064e`, 44 entries; `workspace/submissions/tbrain-gnu-ed-reimplementation.zip` is the same bytes |
| Returned archive | untouched, sha256 `7381ddeb26fa6bbd5836db18bff05471cb7452cb5d758fa318332f99969af45b` |

No fresh blind probe was run: the corpus changed, so the earlier local signal is stale, and the
platform has never reached difficulty measurement for this task. Finding 7's contest note needs
to be posted in `#terminus-3-submissions` by hand.
