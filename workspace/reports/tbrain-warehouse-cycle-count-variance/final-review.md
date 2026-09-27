# Final review — tbrain-warehouse-cycle-count-variance (frozen folder)

Verdict: the task is correct and sound, with one packaging blocker (hygiene), and it is otherwise ready.

## Findings

1. **BLOCKING (hygiene) — `solution/__pycache__/` is shipped.**
   Files: `solution/__pycache__/jobgen.cpython-311.pyc` and `solution/__pycache__/model.cpython-311.pyc`.
   Reproduce: `find <task> -name __pycache__`.
   Fix: delete them before zipping.

2. **SHOULD-FIX (instruction promise vs tests) — instruction ¶3 says graded sheets "include every class letter", but the tests use only A B C D E N Q X Z.**
   A candidate that special-cases, say, class `F` would pass. That would be an odd bug, so the risk is low. Either add a sheet in `other_classes` that uses all 23 other letters, or soften the sentence.

3. **POLISH — no line of another class has status "recount".** The families `06-other_classes` and `08-together` contain only "ok" and "adjust" lines for classes D–Z. The routing is generic code, so this is low risk, but it is one untested cell of rule 3.1 × the kept tolerance.

4. **POLISH — `tests/test_outputs.py:129-146` has an unused path.** `report(..., shipped=True)` is never called. `_install_shipped` (line 68) is used only as a probe target in `test_candidate_cannot_read_verifier_state`. This is dead weight; either remove it, or explain why it is kept.

5. **POLISH — neither `10-limits` nor `09-generated` contains a "recount" status line or a line without a recount.** Status coverage for those cases comes only from the named families. This is acceptable.

## Checks passed (with evidence)
- **Patch.** `patch -p1 --dry-run` applies cleanly from `/` (solve.sh does `cd /`, and the paths are `app/...`). `patch` is installed in `environment/Dockerfile`.
- **Model = sealed expectations = patched package.** In a scratch copy, all 16 sealed rows equal `model.report` and the patched `variance_report`. All ROSTER SHA-256 sums match.
- **Fuzz.** I ran 3,000 random sheets: classes ABCDZQ, systems including 0/19/49/50/70/250/350/1049/100000, recounts or null, costs from 1 to 1e6. The patched package equals the model on every one.
- **The two kept figures are correct and discriminated.** For other classes, the kept tolerance is `round(system*5/100)` (250 → 12, 350 → 18). For lines that are not adjusted, booked is `count - system`. Mutants I ran against the sealed files with the verifier's comparison rules:
  - floor for other classes fails 06 and 08;
  - 0 for other classes fails 06 and 08;
  - half-up for other classes fails 06 and 08;
  - booked = variance on every line fails 07;
  - booked = 0 when not adjusted fails 07 and 08;
  - booked = 0 on "recount" lines only fails 07.
  Every other family ignores booked on non-adjusted lines and contains no other classes. That isolation matches `GRADES` (test_outputs.py:42 and 193) and the load guard (line 174).
- **Rule → test traceability.**
  - 2.1 → `recounts`
  - 2.3/1.2 → `graded_tolerance` (fractions at 19, 49, 119 and 1049, on the edge and one past)
  - 2.4 edge → within families
  - 3.1 → `status`
  - 3.2 and order → `value_and_order`
  - 3.3 (adjusted) → compared in every family
  - 3.4 → `shrink`
  - 1.3 → `limits` (300 lines, 0 and 100000, costs 1 and 1e6)
  - driver byte-identity → `test_submitted_driver_unchanged` plus the `cmp` in test.sh
  Every test traces to a visible sentence.
- **Comparator.** It checks exact int or str types, the README keys, and line order, and ignores extra keys. It never rejects contract-valid output. The one place it ignores a field (booked on non-adjusted lines outside 07 and 08) is lenient, not strict.
- **Isolation.** A separate verifier image is used. `/tests` and `/logs/verifier` are 0700. The candidate runs as uid 65534 with `setpriv --no-new-privs`, `env -i`, `python3 -I -S`, and its own session with the process group killed afterwards. `/app` is sealed root-owned before any run. The verifier's own copy of the driver is `os.replace`d onto the documented path. A readability probe with a positive control is included.
- **Determinism.** The expectations are sealed. Relabelling uses a urandom seed, but it relabels expected and input identically (unique SKUs via a set, one shuffle applied to both), so the outcome does not depend on the seed. The seed is printed on failure.
- **task.toml.** Its counts match the files: 12 tests over 10 sealed files; fractional tolerances at 19/49/119/1049 and half-units at 250/350 are present; 300 lines, 0/100000 and costs 1/1e6 are present. The "sixteen mutants" claim could not be recounted from the files, but the six I ran behave as described. The verifier timeout is 1800 and the internal DEADLINE is 1500, which is consistent.
- **Unfixed package scores 0.** The shipped code, for example, ignores the recount, which the `recounts` family catches.
