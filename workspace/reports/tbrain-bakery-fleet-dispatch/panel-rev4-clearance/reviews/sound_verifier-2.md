{
  "reviewer_id": "sound_verifier-2",
  "axis": "sound_verifier",
  "snapshot_sha256": "c8b4d812db61634a39b8453e8d12635a6a7d6769693675fab88f108c56b795f1",
  "severity": "None",
  "findings": [],
  "input_completeness": {
    "complete": true,
    "files_read": [
      "_panel_docs/quality-panel-judge-guide.md",
      "_panel_docs/quality-panel-examples.md",
      "packet-manifest.json",
      "instruction.md",
      "environment/Dockerfile",
      "environment/.dockerignore",
      "environment/app/README.md",
      "environment/app/docs/dispatch-rules.md",
      "environment/app/planner/plan_morning.py",
      "tests/Dockerfile",
      "tests/test.sh",
      "tests/test_outputs.py",
      "tests/check_plan.py",
      "tests/targets.json",
      "tests/orders/*.json (header of harbour-lanes read in full through customer 7; fleet blocks of all four read; all four scanned for non-integer numbers, booleans, string ids and id sequence)"
    ],
    "identity_notes": "Per packet-manifest.json:9-28, tests/check_plan.py, tests/targets.json and tests/orders/*.json are byte-identical (same sha256) to environment/app/tools/check_plan.py, environment/app/orders/targets.json and environment/app/orders/*.json, so the environment copies were covered by reading the tests copies."
  },
  "coverage_sweep": [
    {
      "requirement": "Plan delivers every customer exactly once",
      "contract": "environment/app/docs/dispatch-rules.md:50",
      "assertion": "tests/check_plan.py:77-79 (duplicate), 104-106 (missing); run by tests/test_outputs.py:35-48 for all four mornings",
      "result": "enforced both directions"
    },
    {
      "requirement": "No more vehicles of a type than fleet count; each vehicle at most one route",
      "contract": "dispatch-rules.md:35,51",
      "assertion": "tests/check_plan.py:72,101-103",
      "result": "enforced"
    },
    {
      "requirement": "Every route has at least one stop; type names a fleet entry",
      "contract": "dispatch-rules.md:34-35,58",
      "assertion": "tests/check_plan.py:63-68",
      "result": "enforced"
    },
    {
      "requirement": "Departure is a JSON integer, not before open",
      "contract": "dispatch-rules.md:37,58-59",
      "assertion": "tests/check_plan.py:69-71 (bool excluded, float 18000.0 rejected as documented)",
      "result": "enforced, matches documented format"
    },
    {
      "requirement": "Service starts at max(arrival, ready) and must not exceed due; leave after service",
      "contract": "dispatch-rules.md:38-40",
      "assertion": "tests/check_plan.py:81-86",
      "result": "enforced; arrival = clock + leg*pace matches dispatch-rules.md:28-29"
    },
    {
      "requirement": "Back by close and within shift of departure",
      "contract": "dispatch-rules.md:41-42",
      "assertion": "tests/check_plan.py:89-95",
      "result": "enforced"
    },
    {
      "requirement": "Capacity and range (range null means unlimited); distance is sum of rounded legs including return",
      "contract": "dispatch-rules.md:20-23,43-46",
      "assertion": "tests/check_plan.py:82,87,89-90,96-99",
      "result": "enforced"
    },
    {
      "requirement": "Distance is Euclidean rounded up",
      "contract": "dispatch-rules.md:27-29",
      "assertion": "tests/check_plan.py:40-43 (isqrt with ceiling correction; all coordinates are integers, grep for decimals in tests/orders returned 0)",
      "result": "exact ceiling for integer coordinates"
    },
    {
      "requirement": "Cost = sum(fixed + per_unit * distance) and cost <= morning target",
      "contract": "instruction.md:1, dispatch-rules.md:51-52",
      "assertion": "tests/check_plan.py:100,107; tests/test_outputs.py:46-48 with tests/targets.json",
      "result": "enforced with inclusive <= as instructed ('no more than')"
    },
    {
      "requirement": "Strict plan format: only routes key; route has exactly type/depart/stops; no repeated keys; stops are integer ids",
      "contract": "dispatch-rules.md:54-62",
      "assertion": "tests/check_plan.py:18-37,53-62,75-76",
      "result": "enforced; no restriction beyond the documented format (key order, whitespace, route order are free)"
    },
    {
      "requirement": "All four mornings graded; plan file must exist at /app/plans/<morning>.json",
      "contract": "instruction.md:1",
      "assertion": "tests/test_outputs.py:29-32,51-80",
      "result": "each morning has feasibility and target tests; reward is all-or-nothing at tests/test.sh:15-21"
    },
    {
      "requirement": "Grading independent of candidate-modifiable /app code and orders",
      "contract": "instruction.md:3 ('Only the four plan files are used')",
      "assertion": "tests/test_outputs.py:1-26 uses verifier-owned check_plan.py, orders and targets under /tests",
      "result": "a candidate editing /app/tools/check_plan.py, /app/orders or targets.json cannot change grading"
    }
  ],
  "interaction_sweep": [
    "Plausible wrong outputs checked by trace: the shipped greedy planner output (dispatch-rules-valid but costly, or missing customers per instruction.md:1) fails check_target or check_feasible; a plan that drops unreachable customers fails tests/check_plan.py:104-106; a plan exceeding bike range or capacity fails :96-99; a plan relying on early service before ready is recomputed by :83 so it cannot under-report time; reusing more vans than count fails :101-103; a float depart fails :70.",
    "Valid alternatives checked: any route order, any vehicle mix, late departures, any JSON key order/whitespace, and any integer depart >= open are accepted when the rules hold; no ordering or canonical-bytes comparison exists in tests/test_outputs.py.",
    "Malformed-input robustness: non-dict plan, non-list routes, non-dict route, non-string type, nested/non-int stop ids, NaN/Infinity, duplicate keys and deep nesting all raise PlanError (tests/check_plan.py:31-37,53-76), which tests/test_outputs.py:36-39 turns into a failure; no path lets an exception other than a failure pass.",
    "Harness: tests/Dockerfile:3 installs pytest and pytest-json-ctrf used by tests/test.sh:15; -p no:randomly is harmless; reward is written 1 only on pytest exit 0 (tests/test.sh:16-21)."
  ],
  "unresolved_checks": [],
  "out_of_axis_notes": [
    "Whether each target in tests/targets.json is actually attainable is a solvability / reference question (solution withheld from this packet); it is not assessable here and is not raised as a verifier finding."
  ]
}
