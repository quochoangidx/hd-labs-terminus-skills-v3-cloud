# Terminus 3 Evidence-Inferability Gate

This gate implements the Terminus 3 distinction between a **clear goal** and an
**inferred specification**. Keep the compatibility filename
`instruction-sufficiency.json`, but use schema version 3 for every new or
revised task.

The task must expose the requested outcome, artifact/interface, and any exact
convention that cannot be derived. It does not have to state every semantic
invariant as prose. Domain rules may be reconstructed from agent-visible
evidence, system state, realistic specifications, or established conventions.

## The three layers

1. **Explicit success contract** — state the goal, artifact paths, public
   interface or output schema, hard safety/resource constraints, and arbitrary
   exact values that the agent could not otherwise derive.
2. **Inferable domain model** — let the agent derive causal relations, protocol
   semantics, geometry, scientific interpretation, state transitions, and
   interacting constraints from one or more visible sources.
3. **Forbidden hidden knowledge** — reject oracle-only policies, unreachable
   authorities, undocumented exact strings, and arbitrary constants or
   tie-breaks that neither evidence nor domain convention determines.

Hidden instances, new combinations, and metamorphic variations are encouraged
when they exercise the same inferable model. A hidden test may not introduce a
new arbitrary policy or a fact the agent could not possibly obtain.

## Required report

Write `workspace/reports/<slug>/instruction-sufficiency.json` outside the task
folder and ZIP. New reports use this shape:

```json
{
  "schema_version": 3,
  "task": "tbrain-example",
  "verdict": "pass",
  "contract_source_files": [
    {"path": "instruction.md", "sha256": "<sha256>"},
    {"path": "environment/evidence/trace.json", "sha256": "<sha256>"}
  ],
  "explicit_contract": [
    {
      "id": "result_artifact",
      "requirement": "Write the recovered session summary to /app/result.json using the documented schema.",
      "test_selectors": ["test_result_schema"],
      "source_locator": "instruction.md:/app/result.json"
    }
  ],
  "inference_families": [
    {
      "id": "session_protocol",
      "inferred_model": "Frame boundaries and key evolution are reconstructed from the capture and host trace.",
      "test_selectors": ["test_session_*"],
      "evidence_sources": [
        {"path": "environment/evidence/capture.bin", "locator": "binary session", "role": "observed frames"},
        {"path": "environment/evidence/host.log", "locator": "startup records", "role": "initial state"}
      ],
      "reasoning_chain": "Correlating frame lengths with startup counters determines the transition model.",
      "competing_interpretation": "Treat every frame as independently keyed.",
      "evidence_discriminator": "That interpretation contradicts the counter progression shared by both artifacts.",
      "hidden_generalization": ["new_instances", "new_combinations", "metamorphic_variations"]
    }
  ],
  "unobtainable_knowledge": {
    "oracle_only_policies": [],
    "unreachable_authorities": [],
    "undocumented_exact_values": []
  },
  "oracle_alignment": {
    "oracle_is_valid_realization": true,
    "verifier_accepts_semantic_equivalents": true,
    "equivalence_notes": "The JSON schema is exact; ordering and implementation strategy are not graded."
  },
  "fairness_review": {
    "reviewer_count": 2,
    "reviewers": [
      {
        "reviewer_id": "fairness-review-1",
        "runtime": "codex",
        "model": "<actual model>",
        "session_id": "<actual fresh session id>",
        "fresh_context": true,
        "task_visible_only": true,
        "reviewed_source_files": ["environment/evidence/capture.bin", "environment/evidence/host.log", "instruction.md"],
        "transcript": "fairness-review-1.md",
        "transcript_sha256": "<sha256>"
      },
      {
        "reviewer_id": "fairness-review-2",
        "runtime": "codex",
        "model": "<actual model>",
        "session_id": "<different fresh session id>",
        "fresh_context": true,
        "task_visible_only": true,
        "reviewed_source_files": ["environment/evidence/capture.bin", "environment/evidence/host.log", "instruction.md"],
        "transcript": "fairness-review-2.md",
        "transcript_sha256": "<sha256>"
      }
    ],
    "questions": [
      {
        "id": "protocol_inferability",
        "family_ids": ["session_protocol"],
        "question": "Can a competent domain practitioner derive a defensible frame/key model from the visible evidence?",
        "inferability_supported": true,
        "unresolved_goal_ambiguity": false,
        "unobtainable_knowledge_required": false,
        "evidence_locators": ["environment/evidence/capture.bin", "environment/evidence/host.log"]
      }
    ]
  }
}
```

Run the V3 gate:

```bash
scripts/python3 .agent/skills/terminus-regular-task-authoring/scripts/sufficiency_manifest_check.py \
  --require-v3 workspace/tasks/<slug> \
  workspace/reports/<slug>/instruction-sufficiency.json
```

## Mapping rules

- Every static pytest function must map to an explicit-contract row, an
  inference family, or both.
- Explicit-contract rows map exact success-surface requirements to
  `instruction.md`. Do not place root cause or solution steps there.
- An inference family may cite multiple sources. The reasoning should emerge
  from their interaction; do not require one sentence that gives away the
  derived rule.
- Evidence sources must be inside the task and agent-visible. An authority is
  acceptable only when it is actually reachable under the configured network
  mode.
- Hidden tests may vary values, layouts, sequences, combinations, and timing
  states while preserving the visible evidence model.
- Exact schema fields, artifact paths, public symbol names, and arbitrary
  constants remain explicit unless a realistic visible source defines them.
- Verifiers should accept semantically equivalent realizations whenever the
  task does not require a unique representation.

## Fairness review

Give two fresh reviewers only `instruction.md` and the agent-visible
environment. Ask them to identify the goal, evidence, defensible domain model,
remaining uncertainty, and any information a correct solution would require
but could not obtain.

For `task-batch`, launch the two reviews concurrently in exactly two distinct
fresh sessions. Neither reviewer may be the builder, consolidated auditor, or
a blind solver. Do not provide solution files, verifier tests, rubrics, reports,
Oracle outputs, or hidden fixtures. The builder may assemble the final manifest
from their transcripts but may not substitute its own judgment for either
review.

The reviewers do **not** need to reproduce the oracle, choose the same
implementation, or predict every hidden case. The gate fails only when the
goal/interface is ambiguous, the evidence cannot support the graded inference,
or success requires unobtainable knowledge. Reviewer disagreement about a
legitimate implementation choice is acceptable when the verifier accepts both.

## Gate ordering

1. Run a lightweight goal/evidence audit before a skeleton probe.
2. Use the full V3 report before a full difficulty probe or packaging.
3. Run oracle/NOP and verifier integrity checks.
4. Measure difficulty empirically and inspect failure reasons.

No pass rate can make an ambiguous or impossible task fair. Conversely, a
solver failure is legitimate difficulty when the goal is clear and the missing
insight is inferable from the supplied evidence.

## Legacy compatibility

Reports without `schema_version: 3` are accepted only by the checker's default
compatibility mode so existing work is not destroyed. New batch handover,
client review, and revised-task validation must call `--require-v3` and migrate
the report. Do not add more rules to the legacy contract-transcription schema.
