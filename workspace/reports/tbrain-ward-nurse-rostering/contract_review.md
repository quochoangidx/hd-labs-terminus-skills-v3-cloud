## Findings

1. **Should-fix — The shipped planner is described incorrectly.**  
   Citation: `instruction.md:1`, `environment/app/planner/plan_ward.py:4`, `environment/app/planner/plan_ward.py:6`, `environment/app/planner/plan_ward.py:51`  
   The instruction and planner docstring say nurses with the fewest worked hours are selected and contracts are ignored. The implementation sorts by `worked[nid] - max_hours`, so it explicitly uses contract maxima and prioritizes nurses furthest below their maximum, not necessarily those with the fewest hours. This may mislead a solver analyzing the baseline.  
   **Smallest fix:** Describe the planner as selecting nurses “furthest below their `max_hours`” and remove the claim that it ignores contracts.

2. **Advisory — The required JSON container shape is shown but not stated explicitly.**  
   Citation: `environment/app/docs/roster-rules.md:67`, `environment/app/docs/roster-rules.md:69`, `environment/app/tools/check_roster.py:18`  
   The example implies a top-level object containing a `"roster"` object, while the checker explicitly rejects every other container shape.  
   **Smallest fix:** Add: “The file must be a JSON object whose `roster` key contains a JSON object.”

3. **Advisory — “Every nurse appears once” is enforced only after JSON parsing.**  
   Citation: `environment/app/docs/roster-rules.md:71`, `environment/app/tools/check_roster.py:22`  
   Python’s JSON parser silently retains the last occurrence of a duplicate textual key, so duplicate nurse keys in the source file are not detected. This has no scoring advantage because only the final value survives.  
   **Smallest fix:** Say “Every nurse must be present as a key in the parsed `roster` object,” or use duplicate-key detection while loading JSON if textual uniqueness matters.

No substantive disagreement was found between the rules and checker for:

- Cover, registered-grade requirements, senior coverage, and preferred-cover penalties: `environment/app/docs/roster-rules.md:24`, `environment/app/docs/roster-rules.md:34`, `environment/app/tools/check_roster.py:39`
- Leave: `environment/app/docs/roster-rules.md:37`, `environment/app/tools/check_roster.py:57`
- Inter-day rest: `environment/app/docs/roster-rules.md:38`, `environment/app/tools/check_roster.py:60`
- Consecutive days: `environment/app/docs/roster-rules.md:40`, `environment/app/tools/check_roster.py:64`
- Post-night rest, including runs ending on the last day: `environment/app/docs/roster-rules.md:42`, `environment/app/tools/check_roster.py:69`
- Hours, nights, weekends, lone days, and requests: `environment/app/docs/roster-rules.md:51`, `environment/app/tools/check_roster.py:75`
- Missing/unknown nurses, row length, codes, and ignored top-level keys: `environment/app/docs/roster-rules.md:67`, `environment/app/tools/check_roster.py:18`

The boundary conventions are adequately specified: day 0 is Monday, nights belong to their starting day, weekends are Saturday/Sunday pairs, nothing outside the period counts, and first/last days cannot incur lone-day penalties.

### Hand-Checked Witnesses

All tool results agreed with the text:

| Witness | Text-implied result | `check_roster.py` result |
|---|---|---|
| Add unknown nurse `ZZZ` to Ash | Invalid | `unknown nurse 'ZZZ'` |
| Omit Ash nurse `A01` | Invalid | Expected a 28-character string |
| Give `A02` a 27-character row | Invalid | Expected a 28-character string |
| Put code `X` in `A02`’s row | Invalid | Unknown shift code |
| Assign `A01` an early on leave day 9 | Invalid | Nurse is on leave |
| Give `A01` `N` on day 1 and `E` on day 2 | Invalid rest transition | “too little rest” |
| Give `A01` at least seven consecutive working days | Invalid after day 6 | More than six days in a row |
| Give `A03` the prefix `N.E` on days 0–2 | Invalid: day 2 is within two rest days after the night | “too soon after the nights ending day 0” |
| In Ash, add `L` versus `E` for `A06` on requested-off shift `L`, day 15 | The `L` version costs exactly 25 more | Penalties 5307 versus 5282 |
| In Dale, change `D01`’s final Sunday, day 27, from off to `L` | No lone-day penalty at the edge; removes one preferred-cover shortage and one split weekend: −60 | Penalty falls from 12287 to 12227 |

The supplied planner generated valid rosters for all four wards. Their penalties were Ash 5313, Birch 12003, Cedar 9002, and Dale 12287, all above their targets as intended. Paths and ward names are consistent, and the instruction clearly neutralizes edits to the visible checker, wards, or targets by stating that the grader uses its own copies and grades only the four roster files. No practical environment shortcut was found.

## Verdict

accept with fixes