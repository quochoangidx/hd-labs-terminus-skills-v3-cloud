# Deterministic quality-panel precheck

Run this fail-closed gate before spending reviewer sessions. It validates
authored scope/closure evidence and existing deterministic receipts. It cannot
decide semantic correctness and never emits a quality-axis `None` verdict.

## Manifest

Keep `panel-precheck-manifest.json` outside the task folder under its report
directory. Bind the full form to the exact task tree. Minimal shape:

```json
{
  "schema_version": 1,
  "task_slug": "tbrain-example",
  "task_snapshot_sha256": "<full task tree hash; full mode only>",
  "primary_outcome": "one observable domain result",
  "obligations": [
    {
      "id": "AUTHORITY",
      "class": "core",
      "contribution": "select the authority valid at the action",
      "authority": {"file": "instruction.md", "anchor": "historical authority"},
      "implementation_sites": ["environment/repo/src/audit.py"],
      "separability": {
        "standalone_deliverable": false,
        "joins_before_output": true,
        "rationale": "the interaction changes the audited decision"
      },
      "witnesses": {
        "positive": ["test_a.py::test_historical_authority"],
        "boundary": ["test_a.py::test_authority_boundary"]
      }
    },
    {
      "id": "RECONCILIATION",
      "class": "core",
      "contribution": "reconcile the selected authority with action evidence",
      "authority": {"file": "instruction.md", "anchor": "reconcile"},
      "implementation_sites": ["environment/repo/src/audit.py"],
      "separability": {
        "standalone_deliverable": false,
        "joins_before_output": true,
        "rationale": "authority and action evidence jointly determine the result"
      },
      "witnesses": {
        "positive": ["test_a.py::test_reconciliation"],
        "boundary": [],
        "boundary_not_applicable": "finite evidence-state interaction"
      }
    },
    {
      "id": "PARSER",
      "class": "support",
      "contribution": "decode the declared envelope",
      "implementation_complete": true,
      "repair_surface": false,
      "paths": ["environment/repo/src/parser.py"],
      "smoke_test_ids": ["test_a.py::test_parser_smoke"]
    }
  ],
  "causal_graph": {
    "edges": [
      {"from": "AUTHORITY", "to": "RECONCILIATION"},
      {"from": "RECONCILIATION", "to": "PRIMARY_OUTCOME"}
    ]
  },
  "interactions": [
    {
      "id": "authority-reconciliation",
      "obligation_ids": ["AUTHORITY", "RECONCILIATION"],
      "witness_ids": ["test_a.py::test_authority_reconciliation"],
      "joins_before_output": true
    }
  ],
  "exact_output_requirements": [
    {
      "id": "INTEROP-ORDER",
      "domain_required": true,
      "rationale": "downstream signed exchange requires canonical order"
    }
  ],
  "verifier_matrix": "verifier-matrix.json",
  "strict_preflight": "preflight.json",
  "wrong_paths": [
    {
      "id": "latest-state-only",
      "kind": "semantic_partial",
      "obligation_ids": ["AUTHORITY", "RECONCILIATION"],
      "receipt": "wrong-paths/latest-state-only.json"
    },
    {
      "id": "candidate-bypass",
      "kind": "harness_bypass",
      "obligation_ids": [],
      "receipt": "wrong-paths/candidate-bypass.json"
    }
  ]
}
```

A wrong-path receipt must contain `status: "pass"`, its `wrong_path_id`, the
current `task_snapshot_sha256`, numeric `reward: 0`, non-empty
`failed_test_ids` and `passed_control_ids`, plus the executed `command` and
`exit_code`. One wrong path may cover multiple obligations when the recorded
failure actually exercises their shared invariant. Do not create mutants to
reach a count.

## Commands

Before scaffolding, planned implementation paths need not exist:

```bash
python3 .agent/skills/task-quality-panel-judgement/scripts/panel_precheck.py \
  workspace/tasks/<slug> \
  --manifest workspace/reports/<slug>/panel-precheck-manifest.json \
  --design-only
```

After strict Docker closure, require current paths, verifier inventory,
Oracle/NOP/noexec, demotion and minimal wrong-path receipts:

```bash
python3 .agent/skills/task-quality-panel-judgement/scripts/panel_precheck.py \
  workspace/tasks/<slug> \
  --manifest workspace/reports/<slug>/panel-precheck-manifest.json \
  --full --output workspace/reports/<slug>/panel-precheck.json
```

Only `status: "pass"` permits packet preparation. The four
`mechanically_ready` labels mean only that deterministic prerequisites passed;
the ten fresh reviewers still perform the semantic panel.
