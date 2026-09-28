{
  "axis": "coherent_contract",
  "reviewer_id": "coherent_contract-2",
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
      "task.toml",
      "environment/Dockerfile",
      "environment/.dockerignore",
      "environment/app/README.md",
      "environment/app/docs/dispatch-rules.md",
      "environment/app/tools/check_plan.py",
      "environment/app/planner/plan_morning.py",
      "environment/app/orders/targets.json",
      "environment/app/orders/harbour-lanes.json (header, sample customers, fleet block)",
      "environment/app/orders/{old-town,riverside,north-ring}.json (depot/fleet/id structure via search)",
      "tests/test.sh",
      "tests/Dockerfile",
      "tests/test_outputs.py",
      "tests/check_plan.py"
    ],
    "notes": "Byte identity per packet-manifest.json:17,21 (check_plan.py), :11-15 vs :22-26 (orders and targets): the verifier's copies of the checker, orders and targets are hash-identical to the candidate-visible copies, so the checker the instruction offers is exactly the checker that grades."
  },
  "coverage_sweep": [
    {"rule": "Output paths /app/plans/<morning>.json for the four named mornings", "authority": "instruction.md:1", "grader": "tests/test_outputs.py:19,29-32,51-80; task.toml:1 artifacts", "status": "consistent"},
    {"rule": "Cost <= target", "authority": "instruction.md:1; environment/app/orders/targets.json:1-6", "grader": "tests/test_outputs.py:46-48 (<=)", "status": "consistent"},
    {"rule": "Distance = Euclidean rounded up", "authority": "dispatch-rules.md:27-29", "grader": "tests/check_plan.py:40-43 (ceil via isqrt)", "status": "consistent"},
    {"rule": "Integer departure, not before open", "authority": "dispatch-rules.md:37,58-59", "grader": "tests/check_plan.py:69-71 (int, not bool, >= open)", "status": "consistent"},
    {"rule": "Service starts at max(arrival, ready), must be <= due; leave after service", "authority": "dispatch-rules.md:38-40", "grader": "tests/check_plan.py:83-86", "status": "consistent"},
    {"rule": "Back by close and within shift from departure", "authority": "dispatch-rules.md:41-42", "grader": "tests/check_plan.py:89-95", "status": "consistent"},
    {"rule": "Capacity and range (null = unlimited), distance = sum of rounded legs incl. return", "authority": "dispatch-rules.md:22-23,43-46", "grader": "tests/check_plan.py:81-82,89-90,96-99", "status": "consistent"},
    {"rule": "Every route non-empty; at most count vehicles per kind", "authority": "dispatch-rules.md:34-35,50-51", "grader": "tests/check_plan.py:66-68,101-103", "status": "consistent"},
    {"rule": "Every customer exactly once; stop ids are the orders' integers", "authority": "dispatch-rules.md:50,59-60", "grader": "tests/check_plan.py:74-79,104-106", "status": "consistent"},
    {"rule": "Cost = sum(fixed + per_unit*distance)", "authority": "dispatch-rules.md:51-52", "grader": "tests/check_plan.py:100", "status": "consistent"},
    {"rule": "Strict JSON: only routes key, route keys exactly type/depart/stops, no repeated keys", "authority": "dispatch-rules.md:54-62", "grader": "tests/check_plan.py:15-37,53-62", "status": "consistent (NaN/Infinity rejection is not valid JSON anyway, so it adds no hidden rule)"},
    {"rule": "kind is informational only", "authority": "dispatch-rules.md:14-16", "grader": "tests/check_plan.py never reads kind", "status": "consistent"},
    {"rule": "Tooling constraint: Python 3.13 stdlib, no network", "authority": "instruction.md:3", "grader": "environment/Dockerfile:1; task.toml:24-25", "status": "consistent, not graded"}
  ],
  "interaction_sweep": [
    "Departure time interacts with shift and early windows: rules state waiting happens at the customer (dispatch-rules.md:38-40) and shift is measured from departure (dispatch-rules.md:41-42); the checker implements the same (tests/check_plan.py:73,83,94). No undisclosed interaction.",
    "Fleet count and one-route-per-vehicle interact with range: range is per morning (dispatch-rules.md:22-23) and each vehicle runs one route (dispatch-rules.md:35), so per-route range checking in tests/check_plan.py:98 is equivalent.",
    "Target is candidate-visible (environment/app/orders/targets.json) and identical to tests/targets.json, so the pass threshold is fully disclosed.",
    "Order data contains sequential integer ids (1..N per file), integer coordinates/times, and range null only on van/truck, so no domain case falls outside the documented rules."
  ],
  "unresolved_checks": [],
  "reach_and_flip": "No finding. I found no pair of contract-compliant interpretations that the grader scores differently: every check in tests/check_plan.py and tests/test_outputs.py maps to a sentence in dispatch-rules.md or instruction.md, and the candidate can run the grading checker itself (byte-identical copy)."
}
