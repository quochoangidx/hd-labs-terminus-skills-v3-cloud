# Final review recheck: tbrain-ward-nurse-rostering

This is a targeted recheck of the refreshed packet against `prior/final_review.md` and `prior/final-review-adjudication.md`. I read only files inside the working directory and edited nothing. Scratch files went to the session scratchpad.

## Checks

- **Both checker copies are identical, and so are the inputs.** `cmp` finds `tests/check_roster.py` and `environment/app/tools/check_roster.py` byte-identical. The same holds for `targets.json` and all four ward files.
- **The reference still passes.** The reference rosters score 450, 1070, 830 and 1665, exactly on target. The pytest suite on the reference passes 8/8.
- **Finding 1 (uncaught `ValueError`) is resolved for integers.**
  - `check_roster.py:52` now catches `(UnicodeDecodeError, ValueError)` and raises `RosterError("the file is not valid JSON: ...")`.
  - I tested integers in an ignored top-level key:
    - 4300 digits: accepted, penalty 450.
    - 4301 digits: rejected with the stated error.
    - The same boundary holds with a minus sign (`-` plus 4300 digits accepted, plus 4301 digits rejected).
  - No traceback escapes.
- **Finding 2 (BOM) is resolved.** `roster-rules.md:76` now says "no byte-order mark". A file that starts with `EF BB BF` is rejected with a clear message.
- **Finding 3 (unsupported `task.toml` claim) is resolved.** The "fresh long anneals beat every restart" sentence is gone from `task.toml:14`. The rest of that field still agrees with `solution/solve.sh:9-10`.
- **Finding 4 (trailing whitespace) is resolved.** `roster-rules.md:56` no longer ends with a space. `grep ' $'` finds no trailing whitespace in `roster-rules.md`, `instruction.md` or `task.toml`.

## Findings

1. **Should-fix: the new digit limit says "number", but the checker enforces it only for integers.**
   - Citation: `environment/app/docs/roster-rules.md:77` against `environment/app/tools/check_roster.py:51` (same lines in `tests/check_roster.py`).
   - The rules forbid any number of more than 4300 digits. The checker only limits integers, because Python applies that limit when converting integer text; numbers with a fraction or exponent are read by `float` with no digit limit.
   - All three of these are accepted with penalty 450, although the sentence forbids them:
     - `1.` followed by 4300 zeros (4301 digits)
     - 5000 digits followed by `.0`
     - 4301 digits followed by `e0`
   - The contract now states a rule the grader does not enforce. The practical effect is nil, because these numbers can only appear in ignored keys and are accepted rather than refused. It is still exactly the kind of mismatch the review brief asks to catch.
   - **Smallest fix (wording only, checker unchanged):** change "no number of more than 4300 digits" to "no integer (a number without a fraction or exponent) of more than 4300 digits".
   - The alternative is to make the checker enforce the sentence for every number by passing a `parse_float` that checks the digit count. That changes both checker copies, which would then need the byte-identity recheck.

2. **Advisory: the "so" in the rules sentence claims too much.**
   - Citation: `roster-rules.md:76-77`.
   - The sentence reads "standard JSON in UTF-8 (so no byte-order mark, no `NaN` or `Infinity`, and no number of more than 4300 digits)". The "so" presents the digit limit as a consequence of standard JSON, but it is an extra limit of this checker. RFC 8259 sets no digit limit.
   - **Smallest fix:** move the digit limit out of the parenthesis and next to the other limits. For example: "..., at most 2,000,000 bytes long, with no integer of more than 4300 digits."

Nothing else in the changed lines is wrong:
- Catching `ValueError` also catches `JSONDecodeError`, which is a subclass of it. Unicode and constant errors are still reported as before.
- `RecursionError` is not a `ValueError`, so it still reaches its own handler at `check_roster.py:54-55`.

## Verdict

accept with fixes
