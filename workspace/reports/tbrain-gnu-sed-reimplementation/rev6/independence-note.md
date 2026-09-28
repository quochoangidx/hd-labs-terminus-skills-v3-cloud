# independence_check.py on rev6: model_in_tests is not applicable

`independence_check.py` gained a `model_in_tests` rule on 2026-09-26 at 14:28, an uncommitted edit in the working tree. The rule blocks an end-to-end expectation model kept under tests/, because the whole answer would then ship in tests/.

This task has no expectation model. For every case, tests/test_outputs.py runs the verifier image's own GNU sed 4.9 binary (root-only) to get the expected stdout and status, then compares the candidate against it (a shipped differential against the authority binary). `--model tests/test_outputs.py` was passed only because the tool requires a `--model` argument.

The same file passed the check on rev5 (rev5/independence.json, status pass). tests/ is byte-identical between rev5 and rev6. The platform's v7 quality checks passed `verifiable`, `reviewable` and `anti_cheat_robustness` on this design.

panel_precheck --full passes on rev6 and does not depend on this receipt.
