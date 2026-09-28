# Adversarial verifier review

Each observed verdict comes from the requested per-day command:

```text
cd tests && STAND_PLANS=../submissions/<name> python3 -m pytest -q test_outputs.py -k "<day_n>_plan_is_valid"
```

| Submission | Day | Rule broken or why valid | Expected | Observed |
|---|---:|---|---|---|
| `wrong-size` | day-1 | Turn `T002` is larger than stand `A08`. | Reject | Reject |
| `wrong-international` | day-2 | International turn `T047` is placed on non-international stand `B06`. | Reject | Reject |
| `wrong-buffer-boundary` | day-3 | `T092` arrives one minute before the 15-minute buffer after `T053` ends. | Reject | Reject |
| `wrong-wingtip-overlap` | day-4 | Size-3 turns `T030` and `T076` overlap on wingtip-paired stands `B16` and `B17`. | Reject | Reject |
| `wrong-duplicate-same-stand` | day-1 | Turn `T001` appears twice on stand `A01`. | Reject | Reject |
| `wrong-duplicate-two-stands` | day-2 | Turn `T006` appears on both `A01` and `A02`. | Reject | Reject |
| `wrong-missing-turn` | day-3 | Required turn `T291` is omitted. | Reject | Reject |
| `wrong-unknown-turn` | day-4 | Adds turn id `NO-SUCH-TURN`. | Reject | Reject |
| `wrong-unknown-stand` | day-1 | Adds stand id `NO-SUCH-STAND`. | Reject | Reject |
| `wrong-number-turn-id` | day-2 | Adds numeric turn id `123` instead of a JSON string. | Reject | Reject |
| `wrong-nested-list-id` | day-3 | Adds a nested list where a string turn id is required. | Reject | Reject |
| `wrong-root-list` | day-4 | Uses a list as the plan root instead of an object. | Reject | Reject |
| `wrong-stands-list` | day-1 | Uses a list for `stands` instead of an object. | Reject | Reject |
| `wrong-stand-value-object` | day-2 | Uses an object instead of a turn-id list for one stand. | Reject | Reject |
| `wrong-nan-token` | day-3 | Contains the non-JSON token `NaN` in an ignored top-level field. | Reject | **Accept** |
| `valid-unusual-order` | day-4 | Reverses stand/turn ordering, omits unused stands, retains an empty stand, and adds ignored top-level keys; all are explicitly permitted. | Accept | Accept |
| `valid-huge-whitespace` | day-1 | A valid plan with trailing JSON whitespace; the stated format has no byte limit. | Accept | **Reject** |

## Findings

- **Invalid JSON is accepted.** `wrong-nan-token` passes because Python's `json.load` accepts `NaN` by default and the checker ignores the containing extra top-level field. Smallest fix: load with a `parse_constant` callback that raises `json.JSONDecodeError` (or another caught validation error) for `NaN`, `Infinity`, and `-Infinity`.
- **An unstated size limit rejects a valid plan.** `valid-huge-whitespace` is rejected solely by `MAX_BYTES = 2_000_000`, although the file-format contract states no size bound and trailing whitespace is valid JSON. Smallest fix: remove the byte-limit assertion from validity checking; if a resource limit is required, state the exact limit in `stand-rules.md` and the task prompt.
