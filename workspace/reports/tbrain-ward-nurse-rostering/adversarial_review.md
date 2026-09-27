Created **15 wrong** and **2 valid** roster submissions under `submissions/`. Ran the requested ward-specific pytest validity test for each.

| Submission | Ward | Rule broken / why valid | Expected | Observed |
|---|---|---|---|---|
| `wrong-cover-minimum` | ash | Late shift day 26 below minimum cover | Reject | Reject |
| `wrong-cover-registered-hca` | ash | HCA incorrectly substituted for required registered nurse | Reject | Reject |
| `wrong-cover-no-senior` | ash | Night shift day 0 has no senior | Reject | Reject |
| `wrong-leave` | ash | A01 works on leave day 10 | Reject | Reject |
| `wrong-between-day-rest` | ash | Late followed by early | Reject | Reject |
| `wrong-after-night-rest` | ash | Work resumes too soon after opening night run | Reject | Reject |
| `wrong-consecutive-days` | ash | Seven consecutive working days | Reject | Reject |
| `wrong-lowercase-code` | ash | Lower-case `e` shift code | Reject | Reject |
| `wrong-short-row` | ash | A07 has only 27 day codes | Reject | Reject |
| `wrong-row-type` | ash | A01 row is an array, not a string | Reject | Reject |
| `wrong-missing-nurse` | ash | A01 omitted | Reject | Reject |
| `wrong-unknown-nurse` | ash | Unknown nurse AXX included | Reject | Reject |
| `wrong-nan` | ash | Ignored field contains non-standard `NaN` | Reject | Reject |
| `wrong-oversize` | ash | File is 2,000,625 bytes | Reject | Reject |
| `wrong-duplicate-nurse-key` | ash | Conflicting duplicate A01 object members | Reject | **Accept** |
| `valid-exact-size-extra-keys` | ash | Exactly 2,000,000 bytes; ignored keys; roster key last | Accept | Accept |
| `valid-deep-ignored-key` | ash | Deeply nested ignored top-level value; valid roster | Accept | **Reject** |

## Findings

1. **Duplicate nurse keys are silently accepted.**  
   `submissions/wrong-duplicate-nurse-key/ash.json:1` contains two conflicting `A01` members. `json.loads` silently keeps the last value, so the grader passes an ambiguous roster.
   - Smallest fix: load with an `object_pairs_hook` that raises `RosterError` when any object contains duplicate names.

2. **Deep ignored values cause a false rejection.**  
   `submissions/valid-deep-ignored-key/ash.json:1` is valid JSON below the byte limit, and the rules say other top-level keys are ignored. The grader instead leaks an unhandled `RecursionError`.
   - Smallest contract change: document a maximum JSON nesting depth and convert `RecursionError` into `RosterError`.
   - Contract-preserving fix: parse top-level members iteratively so ignored values can be skipped without recursive decoding.