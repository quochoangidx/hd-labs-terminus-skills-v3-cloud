# tbrain-gnu-ed-reimplementation — revision v6 (rev6.zip)

Return: evaluation 6, quality panel, 28 blocking findings (Sound Verifier 23, Correct Reference Solution 4, plus 1 Minor launcher bypass). This is the sixth return on the same axis (106, 64, …, 25, 28). The skill's loop signal fired, so this revision narrows the contract instead of adding cases on top of it.

Returned snapshot 9cdf716e… (v6 source zip, same bytes as rev5, untouched). Repaired snapshot 6c31d1b1…. The ledger check passes: 28 findings answered with snapshot-bound evidence (`revision-ledger.json`, `ledger-check.json`).

| Findings | Evidence | Class | Decision |
|---|---|---|---|
| 1, 5 | -p with a hyphen argument; `--prompt=X` rejected by the reference (receipt row F5) | invocation surface, not core | dropped `PROMPT-AND-OTHER-OPTIONS`: only -E, -l and -s, each a single letter |
| 2, 16 | l wrapping and backslash escaping | output formatting | dropped `LIST-COMMAND` |
| 7, 19, 27 | the 100,000-byte bound was untested | bound, not semantics | dropped `LONG-LINES`: 200 bytes a line |
| 8, 9, 10 | binary and unterminated reads (a Major in four consecutive rounds) | corner of io.c | dropped `BINARY-FILES` |
| 20 | EOF during G/V | variant of g/v | dropped `INTERACTIVE-GLOBAL` |
| 22, 23 | `\b`, `\w`, `\W` | GNU conveniences | dropped `GNU-WORD-ESCAPES` |
| 24, 25 | the cut buffer after c and d | unobservable without x/y | dropped `CUT-BUFFER-XY` |
| 26 | default z window | display default | dropped `Z-COMMAND` |
| 11, 12, 13, 14, 15, 17, 18 | each mutant scores reward 1 on the returned verifier (`receipts/returned/*.json`) | core coverage gaps | backed: focused cases plus the grammar generator; each mutant now fails its witness (`../wrong-paths/*.json`) |
| 3, 4, 6 | GNU ed 1.19 and the reference agree byte for byte on each finding's script | panel read the manual, not the program | disputed (`contest-note.md`); 4 also added errata 18 (s without a match inside g) |
| 21 | the returned corpus already catches the mutant (`E other.txt` under -s) | refuted by execution | disputed |
| 28 | tamper, fork_exec and gc probes all got past the returned launcher | real, and wider than reported | backed: closure-based launcher, 9 probes; policy gate `tests:audit-hook-process-gap` |

Scope and verifier: 275 out-of-scope rows left the corpus. The cut used an instrumented reference plus a static argument check, and the 123 cases that earlier maps named and the corpus no longer holds are all out of scope (`evidence/earlier-maps-missing-verdict.json`). `tests/generated.py` adds 640 seeded grammar scripts and fails collection if any grammar entry is drawn fewer than three times. Committed corpus: 663 cases. The reference agrees with GNU ed on all 1,303 cases. Errata: 22 entries, each pinned (`evidence/errata-map.json`).

Probe: the first pair (0/2) was set aside. Its 26 shared misses came from four corners the errata did not settle, now errata 6, 17, 20 and 21. The fresh pair scored 0/2 (Opus 5.5 medium: 23/27 and 14/27), and its shared misses are all documented behaviour (`../probe-verdict.json`). The difficulty stays `advanced`.

Gates on the final snapshot: strict preflight with determinism and noexec (oracle 1, NOP 0), independence, `panel_precheck --full --profile builder_certified` pass, 25 wrong paths each rejected on its own witness (two retired: `unterminated-never-remembered`, `two-print-suffixes`).

Not done: the clearance panel (two fresh reviewers per axis). The contest note has to be posted by hand in #terminus-3-submissions.
