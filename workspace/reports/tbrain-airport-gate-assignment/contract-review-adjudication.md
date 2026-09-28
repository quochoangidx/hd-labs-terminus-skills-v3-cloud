# contract_review adjudication (reviewer: GPT-5.6 medium via stb codex exec, blind to tests/solution)
Verdict: accept with fixes.
1. Should-fix, duplicate stand keys vs "given at most once": builder accept; orchestrator uphold. Fix: dropped "given at most once" (parsed-object semantics; no scoring effect).
2. Should-fix, diagonal and remote walk entries: builder accept; uphold. Fix: cost section now states the matrix entry is used in every case (non-zero diagonal, remote walk on top of bus).
3-5. Advisory, no action.
