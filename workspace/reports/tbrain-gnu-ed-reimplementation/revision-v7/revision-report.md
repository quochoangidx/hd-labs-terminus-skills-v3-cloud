# tbrain-gnu-ed-reimplementation: revision v7 (rev7.zip)

**Return:** evaluation 7, quality panel, 25 blocking findings. The returned snapshot (v7 source zip, identical to rev6) was left untouched. The ledger check passes: every finding is answered with snapshot-bound evidence (`revision-ledger.json`, `ledger-check.json`).

| Findings | Evidence | Decision |
|---|---|---|
| 5–8, 10, 11, 20, 21 | 32 committed rows named an excluded command (`l`, `z`, `x`, `y`) or used a missing FILE with a regular-file stdin (`receipts/returned/out-of-domain-cases.json`). The v6 scope scan was dynamic and missed lines the reference never reached. | Backed: the rows were removed, and `tests/scope.py` now fails collection on any case outside the stated domain. The instruction now says the excluded commands "never appear in a script". |
| 1, 16, 17 | The returned verifier accepts readers that split a 200-byte line. | Backed: 200-byte file, command and text lines. The limit is now stated as bytes before the newline. |
| 2, 3, 4, 18, 19, 23 | The returned verifier accepts each mutant (reward 1). | Backed: ERE collating/equivalence elements, open-ended `{32768,}`, `srp`/`spr`, 4096 lines, three-deep nesting, `e`/`E`/`f`/`r` continuation. Each mutant now fails its witness. |
| 13, 14 | GNU ed does not fold `\xc9`/`\xe9`; the returned reference did. | Backed: `posixre.py` folds ASCII only, and scripts are now ASCII by contract. |
| 22 | The guard allows the standard library's compiled modules. | Backed: the instruction now says the standard library's own compiled modules are allowed. `plain.py` imports `math`. |
| 9, 12, 15, 24, 25 | Refuted by execution or outside the domain. | Disputed (`contest-note.md`, to be posted by hand in #terminus-3-submissions). |

**Verifier and corpus:** 644 committed cases plus 640 generated ones. The reference matches GNU ed 1.19 on all 1,284. `check()` now runs cases on a thread pool, cutting the full verifier from about 110 s to 23 s.

**Wrong paths:** 34 fail their own witness. Retired: `unicode-case-folding` (indistinguishable once scripts are ASCII), plus the two retired in v6.

**Gates:** strict preflight with determinism and noexec passes (Oracle 1, NOP 0, three Oracle runs agree), and so does `panel_precheck --full`.

**Open items:**
- `independence_check` now flags `model_in_tests`. This is a new rule on branch `skills/sister-repo-learnings-frozen-goldens`: it asks for frozen expected results instead of running GNU ed at grading time. Adopting it would change the verifier architecture the panel has judged for seven rounds, so it is left for a decision.
- Probe: the rev6 pair's solutions, re-graded on this verifier, still fail (5 and 16 of 1,284 cases differ). The rev7 changes are on the verifier side, plus clarifications to the instruction's wording.
