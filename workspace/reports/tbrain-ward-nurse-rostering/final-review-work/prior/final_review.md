# Final review: tbrain-ward-nurse-rostering

I read every file in the frozen snapshot and ran the grader's checker and pytest suite locally (Python 3.13.2, pytest 9.1.1) against the reference rosters, the shipped planner's rosters and hand-made wrong and valid files. I edited no task file. Scratch files went only to the session scratchpad.

## Summary of checks

- **Earlier findings.** All resolved as the adjudications say.
  - Contract finding 1: `instruction.md:1` and `environment/app/planner/plan_ward.py:4-7` now say the planner picks whoever is "furthest below their maximum hours". This matches the sort at `plan_ward.py:52`.
  - Contract finding 2: `roster-rules.md:71` now states the container shape.
  - Contract finding 3: duplicate names are now rejected (`roster-rules.md:77`, `check_roster.py:25-31`).
  - Adversarial finding 1 (duplicate keys): rejected with a stated message, including a repeated `"roster"` key and a repeat inside ignored values.
  - Adversarial finding 2 (depth): nesting of 64 levels is accepted and 65 is rejected with the stated message (`check_roster.py:34-41,54-56`).
- **Grader copies match the agent's.** `tests/check_roster.py`, `tests/targets.json` and `tests/wards/{ash,birch,cedar,dale}.json` are byte-identical to their `environment/app/` counterparts (`cmp`). This snapshot has no split-file manifest. The ward files are stored whole, so there was nothing to reassemble.
- **Reference.** The reference rosters score exactly their targets: ash 450, birch 1070, cedar 830, dale 1665. `tests/targets.json` matches `environment/app/wards/targets.json`. The pytest run on the reference passed 8/8.
- **Wrong work is rejected.**
  - The shipped planner's rosters are valid, score 5313, 12003, 9002 and 12287, and fail all four target tests.
  - A cedar roster with one hard-rule breach fails; a missing dale file fails.
  - A list container, a BOM, trailing commas, Latin-1 bytes, `-Infinity`, an empty file and a 2,000,001-byte file are all rejected with stated reasons.
- **Valid work is accepted.**
  - Reordered nurse keys plus extra top-level keys are accepted.
  - A file of exactly 2,000,000 bytes is accepted.
  - Nesting 64 levels deep is accepted.
- **Contract against checker.** Hard rules 1-5, every penalty term and the edge conventions agree with `check_roster.py:84-146`: nights count on their start day, rest after nights applies only to days that exist, lone days never count on the first or last day, and weekends are Saturday plus Sunday. All wards have 28 days, so no weekend is cut short.
- **Isolation and determinism.**
  - The grader imports only `/tests/check_roster.py` and `/tests/wards`, reads `/app/rosters/*.json` as data and runs no `/app` code (`test_outputs.py:15-36`).
  - `environment_mode = "separate"` is set.
  - Nothing depends on time, randomness, the network or test order.
  - Editing `/app/tools`, `/app/wards` or `targets.json` cannot change the grade.
- **`task.toml` claims.**
  - "16-36 nurses" is correct.
  - "7-12 times the target" is correct (7.4x to 11.8x).
  - The planner scores and targets quoted in `verification_explanation` are correct.

## Findings

1. **Should-fix: a valid, in-limit JSON file is falsely rejected by an unhandled exception.**
   - Citation: `environment/app/tools/check_roster.py:50-53` (same in `tests/check_roster.py:50-53`); contract at `environment/app/docs/roster-rules.md:74-79`.
   - An ignored top-level key holding an integer with more than 4300 digits (for example `{"x": 1000…0, "roster": {...}}`, far below 2,000,000 bytes and standard JSON) makes `json.loads` raise `ValueError: Exceeds the limit (4300 digits) for integer string conversion`.
   - That exception is not caught. The tool crashes with a traceback, and in the grader the validity test errors, which counts as a rejection. The rules promise that such a key is ignored, and no stated limit covers it.
   - This is the same kind of gap as adversarial finding 2 (RecursionError). An agent is unlikely to hit it, but it is a real disagreement between the contract and the grader.
   - **Smallest fix:** in both copies of `load_roster`, catch `ValueError` together with `JSONDecodeError`. `JSONDecodeError` is itself a subclass of `ValueError`, so `except (UnicodeDecodeError, ValueError)` covers both. Then add one clause to `roster-rules.md:78-79`, for example: "and a number may have at most 4300 digits". The alternative is to pass `parse_int=float` (or a parser that ignores the value), since no roster field is a number. Afterwards, recheck that the two copies are byte-identical.

2. **Advisory: a UTF-8 BOM is rejected but not mentioned.**
   - Citation: `roster-rules.md:76`, `check_roster.py:51`.
   - "Standard JSON in UTF-8" arguably excludes a BOM (RFC 8259 §8.1 says a BOM must not be added), so the rejection is defensible. The message is clear.
   - **Smallest fix (optional):** add "(no byte-order mark)" after "UTF-8".

3. **Advisory: a `task.toml` claim cannot be checked against the files.**
   - Citation: `task.toml:14`.
   - "fresh long anneals beat every restart on the two largest wards" is a provenance claim. No file in the task supports it, and `solution/solve.sh:9-10` describes the runs more loosely ("single runs of one to four hours").
   - It is harmless, but a platform reviewer who checks explanation claims against files may flag it.
   - **Smallest fix:** drop the parenthetical, or keep it consistent with the `solve.sh` comment.

4. **Advisory: cosmetic whitespace.**
   - Citation: `environment/app/docs/roster-rules.md:56`.
   - The line ends with a space ("the Sunday after it), ").
   - **Smallest fix:** remove the space.

No problems with category or subcategory (`Software` / `Algorithms` fits a combinatorial scheduling search), paths (every path in `instruction.md` and `README.md` exists in the image layout), or the Python version claim (the image is `python:3.13-slim`).

## Verdict

accept with fixes
