# tbrain-gnu-ed-reimplementation: revision v8 (rev8.zip)

**Return:** evaluation 8, quality panel, 15 blocking findings. Protected Ground Truth and Deterministic Execution came back clean. The returned snapshot (the v8 source zip, identical to rev7, tree `c9b156ca…`) was left untouched. The repaired tree is `699c2f22…`. The ledger check passes (`revision-ledger.json`, `ledger-check.json`): 11 backed, 1 dropped, 3 disputed.

| Findings | Evidence | Decision |
|---|---|---|
| 2, 4, 5, 6, 7, 11, 13 | The returned verifier accepts each mutant with reward 1: `k-suffix-ignored`, `group-interval-refused`, `group-plus-optional-refused`, `backref-5-8-refused`, `filename-first-word`, `four-address-slots` (`receipts/returned/`). | Backed with 11 committed cases: `kap`/`kbn`; `\{m,n\}`, `\+` and `\?` on groups and nested groups, basic and extended; matching `\5` to `\8`; file names with inner and double spaces; 5- and 6-address tuples. Each mutant now fails its witness (`../wrong-paths/`). |
| 1 | One committed row (`mixed_scripts_6` row 9, `s/n\>/&&/3g`) survived the v6 removal of the GNU escapes, because `scope.py` did not check escapes. | Backed: `scope.py` now rejects the ten excluded escapes and the row is gone. The panel's flip did not reproduce: a submission that exits on those escapes scores 1 on the returned verifier too. |
| 8 | "No FILE or command argument starts with `!`" also caught `s!a!b!p`. | Backed: the instruction now says "no file name, on the command line or after a command, starts with `!`". `s!…!` stays graded. |
| 12 | 138 generated scripts used `%`, which the manual never defines. | Backed: `%` is removed from the grammar, and `scope.py` rejects a `%` address. |
| 14 | On the returned guard, `sqlite3` `enable_load_extension(True)` runs and exits 0. | Backed: the hook stops both sqlite3 load-extension events, and a new probe (`guardcheck/sqlite_ext.py`) expects status 120. |
| 3 | The guard cannot tell vendored pure-Python code from self-written code. | Dropped (`STDLIB-ONLY-DELIVERED-CODE`): the instruction now says "Import only the Python standard library (its own compiled modules included) and Python source files under `/app`", which is exactly what the guard checks. |
| 9, 10, 15 | Refuted by running GNU ed on the findings' own scripts (9, 10). For 15, the agent image holds no case, roster or seed. | Disputed: `contest-note.md`, **to be posted by hand in #terminus-3-submissions**. |

**Corpus:** 654 committed cases (1 dropped, 11 added) plus 640 generated ones.

**Gates on the repaired tree:**
- `preflight.sh --strict --determinism` passes: Oracle 1, NOP 0, noexec /tmp, three Oracle runs agree.
- `panel_precheck --full --profile builder_certified` passes with no warnings.
- All 34 earlier wrong paths still fail on the repaired verifier (regression suite), and so do the 6 new ones.

**New gate:** `task-policy.py` `tests:audit-hook-process-gap` now also fails a hook that stops ctypes but not sqlite3 extension loading. On the corpus it flags only the grep and bc launchers, which were already exposed. The lessons are in AGENTS.md §2.

**Probe:** the stored rev6b pair, re-graded on this verifier, still fails (run_1: 3 cases differ; run_2: 18), on the same corners as before. No fresh pair was run: the one dropped rule is a construction rule that no offline dependency can exploit, and the other changes only add checks.

**Open items:**
- `independence_check` still flags `model_in_tests` (the verifier runs GNU ed at grading time). Moving to frozen goldens is a verifier-architecture decision left to the user, as in v7.
- `tests/` is 144 KB of text, close to the panel's ~150 KB budget.
