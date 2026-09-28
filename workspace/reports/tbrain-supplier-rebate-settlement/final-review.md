# Final review: tbrain-supplier-rebate-settlement

I had full visibility of the task folder. I reran the Oracle `fix.patch` and `solution/model.py` locally against every row in `tests/expected/` (with the `limits_job` repeat expanded). All rows matched both, with 0 mismatches.

## r1 finding: closed
In r1 the aggregate sentences in 5.1/5.2 ("total of these") conflicted with the preservation clause. In R-4 as shipped:
- 5.1 and 5.2 now have per-item subjects only.
- 5.3 gives "Every price notice ... one credit line, and every sale below cost ... one chargeback line" and defines the totals over all lines.

So a tidy-up or price-match line exists, but no rule sets its amount. That amount falls under the instruction's "keeps the exact calculation today's code makes" clause. Tidy-ups keep today's step (cut × on_hand, or 0 below 5,000), and price-match sales keep theirs (below × units, or 0 below 25 cents). No competing positive enumeration remains. Closed.

## Oracle against the schedule
The Oracle matches the schedule rule by rule:
- Carton lines of 12 or more units get +4 days; loose lines keep the invoice date (2.2, 3.1, 3.2).
- The return charge is 40 through a new figure; `unit_handling` stays at 25 for `claim_cutoff`.
- The settlement minimum is 25,000 through a new figure; `small_credit` stays at 5,000 for `notice_cutoff`.
- Tiers use `>=` on net, the rebate is rounded half-up, and growth is taken on (net - prior).

Kept values in the sealed files:
- Tidy-up credits of 100, 4998, 5000, 11550, 17372, 23112, 24304 and 24900. These cover the 5,000–24,999 band that separates "kept 5,000" from "moved to 25,000".
- Price-match gaps of 1, 24, 25, 26, 38, 39 and 99.
- Loose lines within 4 days of both quarter edges, including the year edge.

For price drops and contract sales, the retained shipped cut-offs never fire: a drop of 250 or more cents on 100 or more units gives at least 25,000, which is over 5,000, and a contract-sale gap of 100 or more is over 25. So the unchanged `protection.py`/`chargeback.py` are correct for the governed items.

## Findings

1. **should-fix (contract wording, residual trap risk).** Instruction: "the only inputs of that calculation that change are those the schedule itself sets." The shipped `settle.py` reads `figure("settlement_minimum")`, which maps to `small_credit`, and 6.2 sets that minimum to 25,000. A reader can argue that the schedule "sets" `small_credit`, so the tidy-up cut-off moves too.
   - Counterexample: a tidy-up notice with a cut of 200 on 100 units, in the quarter. The intended result is protection 20000; that reading gives 0.
   - The same argument works for `unit_handling`: return charge 40 vs price-match cut-off 25. A 30-cent gap on 10 units gives 300 intended, 0 under that reading.
   - "with every constant of the package at its value today" and the use-named `USES` table point to the intended reading, so a careful reader resolves it. But this is the task's main difficulty, and it hangs on the one sentence.
   - Suggested fix: change "inputs ... the schedule itself sets" to "the figures the schedule itself sets for the step in question". Or accept it as the intended trap, since `difficulty_explanation` already calls the shared-figure repair the natural over-repair.
2. **polish.** The Oracle adds `if net <= 0: return 0` in `volume_rebate`, while the instruction says "Add no exception, clamp or guard of your own." It does not change any output (net < 0 already reaches no tier, so bp = 0), but the reference breaks the letter of its own instruction. Drop the guard: `half_up(net*0, 10000)` = 0.
3. **polish.** The `model.py` guard `tier_rate(net, tiers) if net >= 0 else 0` is also redundant because the first threshold is 0. It is harmless.
4. **polish (verifier).** `-p no:randomly` refers to a plugin that is not installed. pytest accepts this, so it only adds noise.
5. **Isolation: no defect found.**
   - `/tests` and `/logs/verifier` are 0700 root, and the candidate runs as uid 65534 via `setpriv --no-new-privs`.
   - `python3 -I -S` blocks `.pth`, sitecustomize and `PYTHON*` environment injection.
   - The driver is recorded, then replaced with `os.replace`, and byte-checked both in pytest and in `test.sh` after the run.
   - `/app` is re-owned by root and made non-writable (`lchown`, so symlinks are not followed).
   - The shipped differential copy is private to uid 65533, and a readable control proves the unreadability probe works.
   - Jobs are staged under a neutral name. Generated and limits jobs are relabelled with a per-run `os.urandom` seed and shuffled, so lookup or steering by content cannot work.
   - Residual risk: the candidate can keep state in world-writable /tmp between runs. That is useless without expectations, so I did not file it as a finding.
6. **Coverage: good.**
   - There is one family per rule, and each boundary has both sides: 12 units, a 250-cent cut, a 100-cent gap, 110%, prior 0/1, threshold ±1 cent, net < 0, 24,999/25,000/25,001, an empty account, exact halves.
   - `trap_inputs` makes sure only the three trap families carry unreached inputs, so an error in a trap cannot fail some other rule's test, and every other family is trap-free.
   - The limits cover 12 rows, 10^11, 100 accounts, 400 lines, 100 returns, 50 notices and 200 sales, 2020-Q1 and 2039-Q4, and codes of 1 and 16 characters with non-ASCII.
   - Comparison is type-strict (`bool` and `float` are rejected), with exact key sets and job order.
7. **Semantic equivalence: acceptable.** Key order inside a settlement and JSON whitespace are free, and only the exact integers are graded. This matches the instruction and README. A candidate that restructures `rates.py` differently (for example, inlining the constants) passes, as `verification_explanation` claims.
8. **task.toml: accurate.** The explanations match the code I read: the patch touches 5 files, the tests and families are as described, and the isolation works as stated. I could not verify the "19 mutants" or "two alternatives score 1" claims here. Category and subcategory (Operations / Supply chain) fit. The `difficulty_explanation` is candid about the traps; it is not agent-visible, so that is fine.
9. **Folder and style: clean.** `.dockerignore` excludes `solution/` and `tests/`. The environment image has no test dependencies, and the verifier image is separate with pinned pytest. The prose in the instruction, schedule and README is plain and specific, and I found no leakage of expected values or trap hints beyond the domain descriptions in 1.4, 1.6 and 1.7 (which are fair).

## Verdict
The task is ready, apart from finding 1: tighten that one sentence or consciously accept it as the trap. Finding 2 is a one-line cleanup of the Oracle.
