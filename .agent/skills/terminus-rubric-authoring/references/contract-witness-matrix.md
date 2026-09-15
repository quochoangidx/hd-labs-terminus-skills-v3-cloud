# Contract-witness matrix

Use this matrix before drafting rubric prose. It is an analysis artifact, not a file
that belongs in the submission ZIP.

## Required columns

| Column | Meaning |
|---|---|
| `contract_id` | Stable local identifier such as `commit_instruction_word` |
| `source` | Agent-visible file and section or line that establishes the promise |
| `observable_requirement` | Outcome visible through the documented public surface |
| `witness_ids` | Exact independently reported cases that can fail for this behavior |
| `discrimination` | The plausible partial fix or shortcut the witnesses reject |
| `coverage` | `covered`, `partial`, or `uncovered` |
| `criterion_id` | Rubric criterion that scores the behavior, or blank while blocked |

## Coverage decisions

Mark a row `covered` only when at least one case changes outcome if that behavior is
removed or implemented incorrectly. These do not qualify by themselves:

- the driver prints a field but no assertion checks its value;
- a mode is compiled but never run on an input that distinguishes it;
- load overlap is tested and used as evidence for store overlap;
- a normal stall case and a normal interrupt case are used as evidence for their
  untested interaction;
- one configuration passes and is used to claim all configurable implementations;
- a preservation fixture never attempts the state change it claims to prevent.

Use `partial` when some named variants or interactions are discriminated and others
are not. Keep every missing variant explicit. Do not convert a partial row to covered
by replacing a precise task promise with a broader rubric phrase.

## Criterion construction

Positive criteria should correspond to semantic nodes or real interactions rather
than file locations or test-family names. Split a criterion when a natural partial
implementation can earn one part without the other. Combining several fixtures of
the same mechanism is fine; combining unrelated mechanisms merely to reach `+5` is
not.

Negative criteria need an observable failure and a witness. Good reasons to split
them include independently possible data corruption, unsafe side effects, replay,
wholesale feature disablement, and cross-entity contamination. Do not split synonyms
or the immediate consequences of one bug into multiple deductions.

## Final audit questions

Before marking the rubric ready, answer all of these:

1. Does every explicit public output and exact field have a criterion or belong to a
   clearly named parent criterion?
2. Does every preservation promise have a fixture that tries to violate it?
3. Does every documented mode execute on a discriminating input?
4. Are cross-component interactions witnessed as interactions rather than inferred
   from separate happy paths?
5. Can two negative criteria fire from one root failure? If so, is the double
   deduction deliberate and proportionate?
6. Would the same criterion wording make sense on three unrelated tasks? If yes,
   replace generic language with the actual public behavior.
7. Across the current submission set, did criterion count, negative count, verb
   sequence, or score distribution repeat because of evidence or because of a
   template?

