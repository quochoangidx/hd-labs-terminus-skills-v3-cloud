---
name: task-revise-flag-remediation
description: Use when revising a Terminus 3 task after platform trial-analysis flags, reviewer feedback, a 0/N solvability return, or a pre-submission correlated-blind-spot audit. Separates task bugs from legitimate evidence-based difficulty, applies the smallest docs-aligned repair, preserves semantic coverage, and re-measures the empirical tier.
---

# Terminus 3 Revision and Flag Remediation

Revise from raw per-trial evidence, not from the job summary alone. Terminus 3
has four empirical tiers and six trial-analysis criteria; a revision should
repair validity without turning domain inference into a disclosed checklist.

## Sources of truth

Read, in order:

1. the exact reviewer message and trial-analysis flags;
2. per-trial trajectories, verifier logs, and per-test CTRF/readback;
3. `instruction.md` plus the agent-visible environment;
4. `tests/`, oracle, and the real authority or invariant;
5. `docs/understanding-tasks/difficulty-guidelines.md` and
   `docs/testing-and-validation/running-real-agents.md`.

Do not infer a defect from a single summary label. Preserve the original task,
reports, and probe artifacts before editing.

## First classification

Classify each failure before changing prose or tests:

| Class | Evidence | Repair direction |
|---|---|---|
| Infrastructure | build, dependency, artifact transfer, setup, refusal, or verifier never ran | repair environment/harness; never count as difficulty |
| Oracle/verifier defect | authority disagrees, flaky result, representation-specific assertion, test-only implementation | fix oracle/verifier and rerun oracle/NOP |
| Explicit-contract gap | missing output path, public schema, parameter name, exact string, or arbitrary constant | state the minimal interface fact or relax the assertion |
| Evidence-inferability gap | goal is clear but visible evidence cannot support the graded model | add authentic evidence, accept equivalents, narrow the claim, or remove the invalid test |
| Legitimate semantic miss | evidence supports the model but the solver reasons or coordinates state incorrectly | keep the challenge; do not add hints merely to raise pass rate |
| Replicated single lever | many failed rows map to one keyword, representation choice, numerical branch, or missing entry point | fix fairness/coverage, then reject Advanced+ unless multi-node geometry survives |
| Solvability/coverage risk | at least one test is 0/N across the platform sample | audit the exact case after the four classes above |

The compatibility report remains
`workspace/reports/<slug>/instruction-sufficiency.json`, but every revised task
must migrate it to `schema_version: 3` and pass:

```bash
python3 .agent/skills/terminus-regular-task-authoring/scripts/sufficiency_manifest_check.py \
  --require-v3 <task-dir> workspace/reports/<slug>/instruction-sufficiency.json
```

## Six trial-analysis flags

### `task_specification`

This flag is blocking when the agent had to guess the success surface or needed
information it could not obtain. It is not automatically valid merely because a
semantic rule was absent from `instruction.md`.

1. Identify the exact failing assertion and solver interpretation.
2. Decide whether it concerns an explicit interface fact or an inferred domain
   model.
3. For interface facts, add the smallest natural statement or make the verifier
   representation-agnostic.
4. For inferred semantics, build an evidence graph. If the visible sources and
   domain convention discriminate the competing interpretation, defend the
   task and record that evidence. If they do not, add realistic evidence,
   accept both interpretations, narrow the test, or remove it.
5. Never add a trap list, worked example, root cause, or solution path solely
   because a solver missed a legitimate inference.

### `reward_hacking`

Close access to tests, solution, reward files, or other grading channels. Test
the candidate from declared artifacts in the separate verifier. A correct but
easy solution is not reward hacking.

### `difficulty_crux`

Compare the actual failure with `[metadata].difficulty_explanation`. Fix an
incidental defect, or rewrite the explanation when the task's legitimate crux
was described inaccurately. Do not retrofit tests to force the old narrative.

### `near_miss`

Compare the exact failing test IDs across runs. Repeated failure on the same one
or few tests points first to those checks or their instruction/evidence support;
different misses across runs are more consistent with genuine difficulty. Keep
this flag about difficulty: an unstated requirement is `task_specification`.
Also replace hardware-sensitive or oracle-near thresholds with a meaningful
quality floor, structural invariant, or broad semantic criterion. Never raise a
tier merely because near-complete runs count as failures.

### `refusals`

Separate provider/setup failures from agent policy refusals. Reframe harmful or
ambiguous wording while preserving legitimate defensive/educational work. A
refusal provides no difficulty evidence.

### `low_timeout`

Raise `[agent].timeout_sec` when the solver was making progress, up to the
documented ceiling. Reduce cold rebuild cost where possible. Time starvation is
not difficulty.

## 0/N solvability returns

The platform calls a task solvable when every individual test passes in at
least one run. A 0/N test is blocking, but the repair depends on its cause.

1. Reconstruct the per-case × per-run matrix from CTRF/readback. Do not rely on
   aggregate pytest functions or the job summary.
2. Re-run the exact case against the oracle and the real authority/invariant.
3. Check environment, artifact transfer, candidate execution, and verifier
   isolation.
4. Inspect failed trajectories. Determine whether the shared miss is an
   explicit-contract gap, an evidence gap, or a legitimate but statistically
   uncovered inference.
5. Apply the smallest valid repair below and re-run fresh trials.

### Allowed repairs

- Fix an oracle, fixture, tolerance, artifact, or verifier defect.
- Split a redundant aggregate into individually reportable semantic units when
  this changes observability but not the all-or-nothing reward.
- Add a missing public schema/path/arbitrary convention in concise prose.
- Add authentic evidence a practitioner would normally possess: a trace,
  drawing, config, design record, capture, dataset, or reachable standard.
- Accept semantically equivalent outputs when the task does not require one
  representation.
- Remove a test that is redundant, invalid, flaky, over-strict, or requires
  unobtainable knowledge.
- Redesign or drop a task whose entire signal is one arbitrary hidden
  convention.

### Disallowed repairs

- Do not prune easy passing cases or tighten thresholds to manufacture a higher
  tier.
- Do not automatically delete every low-pass case from a small local sample.
- Do not disclose the inferred model, root cause, trap list, or exact fix merely
  because all sampled solvers missed it.
- Do not replace semantic verification with source-shape assertions.
- Do not keep a historical tier after the task changes; re-measure it.

## Revision verification

After any content change:

1. update source hashes and rerun both fresh V3 fairness reviews;
2. rerun instruction preflight and the V3 evidence-inferability checker;
3. rebuild agent and verifier images;
4. rerun oracle (reward 1) and NOP (reward 0);
5. rerun the affected verifier cases, then the full verifier;
6. regenerate `semantic-coverage.json`, rerun every affected dedicated mutant,
   and pass the semantic coverage checker; never retain a mechanism label merely
   because it still has many fixtures;
7. rerun the folder-level client/manual review and the task-tree style audit,
   write fresh `probe-preflight.json`, `pre-freeze-review.json`, and
   `task-style-preflight.json`, then pass `preprobe_check.py`;
8. freeze the new snapshot and rerun fresh counted difficulty trials because
   old probe snapshots are stale;
9. update `difficulty` and the external submission prose from the newly measured
   facts, run the submission-only style audit, then regenerate and review the
   exact final ZIP and submission packet.

Base and Core are valid Terminus 3 outcomes. Under an explicit Advanced+
campaign, preserve lower-tier evidence but do not count it toward the campaign
quota.

## Revision report

Return a compact table with:

- platform flag or reviewer claim;
- raw evidence and affected tests/runs;
- root-cause class;
- docs-aligned decision;
- files changed;
- oracle/NOP and verifier results;
- V3 inferability verdict;
- fresh empirical tier signal;
- remaining uncertainty or platform-only validation need.
