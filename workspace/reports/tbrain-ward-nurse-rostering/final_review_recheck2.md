# Final review, second recheck: tbrain-ward-nurse-rostering

This is a targeted recheck of the refreshed packet against the "Recheck" section at the end of `prior/final-review-adjudication.md`. I read only files inside the working directory and edited nothing. Scratch files went to the session scratchpad.

## Checks

- **Both checker copies are identical, and so are the inputs.** `cmp` finds `tests/check_roster.py` and `environment/app/tools/check_roster.py` byte-identical. The same holds for `targets.json` and all four ward files.
- **The reference still passes.** The reference rosters score 450, 1070, 830 and 1665, exactly on target. The pytest suite on the reference passes 8/8.
- **The digit rule now matches the checker** (`environment/app/docs/roster-rules.md:77-79` against `check_roster.py:10,21,28-39,65-66`).
  - The rules say no number "may be written with more than 4300 digits (counting every digit, including those after a decimal point or in an exponent)".
  - The checker enforces this with `parse_int=_int` and `parse_float=_float`. Both first call `_digits`, which counts every ASCII digit in the number's text; a sign, a decimal point and an exponent marker are not counted. Above `MAX_DIGITS = 4300` it raises `RosterError("a number is written with more than 4300 digits")`.
  - I put each number in an ignored top-level array next to the valid Ash reference roster and ran the grader's copy of the checker:

    | Form | 4300 digits | 4301 digits |
    |---|---|---|
    | integer | valid, 450 | refused, stated message |
    | negative integer | valid, 450 | refused, stated message |
    | fraction `1.000…` | valid, 450 | refused, stated message |
    | exponent `1e000…` | valid, 450 | refused, stated message |
    | `-1.5E-000…` | valid, 450 | refused, stated message |
    | mixed (1000 before the point, 1000 after, the rest in the exponent) | valid, 450 | refused, stated message |

  - The results are identical with `PYTHONINTMAXSTRDIGITS` unset, set to `0` and set to `640`.
  - `sys.set_int_max_str_digits(4300)` at `check_roster.py:10` pins the limit, and `sys.get_int_max_str_digits()` reports 4300 in all three runs.
  - Because `_digits` runs before `int()`, the refusal comes from the stated `RosterError`, not from Python's own `ValueError`.
- **My placement advisory is handled.** The digit limit is no longer inside the "(so …)" parenthesis that follows "standard JSON". It now sits in its own sentence next to the 2,000,000-byte limit (`roster-rules.md:77-79`). The parenthesis now lists only the byte-order mark, `NaN` and `Infinity`, all of which do follow from standard JSON.
- **Nothing else in the changed lines is wrong.**
  - The `RosterError` raised inside the parse hooks leaves `json.loads` unchanged: it is not a `ValueError`, so the `except` at line 67 does not re-wrap it.
  - The pinned limit is a process-wide side effect when the grader imports the checker. It is harmless, because the grader parses no other large integers.
  - The first recheck's findings no longer apply.

## Findings

1. **Advisory: one line in the rules is much longer than the others.**
   - Citation: `environment/app/docs/roster-rules.md:79`.
   - The line is 97 characters, while the rest of the file wraps at about 79. "...exponent). No object in it may give the same name twice, and" was not reflowed after the edit.
   - It is purely cosmetic; the rendered Markdown is unaffected.
   - **Smallest fix (optional):** rewrap the paragraph.

No Blocking or Should-fix findings remain.

## Verdict

accept
