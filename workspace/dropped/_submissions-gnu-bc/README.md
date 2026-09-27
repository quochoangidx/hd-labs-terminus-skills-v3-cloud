# tbrain-gnu-bc-reimplementation (stopped 2026-09-26, never submitted): reference only

This is a pure-Python GNU bc 1.07.1 graded against the binary. The ZIP is the last local build (sha256 `d1b5c89e…`). The task tree is `../tbrain-gnu-bc-reimplementation/`.

## Why it was stopped

- **Contract:** the same dual-authority contract as gnu-sed and gnu-ed ("exactly like the binary" plus "only what the manual and the listed rules describe"). Neither of those converged on the platform.
- **Pre-panel risks:**
  - the instruction is 957 words with 18 bullets (sed failed `instruction_check` at 879 words);
  - `expert_time_estimate_hours = 14` and a 1,338-line reference (a `solvable` check risk);
  - the agent image has no bc to compare against, so every convention has to live in the instruction.
- **Probe:** the local counted probe was 0/2, so the task was hard enough, but that did not help sed or ed.

## Reusable parts

- `solution/pybc/bc.py` (the arbitrary-precision bc interpreter)
- `tests/guard.py` (the audit-hook launcher; add `prlimit --nproc=1:1` if a reference binary is ever reachable)
- the evidence in `workspace/reports/tbrain-gnu-bc-reimplementation/`
