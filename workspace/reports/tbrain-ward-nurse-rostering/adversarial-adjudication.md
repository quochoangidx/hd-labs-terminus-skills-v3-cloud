# Adversarial verifier pass (step 5b) - GPT-5.6 medium via stb codex exec; saw instruction, environment, tests; not solution/manifest/reports
15 wrong + 2 valid submissions (adversarial_review.md). Two findings, both upheld (builder: accept; orchestrator: uphold):
1. Duplicate nurse keys silently accepted (json keeps the last value). Fixed: the loader (tool and verifier copy, byte-identical) uses an object_pairs_hook that rejects a name given twice in one object; the rules now say so.
2. Deeply nested ignored value raised RecursionError (false rejection of an unannounced kind). Fixed by narrowing the promise: the rules state that objects and arrays nest at most 64 levels (top-level object = level 1); the loader checks depth iteratively and turns RecursionError into the stated error. 64 levels accepted, 65 and 5000 rejected with the stated message (scratch check 2026-09-25).
The same two gaps existed in the stand-plan and ad-layout loaders and were closed the same way.
