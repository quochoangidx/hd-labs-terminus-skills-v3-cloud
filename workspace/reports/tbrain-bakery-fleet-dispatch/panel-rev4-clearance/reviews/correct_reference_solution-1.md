```json
{
  "axis": "correct_reference_solution",
  "reviewer_id": "correct_reference_solution-1",
  "snapshot_sha256": "c8b4d812db61634a39b8453e8d12635a6a7d6769693675fab88f108c56b795f1",
  "severity": "None",
  "findings": [],
  "input_completeness": {
    "complete": true,
    "files_read": [
      "instruction.md",
      "environment/Dockerfile",
      "environment/.dockerignore",
      "environment/app/README.md",
      "environment/app/docs/dispatch-rules.md",
      "environment/app/tools/check_plan.py",
      "environment/app/planner/plan_morning.py",
      "environment/app/orders/targets.json",
      "environment/app/orders/harbour-lanes.json (full)",
      "environment/app/orders/old-town.json (ids, demands, fleet)",
      "environment/app/orders/riverside.json (fleet; id count)",
      "environment/app/orders/north-ring.json (fleet)",
      "solution/solve.sh",
      "solution/search/sisr.py",
      "solution/plans/harbour-lanes.json",
      "solution/plans/old-town.json",
      "solution/plans/riverside.json",
      "solution/plans/north-ring.json",
      "_panel_docs/quality-panel-judge-guide.md",
      "_panel_docs/quality-panel-examples.md"
    ],
    "not_fully_traced": "Per-stop timing and cost of old-town, riverside and north-ring (110/160/220 customers) were not hand-traced; see unresolved_checks."
  },
  "contract_requirements": [
    "R1 instruction.md:1 - write /app/plans/<morning>.json for all four mornings",
    "R2 instruction.md:1 - each plan obeys dispatch-rules.md",
    "R3 instruction.md:1 + orders/targets.json:1-6 - cost <= target per morning",
    "R4 dispatch-rules.md:27-29 - Euclidean distance rounded up; travel = distance*pace",
    "R5 dispatch-rules.md:37-46 - integer depart >= open; start=max(arrival,ready) <= due; back <= close; back-depart <= shift; capacity; range",
    "R6 dispatch-rules.md:50-52 - every customer exactly once; per-kind count; cost = sum(fixed + per_unit*distance)",
    "R7 dispatch-rules.md:54-62 - JSON format: only 'routes'; route keys exactly type/depart/stops; integer depart and stop ids; no repeated keys"
  ],
  "coverage_sweep": [
    {
      "requirement": "R1",
      "evidence": "solution/solve.sh:24-25 creates /app/plans and copies solution/plans/*.json; the four files exist under solution/plans/ with the exact morning names. solve.sh:26-28 runs check_plan.py on each under set -euo pipefail (solve.sh:23), and check_plan exits 1 on INFEASIBLE (check_plan.py:117-119), so an infeasible reference plan would fail the oracle run."
    },
    {
      "requirement": "R2/R4/R5/R6 harbour-lanes (full static trace)",
      "evidence": "All 12 routes of solution/plans/harbour-lanes.json:1-136 were hand-traced against orders/harbour-lanes.json. Coverage: 60 stops, ids 1..60 each exactly once. Vehicle use: van 7/7, truck 1/3, bike 4/5 (orders/harbour-lanes.json:613-640). Capacity: max van load 60 (route 2), truck 150/150 (route 4), bikes 14/14/13/13. Bike range: 255, 251, 227, 258 <= 260. Every window satisfied, several binding exactly at due (for example route 1 customer 20 arrives 25200 with due 25200; route 4 customer 10 arrives 21600 with due 21600; route 11 customer 49 arrives 25200 with due 25200), all under shift and back before close. Route costs 6598+7324+7049+15561+1410+1402+9535+1354+9524+8358+1416+8336 = 77867, equal to targets.json:2 (77867), so cost <= target holds at equality."
    },
    {
      "requirement": "R6 old-town (structural)",
      "evidence": "solution/plans/old-town.json: 21 routes, 110 stops, ids 1..110 each exactly once (checked id by id). Fleet use truck 4/5, van 10/13, bike 7/9 (orders/old-town.json:1113-1140). Loads recomputed from demands: trucks 149/146/150/150 <= 150; vans 59,59,60,60,57,60,60,58,59,60 <= 60; bikes 14,14,12,14,13,14,14 <= 14."
    },
    {
      "requirement": "R6 riverside / north-ring (structural)",
      "evidence": "riverside.json plan: 28 routes, 160 stops (orders file has 160 ids); fleet use truck 7/8, van 10/20, bike 11/13 (orders/riverside.json:1613-1640). north-ring.json plan: 44 routes, 220 stops, max id 220; fleet use truck 10/11, van 16/27, bike 18/18 (orders/north-ring.json:2213-2240)."
    },
    {
      "requirement": "R7",
      "evidence": "All four plan files are {\"routes\": [...]} with each route carrying exactly type/depart/stops, integer depart values (no decimals), integer stop ids, and no repeated keys; matches dispatch-rules.md:54-62 and the strict loader in check_plan.py:18-37,55-62."
    },
    {
      "requirement": "Checker fidelity (reference self-check relies on it)",
      "evidence": "check_plan.py:40-43 rounds distance up via isqrt, matching dispatch-rules.md:27-28; check_plan.py:70-100 implements depart>=open, max(arrival,ready)<=due, back<=close, back-depart<=shift, capacity, range and fixed+per_unit*driven exactly as dispatch-rules.md:37-52; check_plan.py:101-106 enforces fleet counts and coverage."
    },
    {
      "requirement": "Provenance generator (not run by solve.sh)",
      "evidence": "solution/search/sisr.py:20-23 uses the same rounding. Its departure delay (sisr.py:82-85, 87-98) is min(forward slack, cumulative waits), which keeps every start <= due and leaves the return time unchanged, so the emitted depart values are feasible under the rules. to_plan (sisr.py:308-310) emits integer depart values and the orders file ids."
    }
  ],
  "interaction_sweep": [
    "Window x shift x depart: sampled routes depart after open so that later windows still bind at due while shift holds (for example harbour-lanes route 6 departs 27304 and reaches customer 58 at 28800 = due).",
    "Capacity x range on bikes: harbour-lanes bike routes sit near both caps (load 14/14 with range 255/260) and remain within both.",
    "Fleet count x kind choice: north-ring uses all 18 bikes, which is allowed (count <= fleet)."
  ],
  "unresolved_checks": [
    "Per-stop window/shift feasibility and exact cost equality to target were not hand-traced for old-town (147362), riverside (201921) and north-ring (288705). solve.sh:26-28 would fail the oracle if any plan were infeasible, and the fully traced harbour-lanes plan matches its target exactly. No evidence of a defect, but this is bounded static review, not execution."
  ],
  "notes_non_blocking": [
    "solve.sh installs precomputed plans instead of re-running the search. The contract leaves the method open (instruction.md:3, 'how you produce them is up to you'), so this is not a correctness defect.",
    "solve.sh's self-check verifies feasibility only and does not compare the printed cost to targets.json. That is not a defect because the costs are recorded as equal to the targets (solve.sh:18-22, confirmed for harbour-lanes)."
  ],
  "reach": "n/a - no finding",
  "flip": "n/a - no finding"
}
```
