# Final review: tbrain-mobile-data-overage-billing (final-packet)

Verdict: **no BLOCKING findings, ready to submit.** There are 2 SHOULD-FIX (claims I could not check) and 3 POLISH items.

Everything below comes from running Python 3.11 in a scratch copy. I did not build Docker or do a Harbor run.

## Checks and evidence
1. **fix.patch applies and gives the model's figures.** I ran `patch -p1` against a copy laid out as `/app` and it applied cleanly (dry run first, then for real).
   - The patched package equals `model.statement` on all 9 sealed files.
   - It also matches on 3,000 random fuzz files, covering all three plans, sessions of 1, 1023, 1024 and 1025 kB and random sizes, and 0 to 12 sessions per line.
2. **Sealed expectations and ROSTER.** Every file's SHA-256 and row count match ROSTER, and every stored statement equals `model.statement(usage)`.
   - Re-running `seal.py` in a scratch copy reproduces `tests/expected` and `tests/shipped` byte for byte.
   - `tests/shipped` equals the environment's `src` and driver.
3. **The two kept figures are graded, and each is graded in isolation.** I ran one-edit mutants against the sealed files:

   | Mutant | Families that fail |
   |---|---|
   | FLEX allowance 0 or 2048 | 05-flex and 07-together only |
   | Overage clamped at 0 inside the allowance | 06-not_over and 07-together only |
   | Charge clamped at 0 inside the allowance | 06-not_over and 07-together only |
   | Unfixed shipped package | all 9 |
   | Lower rate from 1,000 or 1,025 MB | all 9 |
   | Part megabytes dropped | 01, 04, 05, 06, 08, 09 |

   `load()` asserts that no FLEX line and no inside-allowance line shows up in a family that does not grade it. In both `jobgen` and the tests, "idle" means used <= allowance, so a line exactly on its allowance counts as idle and lives only in not_over (N3, N4) and together (X2).
4. **Coverage promises in the instruction are met.**
   - 1-line file (ONLY) and 200-line file (limits).
   - All three plans.
   - No sessions (N1, X1).
   - 1 kB sessions, whole-MB and part-MB sessions.
   - Inside, exactly on, 1 MB over (P1, P2, F1) and far over.
   - Overage of 1023, 1024 and 1025 MB and far more (R1 to R6).
   - Rates 1 and 500.
   - 60 sessions and 2,000,000 kB sessions.
   - Ids of 1 and 10 characters.
   - Every file passes `within_limits` at seal time and again at test time.
5. **task.toml explanations**
   - True as checked: 11 tests over 9 sealed files; the independent model; the isolation claims; the listed limits; the relabelling from os.urandom with lines and sessions shuffled; the driver swap, the root-owned seal and the readability test (from reading the code).
   - Stated but not run by me: "Oracle scores 1, unfixed 0", "Fifteen one-edit mutants", "a contract-valid alternative scores 1". The mutants I did run behave as described.
6. **Hygiene.**
   - No TODOs, author names or host paths.
   - `.dockerignore` excludes solution/ and tests/.
   - Base image pinned by digest; pytest versions pinned.
   - The instruction is unchanged from the contract packet I reviewed in r1.
   - I found a `solution/__pycache__` directory, but my own import created it (its mtime is from this review), and I deleted it. The packet is clean again.

## Findings
- **SHOULD-FIX 1:** the "Fifteen one-edit mutants" and "Oracle 1 / nop 0" claims in `verification_explanation` rest on runs I cannot see. Keep the receipt next to the submission, or soften the wording if no receipt exists. Evidence: the claims are not reproducible from the packet; there is no mutant script.
- **SHOULD-FIX 2:** no Docker or Harbor oracle/nop run was part of this review. The verifier depends on `setpriv` (util-linux, present in Debian slim), on uid 65533/65534, and on `/app` arriving as an artifact under `environment_mode = "separate"`. Confirm with one real oracle and nop run before upload.
- **POLISH 1:** "one named test per rule" is loose. 2.3 has no named test of its own; it is exercised by every family.
- **POLISH 2:** the difficulty explanation's sentence "A hand-built reference fuzzed against the package will not flag the difference" is vague. Consider saying that fuzzing a clamping rewrite against the shipped code on over-allowance lines only will not flag it.
- **POLISH 3:** the reference patch's `if over <= 0` branch is not a new guard. It reproduces today's `over * rate` and is equivalent to the tiered formula there, so the fuzz is identical. It may still read as a guard to a reviewer, and a one-line comment would help.
