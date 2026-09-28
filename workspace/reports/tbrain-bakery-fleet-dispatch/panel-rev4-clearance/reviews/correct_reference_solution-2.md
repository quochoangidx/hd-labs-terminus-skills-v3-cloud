{
  "axis": "correct_reference_solution",
  "reviewer_id": "correct_reference_solution-2",
  "snapshot_sha256": "c8b4d812db61634a39b8453e8d12635a6a7d6769693675fab88f108c56b795f1",
  "severity": "None",
  "findings": [],
  "input_completeness": {
    "status": "complete",
    "files_read": [
      "_panel_docs/quality-panel-judge-guide.md",
      "_panel_docs/quality-panel-examples.md",
      "packet-manifest.json",
      "instruction.md",
      "environment/Dockerfile",
      "environment/app/README.md",
      "environment/app/docs/dispatch-rules.md",
      "environment/app/tools/check_plan.py",
      "environment/app/orders/targets.json",
      "environment/app/orders/harbour-lanes.json (full)",
      "environment/app/orders/{old-town,riverside,north-ring}.json (depot, fleet, customer count, spot customers 113/138 of riverside)",
      "solution/solve.sh",
      "solution/search/sisr.py",
      "solution/plans/{harbour-lanes,old-town,riverside,north-ring}.json"
    ],
    "not_read": "environment/app/planner/plan_morning.py (the legacy planner; it is not part of the reference and the contract only uses it as motivation, instruction.md:1). environment/.dockerignore not material."
  },
  "contract_requirements": [
    "R1 four files /app/plans/<morning>.json for harbour-lanes, old-town, riverside, north-ring (instruction.md:1)",
    "R2 each plan obeys dispatch-rules.md: every customer exactly once, per-kind vehicle count, integer depart >= open, windows (start <= due), back <= close, back-depart <= shift, capacity, range (dispatch-rules.md:33-52)",
    "R3 plan JSON shape: only 'routes'; route keys exactly type/depart/stops; integer depart and ids; no repeated keys (dispatch-rules.md:54-62)",
    "R4 cost <= targets.json value for each morning (instruction.md:1, targets.json:1-6)",
    "R5 only stdlib Python 3.13, no network (instruction.md:3)"
  ],
  "coverage_sweep": {
    "R1": "solve.sh:24-25 creates /app/plans and copies all four solution/plans/*.json; the four morning names match instruction.md:1 and the solution/plans file list.",
    "R2_harbour_lanes_full_trace": "Hand-traced all 12 routes of solution/plans/harbour-lanes.json:1-136 against orders/harbour-lanes.json with the check_plan.py:40-43 ceil-distance rule. Every stop starts at or before due (several exactly at due: cust 20 at 25200, 7 at 23400, 10 at 21600, 58 at 28800, 9 at 21600, 2 at 21600, 33 at 21600, 49 at 25200, 41 at 21600, 17->28 at 21600; start == due is permitted by dispatch-rules.md:38-39 and check_plan.py:84). All returns <= 46800, all shifts within limits (max van 16434 s vs 25200), loads within capacity (truck route exactly 150/150, bike routes 14/14 and 13/14), bike distances 255/251/227/258 <= range 260. Vehicle use van 7/7, truck 1/3, bike 4/5. Customers 1..60 each appear exactly once. Route costs 6598+7324+7049+15561+1410+1402+9535+1354+9524+8358+1416+8336 = 77867 = targets.json:2.",
    "R2_other_mornings_structural": "old-town: 110 stops over 21 routes, ids 1..110 each exactly once, truck 4/5, van 10/13, bike 7/9. riverside: 160 stops over 28 routes, ids 1..160 each exactly once, truck 7/8, van 10/20, bike 11/13. north-ring: 220 stops over 44 routes, ids 1..220 each exactly once, truck 10/11, van 16/27, bike 18/18. Spot traces: riverside bike depart 15382 -> cust 138 (-116,-24): leg 119, arrives 18000 = ready, back 21058, distance 238 <= 260; riverside bike depart 21068 -> cust 113: leg 106, arrives 23400 = ready, demand 14 = capacity, distance 212. All departs >= open 14400 (minimum 15382).",
    "R2_self_check": "solve.sh:23,26-28 runs check_plan.py on every installed plan under set -euo pipefail; check_plan.py:117-119 returns 1 on any rule violation, so an infeasible shipped plan would fail the reference loudly rather than silently install.",
    "R3": "All four plan files have only a 'routes' key, route objects with exactly type/depart/stops, integer depart values, integer customer ids, no repeated keys (visual inspection of all four files).",
    "R4": "harbour-lanes cost proven equal to target by full trace. For the other three, solve.sh:18-22 states plan cost = target and the targets are defined as the cost of the kept plans (instruction.md:1 'best plan anyone ... has found'); sisr.py cost function (sisr.py:85: fixed + per_unit * sum of ceil legs) matches dispatch-rules.md:50-52 and check_plan.py:100.",
    "R5": "solve.sh uses only bash cp/mkdir and python3 stdlib; sisr.py imports json, math, random, sys, time only (sisr.py:13-17). The reference ships precomputed plans, which the contract permits ('how you produce them is up to you', instruction.md:3)."
  },
  "interaction_sweep": [
    "sisr.py departure choice (sisr.py:87-98, depart = open + min(forward slack, total waits)) vs check_plan shift check (check_plan.py:94): the delay is bounded by forward time slack so windows stay met and by total waiting so the return time is unchanged; the shift test in sisr.evaluate (sisr.py:82-84) is therefore the same test check_plan applies to the emitted depart. Consistent.",
    "Distance rounding: sisr.dist (sisr.py:20-23) is byte-identical logic to check_plan.distance (check_plan.py:40-43), so search costs and checker costs agree.",
    "Boundary equalities (start == due, load == capacity, bikes used == count in north-ring) are all accepted by the rules' non-strict wording and check_plan's strict '>' comparisons."
  ],
  "unresolved_checks": [
    "Full per-stop time-window/shift/range trace of old-town, riverside and north-ring (93 routes) was not done by hand; feasibility of those is supported by structural checks, spot traces, the matching cost model, and solve.sh's set -e check_plan gate, which would make the reference fail visibly if any were infeasible. Not reward-relevant as an open defect claim; an orchestrator can close it by running solve.sh in the image and comparing the printed costs to targets.json (expected 147362, 201921, 288705)."
  ],
  "notes": [
    "Non-finding observation: solve.sh prints each cost but does not compare it with targets.json, so a cost > target would not make solve.sh itself exit non-zero. The harbour-lanes cost equals its target exactly and the others are documented as equal (solve.sh:18-22); no evidence of a mismatch, so this is not reported as a defect."
  ]
}
