# tbrain-gnu-grep-reimplementation (stopped 2026-09-26, never submitted): reference only

This is a pure-Python GNU grep 3.8 graded against the binary. The ZIP is the last local build (sha256 `69ebabfe…`). The task tree is `../tbrain-gnu-grep-reimplementation/`.

## Why it was stopped

- **Contract:** the same dual-authority contract as gnu-sed and gnu-ed, neither of which converged on the platform.
- **Harness failure:** `environment/Dockerfile` deletes `grep`, but the platform harness calls `grep` inside the task container (`get-asciinema-timestamp.sh`). That is the failure that invalidated all 8 gnu-sed v7 difficulty trials (`NonZeroAgentExitCodeError`).
- **Subprocess hole if grep is kept:** keeping grep in the image opens the `_posixsubprocess.fork_exec` hole in `tests/guard.py` (no audit event), which was proven at reward 1 on gnu-sed. It would need `prlimit --nproc=1:1` on the demoted candidate.
- **Other risks:** `expert_time_estimate_hours = 10` (above 8), and a 650-word bulleted instruction.

## Reusable parts

- `solution/` (a POSIX leftmost-longest matcher plus grep's output controls)
- `tests/guard.py`
- the evidence in `workspace/reports/tbrain-gnu-grep-reimplementation/`
