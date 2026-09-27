# Final review — tbrain-car-rental-agreement-billing (r3 contract)

## Findings

1. **BLOCKING — there is no `solution/solve.sh`.** The `solution/` folder holds only `fix.patch`, `model.py`, `seal.py`, `jobgen.py` and `__pycache__/`. Nothing applies `fix.patch` to /app, so the Harbor Oracle run has no entry point. task.toml's verification_explanation claims "Locally the Oracle scores 1", which cannot be true of this folder as it stands.
   Reproduction: `ls solution/`.
   Fix: add `solution/solve.sh` that applies the patch from /app's parent, since the patch paths are `a/app/src/...`. For example: `cd / && patch -p1 < /solution/fix.patch`, or `cd /app && git apply -p2 ...`. Then re-run oracle and nop.

2. **SHOULD-FIX — stray `solution/__pycache__/`** (`jobgen.cpython-311.pyc`, `model.cpython-311.pyc`). This is packaging hygiene. Delete it before zipping.

3. **POLISH — dead code in `tests/test_outputs.py`: `_install_shipped()` / `SHIPPED_RUN` and the `bill_run(shipped=...)` branch.** No test calls `shipped=True`. The shipped copy is used only as a target in the unreadability probe (test_candidate_cannot_read_verifier_state). It is harmless, but it chowns a tree to uid 65533 for nothing. Either drop it or use it (e.g. a check that the unfixed package fails each named family).

4. **POLISH — task.toml numbers I cannot check from the folder.** "Twenty-two one-edit mutants" and "Two contract-valid alternatives score 1" have no artifact in the task folder, so I could not confirm them. The checkable claims do match: 15 tests (counted `def test_` = 15), 13 sealed files (ROSTER has 13 lines), the listed lengths (short_days 1/30/59/60/1439; grace 4320/4379/4380/4381 etc.; limits file of 200 agreements; 86,400-minute rental present), and taxes of half cents.

## Checks that passed
- **Patch vs model.** I applied `fix.patch` to a scratch copy of environment/app; it applies cleanly. A 20,000-agreement fuzz inside rule 1.3 against `solution/model.py` gave 0 mismatches. The fuzz was weighted to 1–1500 minutes, whole days ±{1,0,59,60,61} minutes, turnover, all fuel pairs and full rate ranges.
- **Sealed expectations.** Every row in tests/expected/*.jsonl equals `model.report(...)`, and equals the patched package's output. The ROSTER digests match the files.
- **Model vs manual.** Grace (n//1440 + (n%1440>59) for n≥1440), 150 per day charged, turnover +1,000,000 when in<out, fee only when short, tax on time+mileage with an exact half-up via Fraction, and file totals are all correct. Both kept figures mirror the shipped code: days for a rental under a day = ceil = 1, and fuel for a car back full or fuller = (out−in)×rate with no fee, which gives a credit. The model and patch each say so in a comment.
- **Test → contract tracing.** Each named test maps to a manual rule or to the silence sentence. The limits test maps to 1.3, the order test to the README, and the driver test to the instruction's byte-for-byte sentence. Every rule has a discriminating family: grace at 59/60/61 minutes past a day, allowance met and passed by a mile, turnover at 999,999, refuelling fee, fuel untaxed, half-cent tax. `silent_inputs` keeps short and fuller rentals only in the families that grade them. Equal fuel appears elsewhere, but it gives 0 under every reading, so that is fine.
- **Comparator.** It checks only the README keys, with an exact int type (`type(actual) is type(expected)`), and ignores extra keys. JSON integers parse as int, so it never rejects contract-valid output. Bill order is compared positionally, as the README promises. The relabel moves times by whole weeks, which leaves lengths unchanged, and shuffles order with the expected bills following. That is valid.
- **Isolation and privilege.** The verifier runs in a separate image and seals /tests and /logs/verifier with mode 700. The candidate runs as uid 65534 via `setpriv --no-new-privs`, with `env -i` and `python3 -I -S`, in its own session with its process group killed. /app is lchown-ed to root and made unwritable, and the verifier's driver is `os.replace`d onto the path first. The reward also requires a `cmp` of the driver after the run. There is an unreadability probe with a positive control.
- **Determinism.** Expected files are sealed. The only runtime randomness is the relabel seed from os.urandom, which is printed on failure and cannot change a correct package's outcome.
- **Dockerfiles.** Both are digest-pinned, and pytest is installed only in the verifier image. `.dockerignore` excludes solution/ and tests/. The environment Dockerfile is fine.
