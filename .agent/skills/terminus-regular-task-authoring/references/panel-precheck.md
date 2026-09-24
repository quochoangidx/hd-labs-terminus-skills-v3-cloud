# Deterministic obligation precheck

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
      },
      "expected_source": "independent_model",
      "discriminating_instance": "an action dated between two authority versions",
      "wrong_but_plausible": "use the newest authority regardless of the action date",
      "selfdescription_phrase": "which authority applies"
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
  "closure": {
    "universal_rule": {"file": "instruction.md", "anchor": "holds for every argument"},
    "silence": {"file": "instruction.md", "anchor": "the shipped behavior stands",
                "named_cases": [{"anchor": "a side of nought or less", "witness_ids": ["test_a.py::test_untouched_edges"]}]},
    "coverage_envelope": {"file": "instruction.md", "anchor": "ordinary and extreme states"},
    "entrypoint_scope": {"file": "environment/repo/NOTE.md", "anchor": "when called directly",
                         "helpers": [{"name": "shorter", "witness_ids": ["test_a.py::test_shorter_direct"]}]}
  },
  "determinism": {
    "seeds": [],
    "clock_dependence": "none",
    "network": "none",
    "order_sensitivity": "none"
  },
  "reference_selfdescription": "solution/solve.sh",
  "restrictions": [
    {
      "id": "X-no-reflection",
      "statement": "the package does its own work: no reflection, no native methods",
      "enforced_by": ["test_policy.py::test_compiled_code_obeys_the_rules"],
      "enforcement_level": "both",
      "allowed_exceptions_disclosed": true
    }
  ],
  "unclaimed_units_rationale": {},
  "removed_obligations": [],
  "exact_output_requirements": [
    {
      "id": "INTEROP-ORDER",
      "domain_required": true,
      "rationale": "downstream signed exchange requires canonical order",
      "authority_anchor": {"file": "environment/repo/NOTE.md", "anchor": "written in this order"}
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

## What the added fields are for

- **`closure`** — the clauses that decide the input domain the authority does not
  name. `universal_rule`, `silence` and `coverage_envelope` are required.
  `entrypoint_scope` is optional and discouraged: grade through the entry point
  unless a helper is the deliverable (`contract-closure.md` §1). When it is
  present, `entrypoint_scope.helpers` lists every helper the sentence promises,
  each with the `witness_ids` that call it directly. A promised helper that no
  test calls blocks (`entrypoint_helper_unwitnessed`). A listed helper the cited
  file never names also blocks (`entrypoint_helper_unnamed`). Each anchor must
  appear verbatim in the cited file. `silence.named_cases` is required: one row
  per case the silence prose names, each with its anchor phrase and the
  `witness_ids` that check it against the shipped behaviour, or `[]` when the
  prose names none. A named case with no witness blocks (`silence_case_unwitnessed`):
  the platform's `test_instruction_alignment` check reads every named case as a
  requirement, and failed `tbrain-quantized-depthwise-convolution` on exactly this. Rationale and worked examples:
  [contract closure](contract-closure.md).
- **`expected_source`** — where a witness's expected value comes from, one of
  `independent_model`, `authority_text`, `shipped_differential`, `invariant`,
  `oracle_recorded`. The last records what the reference already does, so it
  agrees with the reference whatever the reference got wrong; pair it with
  `oracle_recorded_corroboration` naming an invariant or shipped differential.
- **`discriminating_instance` / `wrong_but_plausible`** — the case the witness
  runs, and the reasonable wrong answer it rules out. A witness that no plausible
  wrong implementation fails is not coverage.
- **`authority_anchor` on an exact convention** — the visible sentence that fixes
  it. A `rationale` says why the convention exists; it does not let a candidate
  read the convention off anything.
- **`determinism`** — `deterministic_execution` blocks on `Minor`, and nothing
  else here would notice a verifier that depends on the clock, the network or
  collection order.
- **`reference_selfdescription`** — the solution file whose header maps each core
  obligation to its change. The reference is judged against the instruction alone.
- **`unclaimed_units_rationale`** — the escape hatch for a verifier unit that
  deliberately belongs to no obligation, such as a collection smoke test. Full
  mode sweeps units against witnesses in both directions.
- **`removed_obligations`** — obligations dropped because they were not core,
  each with the reason and the `former_anchor` sentence that used to promise it.
  Full mode fails when that sentence still reads in the task: a promise left in
  the prose after its witness is deleted is still enforced by the panel and now
  has nothing defending it.
- **`restrictions`** — one entry per thing the contract forbids. `statement` is
  the restriction as the candidate reads it; `enforced_by` names the checks that
  run, because a restriction the verifier cannot see is decoration;
  `allowed_exceptions_disclosed` asserts the prose also names what stays legal,
  so an honest solution cannot fail on a rule nobody wrote down.

  `enforcement_level` is `source`, `compiled` or `both`. **A restriction on what
  the program may reach at run time cannot be enforced by reading source**: the
  same capability is reachable through a constant, a generated name or a
  dependency, so the check must read the compiled artifact. The gate flags a
  run-time restriction declared `source` — either audit the compiled output, or
  narrow the sentence to what source can actually decide, such as where files
  live or which names appear in an import list.

A wrong-path receipt must contain `status: "pass"`, its `wrong_path_id`, the
current `task_snapshot_sha256`, numeric `reward: 0`, non-empty
`failed_test_ids` and `passed_control_ids`, plus the executed `command` and
`exit_code`. One wrong path may cover multiple obligations when the recorded
failure actually exercises their shared invariant. Do not create mutants to
reach a count.

## Commands

Before scaffolding, planned implementation paths need not exist:

```bash
python3 .agent/skills/terminus-regular-task-authoring/scripts/panel_precheck.py \
  workspace/tasks/<slug> \
  --manifest workspace/reports/<slug>/panel-precheck-manifest.json \
  --design-only
```

After strict Docker closure, require current paths, verifier inventory,
Oracle/NOP/noexec, demotion and minimal wrong-path receipts:

```bash
python3 .agent/skills/terminus-regular-task-authoring/scripts/panel_precheck.py \
  workspace/tasks/<slug> \
  --manifest workspace/reports/<slug>/panel-precheck-manifest.json \
  --full --output workspace/reports/<slug>/panel-precheck.json
```

Only `status: "pass"` permits packet preparation. The four
`mechanically_ready` labels mean only that deterministic prerequisites passed;
the ten fresh reviewers still perform the semantic panel.
