# tbrain-gnu-bc-reimplementation (stopped 2026-09-26, never submitted): reference only

The task is a pure-Python GNU bc 1.07.1 reimplementation, graded against the binary.

## What is here

- `tbrain-gnu-bc-reimplementation.zip`: the last local build, from 2026-09-27 (sha256 `9bac93e4…89aa`). It matches `../tbrain-gnu-bc-reimplementation/`. Compared with the 2026-09-25 build, it hardens only `tests/guard.py` and `tests/test_outputs.py`, applying the gnu-sed rev7 lesson:
  - the audit hook is built in a closure;
  - `_posixsubprocess.fork_exec` is replaced before the program runs;
  - the sqlite extension-loading events are blocked;
  - the demoted candidate starts under `prlimit --nproc=1:1`.
- `tbrain-gnu-bc-reimplementation-2026-09-25.zip`: the earlier build (sha256 `d1b5c89e…`). Its probe verdict and reports belong to this build.
- `SUBMISSION-…md`: the submission note and rubric (the same for both builds).
- `../tbrain-gnu-bc-reimplementation/`: the task tree of the 2026-09-27 build.

## Why it was stopped

- **Contract:** it has the same dual-authority contract as gnu-sed and gnu-ed: "exactly like the binary" plus "only what the manual and the listed rules describe". Neither of those converged on the platform. sed was retired after nine evaluations and ed after eleven.
- **Pre-panel risks:**
  - The instruction is 957 words with 18 bullets; sed failed `instruction_check` at 879 words.
  - `expert_time_estimate_hours = 14` with a 1,338-line reference, which is a risk for the `solvable` check.
  - The agent image has no bc to compare against, so every convention has to be written into the instruction.
- **Probe:** the counted pair was 0/2 (GPT-5.6 through stb harbor, 2026-09-25; 2/20 and 3/20 tests). Both runs failed on rules the manual or the instruction settles:
  - no leading zero below one;
  - plain strings printed literally;
  - short-circuit `&&` / `||`;
  - the precedence of `!` and the relational operators;
  - the single-digit constant rule;
  - the line split at the 69th character.

  Nearly every test failed in both runs. That points to a 0/8 solvability return, not a difficulty signal.

## Lessons

- **A reimplementation graded against a binary does not converge.** Promising "only what the manual describes" while grading against the binary's behaviour gives every panel round a new binary-versus-manual departure to find. Choose a single authority before building anything.
- **0/2 with broad failure across the suite is a warning, not a pass.** When both runs fail almost every test on stated rules, the platform's 8 runs are likely to leave some tests at 0/N, and the conventions become a disclosure list. A good hard signal is a narrow miss on one or two inference traps.
- **Watch the instruction's size before uploading.** More than about 850 words, an expert estimate above 8 hours, or a reference over 1,000 lines each predict a pre-panel `instruction_check` or `solvable` failure.

## Reusable parts

- `solution/pybc/bc.py`: an arbitrary-precision bc interpreter.
- `tests/guard.py` (2026-09-27 build): an audit-hook launcher with a closure hook, a blocked `fork_exec`, and `prlimit --nproc=1:1` in `test_outputs.py`. This is the construction AGENTS.md §2 asks for when no child process is legitimate.
- Evidence:
  - `workspace/reports/tbrain-gnu-bc-reimplementation/`;
  - probes in `workspace/local-solve-probes/tbrain-gnu-bc-reimplementation-*`.
