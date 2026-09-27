```json
{
  "axis": "sound_verifier",
  "reviewer_id": "sound_verifier-1",
  "snapshot_sha256": "c8b4d812db61634a39b8453e8d12635a6a7d6769693675fab88f108c56b795f1",
  "severity": "None",
  "findings": [],
  "input_completeness": {
    "status": "complete",
    "read": [
      "_panel_docs/quality-panel-judge-guide.md",
      "_panel_docs/quality-panel-examples.md",
      "packet-manifest.json",
      "instruction.md:1-3",
      "environment/app/docs/dispatch-rules.md:1-62",
      "environment/app/README.md:1-13",
      "environment/app/planner/plan_morning.py:1-69",
      "environment/app/orders/targets.json:1-6",
      "environment/Dockerfile:1-7",
      "environment/.dockerignore:1-13",
      "tests/test.sh:1-21",
      "tests/Dockerfile:1-6",
      "tests/test_outputs.py:1-80",
      "tests/check_plan.py:1-125",
      "tests/orders/harbour-lanes.json:1-30,600-643 (schema sample); fleet/depot fields of all four orders files via grep"
    ],
    "notes": "The manifest shows tests/check_plan.py, tests/orders/*.json and tests/targets.json have the same hashes as environment/app/tools/check_plan.py, environment/app/orders/*.json and environment/app/orders/targets.json (packet-manifest.json:9-28). The verifier therefore applies the same rules and targets the candidate can see and run. I did not read every customer record line by line. Customer fields were sampled, and every depot and fleet field was checked in all four files."
  },
  "coverage_sweep": [
    {"requirement": "Four plan files at /app/plans/<morning>.json", "evidence": "tests/test_outputs.py:19,29-32,51-80", "status": "enforced; a missing file fails"},
    {"requirement": "Plan is strict JSON: no repeated keys, no NaN/Infinity", "evidence": "dispatch-rules.md:59-62; tests/check_plan.py:18-37", "status": "enforced"},
    {"requirement": "Only the 'routes' key; each route has exactly type/depart/stops", "evidence": "dispatch-rules.md:60-61; tests/check_plan.py:53-62", "status": "enforced"},
    {"requirement": "type names a fleet entry", "evidence": "dispatch-rules.md:58; tests/check_plan.py:63-65", "status": "enforced, and a non-string type is guarded"},
    {"requirement": "Every route visits at least one customer", "evidence": "dispatch-rules.md:35; tests/check_plan.py:67-68", "status": "enforced"},
    {"requirement": "depart is a JSON integer (not float or bool) and not before open", "evidence": "dispatch-rules.md:37,58-59; tests/check_plan.py:70-71", "status": "enforced"},
    {"requirement": "Stops are integer customer ids from the orders; each customer is served exactly once; nobody is missed", "evidence": "dispatch-rules.md:50,59-60; tests/check_plan.py:75-79,104-106", "status": "enforced"},
    {"requirement": "Euclidean distance rounded up to a whole unit", "evidence": "dispatch-rules.md:27-28; tests/check_plan.py:40-43", "status": "exact integer ceil via isqrt; coordinates are integers"},
    {"requirement": "Service starts at max(arrival, ready) and must be <= due; the vehicle leaves after service", "evidence": "dispatch-rules.md:38-40; tests/check_plan.py:83-86", "status": "enforced"},
    {"requirement": "Back by close and within shift of departure", "evidence": "dispatch-rules.md:41-42; tests/check_plan.py:89-95", "status": "enforced"},
    {"requirement": "Capacity, and range where it is not null (range = sum of rounded legs including the return)", "evidence": "dispatch-rules.md:43-46; tests/check_plan.py:81-82,96-99", "status": "enforced"},
    {"requirement": "Fleet count per type", "evidence": "dispatch-rules.md:50-51; tests/check_plan.py:72,101-103", "status": "enforced"},
    {"requirement": "Cost = sum of fixed + per_unit*distance; cost <= target per morning", "evidence": "instruction.md:1; dispatch-rules.md:51-52; tests/check_plan.py:100; tests/test_outputs.py:46-48", "status": "enforced against verifier-owned targets.json (identical to the visible targets)"}
  ],
  "wrong_solution_probes": [
    {"probe": "Submit the greedy planner output unchanged", "result": "instruction.md:1 says it is over cost and infeasible on two mornings; the cost is compared with the target at tests/test_outputs.py:48, and missing customers are rejected at tests/check_plan.py:104-106. Rejected."},
    {"probe": "Plan that skips hard customers or delivers one twice", "result": "Rejected at tests/check_plan.py:77-78,104-106."},
    {"probe": "Float depart (18000.0), bool ids or depart, extra keys, duplicate keys, NaN", "result": "Rejected at tests/check_plan.py:21,26,55-62,70,75."},
    {"probe": "Over-using a vehicle type to cut cost", "result": "Rejected at tests/check_plan.py:101-103."},
    {"probe": "Tampering with /app/tools/check_plan.py or /app/orders to change the grade", "result": "No effect. The verifier imports its own /tests/check_plan.py and orders (tests/test_outputs.py:15-26), and no /app code runs."}
  ],
  "valid_alternative_probes": [
    {"probe": "Any JSON whitespace or indentation, any route order, and any departure time >= open", "result": "Accepted. The file is parsed as JSON (tests/check_plan.py:33); route order is irrelevant to the checks; depart is only bounded below by open, and above implicitly by close and shift, as the rules document states."},
    {"probe": "Plans cheaper than the target", "result": "Accepted; the comparison is <= (tests/test_outputs.py:48)."},
    {"probe": "Unused vehicle types / fewer routes", "result": "Accepted; used counts start at 0 for every type (tests/check_plan.py:50)."}
  ],
  "interaction_sweep": "Checked how the time window interacts with shift and close: the shift is measured from the chosen depart, not from open (tests/check_plan.py:94), which matches dispatch-rules.md:41-42. A late departure therefore cannot bypass the close check at line 92. Checked range together with the return leg: driven includes the return leg (lines 89-90) before the range check at line 98, which matches dispatch-rules.md:45-46. Checked cost together with feasibility: cost is returned only after every per-route and plan-level check passes, so an infeasible cheap plan cannot pass the target test. Checked verifier independence: test.sh:13-15 runs pytest with -I from a fresh mktemp directory, and the tests use only /tests copies.",
  "unresolved_checks": [],
  "notes": "Reward is all-or-nothing over eight tests (test.sh:15-20), and the reward file is initialised to 0 (test.sh:5). Whether the targets are reachable belongs to the reference/contract axes and is outside this axis. The verifier grades exactly the documented rules and cost bound, and it rejects every plausible wrong plan I probed. I found no verifier-soundness defect."
}
```

Summary: sound_verifier -- severity **None** (0 findings; reach: n/a; flip: n/a). The verifier (tests/test_outputs.py + tests/check_plan.py) implements every rule in environment/app/docs/dispatch-rules.md one-for-one. It rejects missing, duplicated, over-capacity, out-of-window, over-shift, over-range and over-fleet plans and malformed JSON. It compares cost with verifier-owned targets identical to the visible ones. It accepts contract-valid alternatives: any formatting, any route order, any valid departure time, and any cheaper plan.
