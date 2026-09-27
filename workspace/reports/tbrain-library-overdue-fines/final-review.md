# Final review: tbrain-library-overdue-fines (final-packet)

I read only `final-packet/`. All Python ran in a scratch copy, and the packet has no `__pycache__` or `.pyc`.

## Verdict
No BLOCKING issue. One SHOULD-FIX: the cap test has no loan whose fine lands exactly on the replacement cost, and both the instruction and task.toml say that case is covered. Everything else checks out.

## Checks
| Check | Result |
|---|---|
| `fix.patch` from `/` (`patch -p1`, as `solve.sh` runs it) | applies cleanly (dry run, then real) to `app/src/finebook/{dates,fines}.py` |
| Patched package == sealed statements | 0 mismatches across all 9 files (18 return files, 290 loans) |
| `model.statement` == sealed statements | 0 mismatches |
| ROSTER | all 9 SHA-256 sums OK; the row counts match |
| `tests/shipped/app` == `environment/app` src + driver | byte-identical |
| instruction.md | identical to the one in contract-packet-r1 |

## Findings

### SF-1 SHOULD-FIX: no graded fine lands exactly on the replacement cost
Promised in instruction.md ("fines that ... reach it exactly") and in task.toml verification_explanation ("fines short of, exactly on and past the replacement cost"). Sealed `03-cap.jsonl`:
- C2 DVD 2000 to 2030, daily 100, repl 2000. The span 2008..2030 has 4 Sundays (2008, 2015, 2022, 2029), so late 19, fine **1900**. That is short of the cost, not on it.
- C6 BOOK 2000 to 2022, daily 150, repl 150. Return day 2022 is a Sunday, so late 0, fine **0**. This one was meant to sit exactly on the cap.

I counted over all families: no late loan has late*daily == replacement. The case does not add discrimination (a `min` versus a `>`/`>=` cap branch gives the same output). But a coverage promise is unmet and an explanation is false.
Fix: in `jobgen.cap()` set C2 replacement to 1900 and C6 `after` to 23 (late 1, fine 150 == 150), then rerun `seal.py`. The ROSTER changes, and the tests need no edit.

### Coverage I verified as met (from the sealed data)
- All three kinds appear. Returns on the borrowing day, before the due day and on it appear (not_late, together).
- A return one day after the due day appears for each kind: BOOK/DVD in loan_period, JOURNAL in J1.
- Returns come 180 days after borrowing, due days and return days fall on Sundays, and late spans cross 0, 1 and many Sundays. One span is a single Sunday (S2, C6).
- Fines stop short of the cap and go past it. Daily fines 1..500 and costs 100..20,000 include both ends. There are 200 loans, borrowing days 0 and 3650, and ids of 1 and 10 characters.
- The order of the loans and the total are checked.

### Kept figures: graded and kept apart
- `test_journal_keeps_todays_loan_period` (J1: the fixed package says due 1014, late 1; a 21-day journal gives a loan that is not late). `test_loan_not_late_keeps_todays_late_days_and_fine` (N1..N7: late -21..0 with negative fines; a clamp to 0 fails). `together` combines both.
- Isolation is enforced twice, by `silent() <= GRADES[family]` in `seal.py` and in `test_outputs.load()`. No journal or loan that is not late sits in any other family: limits and generated contain only late books and DVDs, and the journal family's journals are all late.

### task.toml explanations
- True: there are 11 tests (counted) over 9 files. The limits, the relabel with `os.urandom`, the uid separation, the driver swap and seal, and the read-denial test all match the code. solution_explanation matches the patch.
- False: "exactly on ... the replacement cost" (see SF-1).
- Not reproduced here (a claim only, no artifact in the packet): Oracle 1 / nop 0, "fifteen one-edit mutants", and the "contract-valid alternative". POLISH: keep the evidence outside the packet or soften the wording.

### Hygiene
- No `__pycache__`, `.pyc` or `.DS_Store`. `.dockerignore` excludes solution/ and tests/.
- The verifier image pins pytest and ctrf. `/tests` has mode 700, and `setpriv` is in bookworm's util-linux.
- The driver is untouched by the patch, and `test.sh` also runs `cmp` on it.
