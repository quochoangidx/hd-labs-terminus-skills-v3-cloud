# Task Instruction Sufficiency Gate

Use this gate before any difficulty probe. Hidden inputs, fixture identifiers,
expected outputs, and oracle implementation may remain hidden. A graded
contract rule may not.

## Required artifact

Write `workspace/reports/<slug>/instruction-sufficiency.json` outside the task
folder and ZIP. The report is local audit evidence, not agent-facing material.

```json
{
  "task": "tbrain-example",
  "verdict": "pass",
  "hidden_case_policy": {
    "hidden_inputs": true,
    "hidden_expected_outputs": true,
    "hidden_contract_rules": false
  },
  "contract_source_files": [
    {
      "path": "instruction.md",
      "sha256": "<sha256 of the reviewed instruction.md>"
    }
  ],
  "contract_rows": [
    {
      "id": "transport_policy",
      "asserted_behavior": "Only HTTPS and SCP-style git remotes are accepted.",
      "test_selectors": ["test_supported_remotes", "test_unsupported_transports"],
      "source_type": "instruction",
      "source_locator": "instruction.md:Accept HTTPS remotes and SCP-style git remotes",
      "reasonable_alternative": "Allow ssh:// because Git documents it as a standard transport.",
      "visible_contract_rejects_alternative": true
    }
  ],
  "blind_contract_review": {
    "reviewer_count": 2,
    "contract_inventory_complete": true,
    "reviewers": [
      {
        "reviewer_id": "contract-review-1",
        "runtime": "<codex|claude-code>",
        "model": "<actual model>",
        "session_id": "<actual fresh session id>",
        "fresh_context": true,
        "source_only": true,
        "reviewed_source_files": ["instruction.md"],
        "transcript": "contract-review-1.md",
        "transcript_sha256": "<sha256>"
      },
      {
        "reviewer_id": "contract-review-2",
        "runtime": "<codex|claude-code>",
        "model": "<actual model>",
        "session_id": "<different fresh session id>",
        "fresh_context": true,
        "source_only": true,
        "reviewed_source_files": ["instruction.md"],
        "transcript": "contract-review-2.md",
        "transcript_sha256": "<sha256>"
      }
    ],
    "questions": [
      {
        "id": "transport_boundary",
        "contract_ids": ["transport_policy"],
        "question": "Should ssh:// be accepted or rejected?",
        "answers_agree": true,
        "matches_oracle": true,
        "source_locator": "instruction.md:Accept HTTPS remotes and SCP-style git remotes"
      }
    ]
  }
}
```

Run:

```bash
scripts/python3 .agent/skills/terminus-regular-task-authoring/scripts/sufficiency_manifest_check.py \
  workspace/<slug> workspace/reports/<slug>/instruction-sufficiency.json
```

The command must pass before local solve probing, coverage remediation,
platform-candidate packaging, or submission packaging.

## Contract sources

Every semantic test or cluster must resolve to exactly one visible source:

- `instruction`: an observable rule stated in `instruction.md`.
- `environment_reference`: a contract, format, examples, or data file under
  `environment/` that the agent can read offline.
- `reachable_authority`: a pinned authority that is actually callable or
  readable inside the task image without network access.
- `visible_training_data`: a behavior learnable from the visible labeled
  archive rather than from an oracle-only labeling rule.

For `visible_training_data`, record `support.training_path`, at least two
positive examples, at least two contrast examples, and an empty
`hidden_only_feature_values` list. Increase those counts when the interaction
has several degrees of freedom. A hidden validation row may be new; a hidden
feature value, interaction family, threshold, or policy may not.

For `reachable_authority`, record `authority_command` and
`offline_reachable: true`, then execute that command in the final image. Naming
an unavailable standard or runtime is not evidence.

## Reasonable-alternative test

For each row, write the strongest implementation a competent developer could
justify from the visible files but that the oracle rejects. The visible
contract must unambiguously reject it. If it does not, fix one of these:

1. State the missing observable fact in concise prose.
2. Add an agent-visible contract/reference artifact.
3. For ML, add disjoint positive and contrast training examples.
4. Relax or remove the assertion.
5. Drop the task if disclosure removes its entire difficulty wall.

Do not use solver success as the source. A solver can guess an undocumented
rule correctly.

## Blind contract review

Run two independent reviews with only `instruction.md` and `environment/`.
Do not provide tests, solution, oracle outputs, suspected gaps, or desired
answers. Derive decision questions from every graded boundary, then compare the
answers after both reviews finish.

The gate fails when reviewers disagree, agree on an answer different from the
oracle, cannot cite a visible source, or infer a rule only from existing buggy
code that contradicts the expected policy. Fix the contract and repeat the
blind review with fresh context.

Record the actual runtime, model, unique session ID, raw transcript, and SHA-256
for both reviews. Hash every reviewed contract source in
`contract_source_files`; any later instruction/reference edit invalidates the
manifest. `contract_inventory_complete: true` is an explicit two-reviewer
attestation that every normative promise was classified as graded or deliberately
ungraded, so the audit covers both directions: tests-to-contract and
contract-to-discriminating-tests.

## Separation from other gates

- Sufficiency asks where an agent is allowed to learn each graded rule.
- Difficulty asks whether agents implement or infer that visible rule correctly.
- Coverage asks whether each visible test unit has at least one passer.

Run them in that order. Oracle/NOP success, 0/N difficulty, union coverage, and
platform sample size never override a sufficiency failure.
