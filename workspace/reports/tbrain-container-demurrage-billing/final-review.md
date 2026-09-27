# Final review: tbrain-container-demurrage-billing (final-packet)

Scope: final-packet/ only. Checks were run in a scratch copy.

## Verdict: no BLOCKING and no SHOULD-FIX findings. POLISH only.

### Checks
1. **fix.patch.** Copied environment/app to <root>/app and ran `patch -p1 --dry-run`, then the real patch. Both hunks apply cleanly (charges.py, dwell.py). The patched package's `statement` equals `model.statement` for every sealed row (0 mismatches across all 9 files). The driver is untouched.
2. **Seal and ROSTER.** All 9 SHA-256 digests and row counts match ROSTER. Every sealed statement equals `model.statement(release)`. Re-running `solution/seal.py` in the scratch copy gives a `tests/expected` that is byte-identical to the frozen one. tests/shipped/app equals environment/app (src and driver) byte for byte.
3. **Kept figures graded and isolated.**
   - Tank: family `05-tank` has TANK dwell 6 → days 1, which separates free 5 from 3 or 0. Dwell 10 → days 5 and 121 → 116 exercise the higher rate on a tank.
   - Inside free time: `06-not_on_demurrage` has 6 idle containers, including 2 picked up on the discharge day, 2 exactly on their last free day (days 0), and rates of 1 and 100,000. This catches any clamp at 0.
   - `07-together` holds tanks inside free time.
   - Isolation is enforced twice, by `seal.py` (assert) and by `load()` in the tests (`silent(x) <= GRADES[family]`). My tally confirms no TANK and no idle container appears in any other family. A candidate that errs on one kept figure therefore fails only that figure's test (and `together`).
4. **Coverage promises.** Every promise in the instruction has a sealed witness:
   - all three types;
   - pickup on the discharge day (06);
   - inside free time (06, 07);
   - exactly on the last free day (06, 07);
   - just past it, days 1 (01, 02, 03, 04, 05, 09);
   - up to 120 days later, span 120 (01, 02, 05, 09);
   - fewer than 4 demurrage days, exactly 4 (03, 08) and more;
   - rates of 1 and 100,000;
   - 1 to 200 containers (09 has 200);
   - discharge days 0 and 3650;
   - ids of 1 and 11 characters (04, 09).
5. **task.toml.** The claims I could check are true: 11 tests over 9 sealed files; the model never imports the package; the tank and idle families are isolated; limits test (200 containers, days 0 and 3650, stays of 1 and 121, rates 1 and 100000, ids of 1 and 11); the relabel uses os.urandom; the driver is replaced and /app sealed; there is a separate verifier image; and there is a readability test. The difficulty and solution explanations match the patch and the model.
6. **Hygiene.** No __pycache__, .pyc, .DS_Store or caches anywhere in the folder. The `.dockerignore` excludes caches, solution/ and tests/.

### POLISH
- **P1:** the explanation says the named files hold "demurrage of 3, 4, 5 and more days". The higher_rate family has days {1, 4, 4, 5, 5, 40}. Exactly 3 is not in that file, although other families have lt4 cases. Either add a 3-day box to 03 or reword the claim.
- **P2:** the claims that the Oracle scores 1, the unfixed package 0, the "thirteen one-edit mutants" and the contract-valid alternative cannot be checked from this packet. Nothing contradicts them, but I did not run them (no Docker).
- **P3:** `_install_shipped()` and `run(shipped=True)` build a shipped-package runner that no test uses except the readability probe. This is dead code; it is harmless.
- **P4:** the silent-figure helpers (`silent` and `within_limits`) are duplicated in seal.py, model.py and test_outputs.py. They agree today, but they could drift apart.
- **P5:** test.sh relies on `setpriv` (util-linux) being present in python:3.13-slim-bookworm. It normally is, but a one-line `command -v setpriv` check would make a failure louder.
