# tbrain-gnu-sed-reimplementation (stopped 2026-09-26): reference only, do not submit

Platform task `12e6eda4-8ced-4dcd-928d-7abc22b133a9`. The task asks for a pure-Python GNU sed 4.9 that matches the binary byte for byte, graded against the binary itself over about 1,300–1,600 fixed cases.

## What is here

- `tbrain-gnu-sed-reimplementation.zip` is the last uploaded bytes (rev7, sha256 `0c07fad0…`), the same as `workspace/revision/12e6eda4-…/revisions/tbrain-gnu-sed-reimplementation-rev7.zip`.
- `SUBMISSION-tbrain-gnu-sed-reimplementation.md` describes rev8, which was never uploaded.
- `../tbrain-gnu-sed-reimplementation/` holds the unfinished rev8 working tree. It was not packaged, and its last reference fixes were never re-run through the full verifier.

## History

Nine platform evaluations happened:

- Seven were quality-panel returns.
- One was blocked by the static instruction check.
- One reached the difficulty run, but every trial was invalid: the agent image had no `sed`, which the harness itself calls.

The task never received a valid difficulty measurement.

## Why it was stopped

The contract ("behave exactly like the binary, and every check relies only on what the manual describes") has two sources of truth, and they keep disagreeing. Each panel round found new places where GNU sed 4.9 departs from its manual, or corner classes the fixed cases did not cover.

Round v8 had 10 findings. The rev8 local clearance (ten fresh reviewers) then found more:

- a `first~step` second address crashing the reference;
- `\s` matching `\v`, `\f` and `\r` in GNU but not in the manual;
- empty matches after a match under `g`/N;
- `N` at a file's end under `-s`;
- one graded script that GNU itself rejects;
- an audit-hook bypass through `_posixsubprocess.fork_exec`. It was confirmed at reward 1 against the returned verifier; the fix is `prlimit --nproc=1` on the demoted candidate.

The findings do not converge. That matches the loop signs in `task-revise-flag-remediation`.

## Reusable parts

- `rev8/fuzz.py` and `rev8/cmp.py` run a random differential of a reimplementation against the real binary. In rev8 they found reference bugs the panel had missed.
- `rev8/gen_sweeps.py` generates class-sweep cases and keeps only those where the binary agrees with the manual.
- The Pike-VM POSIX leftmost-longest matcher is in `solution/pysed/posixre.py`.
- The OS-level no-subprocess enforcement is `prlimit --nproc=1` before `setpriv`. At 1 it refuses fork; at 2 it allows one.

All evidence is in `workspace/reports/tbrain-gnu-sed-reimplementation/` (`rev1`–`rev8`, `ledger-receipts-v*`, `rev8/reviewers/`). The platform returns are in `workspace/revision/12e6eda4-8ced-4dcd-928d-7abc22b133a9/`.
