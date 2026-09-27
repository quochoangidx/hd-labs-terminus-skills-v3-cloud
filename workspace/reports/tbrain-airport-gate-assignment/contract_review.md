## Findings

1. **Should-fix — Duplicate stand keys are forbidden by the document but accepted by the checker.**
   - **Citation:** `environment/app/docs/stand-rules.md:62`; `environment/app/tools/check_plan.py:76`
   - The rules require each stand key “at most once.” However, `json.load()` silently keeps the last occurrence of a duplicate object key. For example, `{"stands":{"S1":[],"S1":["T1"]}}` was accepted as valid.
   - This does not appear to enable a useful shortcut, but it is a direct contract/checker mismatch.
   - **Smallest fix:** Parse the plan with an `object_pairs_hook` that rejects duplicate keys, or remove the “given at most once” requirement.

2. **Should-fix — Same-stand and remote-transfer walking costs are technically derivable but materially counterintuitive.**
   - **Citation:** `environment/app/docs/stand-rules.md:25`; `environment/app/docs/stand-rules.md:50`; `environment/app/tools/check_plan.py:66`; `environment/app/days/day-1.json:257`; `environment/app/days/day-1.json:1107`
   - The checker charges the matrix entry for every transfer, including transfers whose turns use the same stand. The supplied matrices have nonzero diagonals: contact stands commonly charge 40 metres, while a remote stand can charge 800 metres even to itself. Remote-to-remote transfers also incur this walking charge in addition to both turns’ bus costs.
   - A literal reading of the formula produces the checker’s result, but “walking distance from [a] stand to [the same] stand” would ordinarily be understood as zero.
   - **Smallest fix:** Add one sentence: “Use the matrix entry even when both turns use the same stand; remote-to-remote transfers use the remote matrix entry, and remote bus charges still apply separately.”

3. **Advisory — All other reviewed rule surfaces align.**
   - **Citation:** `environment/app/docs/stand-rules.md:31`; `environment/app/tools/check_plan.py:16`
   - Size, international eligibility, same-stand buffer equality, wingtip half-open overlap without a buffer, bus charges, transfer direction, unknown IDs, duplicate/missing turns, list ordering, omitted stands, and ignored extra top-level keys match the implementation.
   - Boundary behavior is sufficiently defined: `depart + buffer == arrive` is valid, and one widebody departing exactly when the neighboring widebody arrives does not clash.
   - **Smallest fix:** None.

4. **Advisory — Environment and feasibility checks passed.**
   - **Citation:** `instruction.md:1`; `instruction.md:3`; `environment/app/planner/plan_day.py:31`; `environment/app/days/targets.json:2`
   - All four named day files and target entries exist, `/app/plans` is created by the image, and only JSON plans are required. The instruction does not impose a construction-language restriction; it merely identifies Python 3.13 and its standard library as the available search environment.
   - Running the shipped planner in memory produced valid plans for all four days. Their costs were `9,077,225`, `12,189,855`, `14,519,325`, and `21,326,260`, respectively—above the targets, as expected for the baseline planner.
   - The visible files contain no target-achieving plan, so target attainability cannot be independently proven from the solver-visible contract alone, but nothing indicates infeasibility.
   - **Smallest fix:** None.

5. **Advisory — No useful visible bypass was found.**
   - **Citation:** `instruction.md:3`; `environment/app/tools/check_plan.py:18`; `environment/app/tools/check_plan.py:32`
   - Editing the supplied checker, planner, days, or targets cannot replace the four required plan files under the stated grading model. Unknown IDs, missing turns, and repeated turn placements are rejected. Extra top-level keys and duplicate raw JSON keys do not remove the requirement to provide one valid placement for every turn.
   - **Smallest fix:** Enforcing duplicate JSON keys as described in Finding 1 closes the only observed parser discrepancy.

### Witness Checks

| Witness | Text-implied result | Checker result |
|---|---:|---:|
| Same stand: first turn departs at 10, second arrives at 25, buffer 15 | Valid | Valid, cost 0 |
| Same stand: second arrives at 24 | Invalid | Invalid |
| Wingtip pair: size-3 turns meet exactly at minute 10 | Valid; no buffer | Valid |
| Wingtip pair: second size-3 turn arrives at minute 9 | Invalid | Invalid |
| International turn on a non-international stand | Invalid | Invalid |
| One turn listed on two stands | Invalid | Invalid |
| Valid plan with an unrelated top-level key | Valid; key ignored | Valid |
| Remote turn with 5 total passengers plus a 5-passenger transfer over distance 13 | `300×5 + 5×13 = 1,565` | Cost 1,565 |
| Same-stand 5-passenger transfer with diagonal distance 7 | Cost 35 | Cost 35 |
| Raw JSON repeats the same stand key | Invalid per document | **Accepted after last-key-wins parsing** |

## Verdict

accept with fixes