{
  "axis": "protected_ground_truth",
  "reviewer_id": "protected_ground_truth-2",
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
      "environment/app/tools/check_plan.py (hash-identical to tests/check_plan.py per manifest)",
      "environment/app/orders/targets.json (hash-identical to tests/targets.json)",
      "environment/app/orders/*.json (structure: name, depot, customers, fleet; hash-identical to tests/orders/*.json; north-ring fleet read in full)",
      "tests/Dockerfile",
      "tests/test.sh",
      "tests/test_outputs.py",
      "tests/check_plan.py"
    ],
    "notes": "Order files were checked by key structure and a keyword search (routes/plan/best/solution/stops/note/comment: no matches). I did not read every customer record line by line. Those records are plain input data, and the manifest shows they are byte-identical to the verifier copies."
  },
  "coverage_sweep": {
    "answer_exposure": "Nothing in the environment holds an answer. The environment contains no plan, no best-known routes and no reference (environment/.dockerignore:11-12 excludes solution/ and tests/). The only candidate-visible planner is the weak greedy baseline (environment/app/planner/plan_morning.py:1-53). The targets (environment/app/orders/targets.json:1-6) are disclosed on purpose as cost thresholds (instruction.md:1). A threshold is a pass bound, not the answer: a candidate still has to build a feasible plan that meets it.",
    "trusted_inputs": "The verifier loads orders, targets and rules code only from its own directory (tests/test_outputs.py:15-26, sys.path.insert of HERE at :16). These come from the verifier image's COPY . /tests/ (tests/Dockerfile:5). If the candidate edits /app/orders, /app/orders/targets.json or /app/tools/check_plan.py, grading is unaffected. The docstring's statement that no /app code runs (tests/test_outputs.py:3-5) holds.",
    "candidate_artifact_handling": "Plans are the only candidate-controlled input. They are read strictly as JSON data (tests/check_plan.py:29-37), and nothing in them is executed. A symlinked plan is followed (tests/test_outputs.py:31 os.path.isfile, check_plan.py:32 open), but no file the verifier can read is a valid plan: /tests/targets.json and /tests/orders/*.json fail the routes-only schema at check_plan.py:53-56. So there is no chmod_follow path to credit. Deep nesting (RecursionError) and NaN/Infinity are converted to PlanError (check_plan.py:25-37).",
    "reward_channel": "test.sh writes 0 first and sets the reward only from pytest's exit code (tests/test.sh:5, 15-21). Candidate stdout and plan contents cannot write reward.txt.",
    "verifier_process_isolation": "pytest runs as python3 -I from a fresh mktemp dir (tests/test.sh:13-15), so PYTHON* environment variables and cwd-based imports are ignored. Rootdir and conftest discovery are anchored at /tests, which holds no candidate-writable files. The DISPATCH_PLANS override (tests/test_outputs.py:19) is verifier environment, not candidate-controlled.",
    "label_leak_channels": "Plan paths use neutral morning names (tests/test_outputs.py:30). No expected outcome is carried by a filename, argument, cwd or environment variable, and no candidate code is invoked."
  },
  "interaction_sweep": "I checked combinations of symlinked plans with the verifier's own golden-like files: targets and orders fail the plan schema. I also combined edits to candidate-side copies of the checker, orders and targets with the verifier's separate copies: there is no shared path. No combination gives an answer-protection bypass. Whether check_plan.evaluate accepts an invalid plan cheaply is a sound_verifier question, not this axis. On a spot check, fleet fixed and per_unit costs are non-negative (orders/north-ring.json:2211-2242), so a negative-cost trick does not work.",
  "rejected_concerns": [
    {
      "concern": "Targets are candidate-visible (environment/app/orders/targets.json:1-6, identical to tests/targets.json).",
      "reason": "instruction.md:1 discloses the targets on purpose as cost bounds. Knowing a bound does not produce a feasible plan or earn credit."
    },
    {
      "concern": "The plan read follows symlinks (tests/test_outputs.py:31, tests/check_plan.py:32).",
      "reason": "No verifier-readable file is a valid plan for these orders. The only goldens are targets and orders, and both fail check_plan.py:53-56, so pointing a symlink at them earns nothing (examples C-1/C-2 reasoning)."
    }
  ],
  "unresolved_checks": [],
  "finding_evidence": "static_proof (read-only review; nothing was executed)"
}
