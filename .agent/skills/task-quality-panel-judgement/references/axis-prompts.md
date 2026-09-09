# Axis briefs and reviewer output

Use the shared instructions plus exactly one axis brief in each fresh reviewer's
prompt. Replace placeholders with the assigned axis, packet path, and snapshot
hash. Do not append historical context.

## Shared instructions

You are the sole reviewer for `<axis>` on frozen snapshot `<snapshot_sha256>`.
After the mandatory Codex skill entrypoint has loaded, read only `<packet_path>`.
The packet is your entire task-evidence universe. Do not inspect its parent, the
live repository, Git history, reports, prior reviews, or other agents. Do not
edit files, run the task, install dependencies, access the network, or spawn
subagents. Read `_panel_docs/quality-panel-judge-guide.md` and
`_panel_docs/quality-panel-examples.md` before judging.

Review only the assigned axis. A valid finding must cite concrete packet files
and lines, identify a reachable case or path, and explain how it affects grading,
reward, or solvability. Do not report generic hardening, style preferences,
speculation, or a hypothetical issue that the visible contract excludes. Do not
invent new task requirements or demand exhaustive coverage.

Inspect the complete allowed packet before answering. Work through every review
category and pre-submission checklist family for the assigned axis in the judge
guide, even after finding a `Major`. Return every independent supported finding
in this one response, not merely the first, easiest, or highest-severity issue.
Do not impose an arbitrary finding limit. Merge cases only when they have the
same root cause; list all distinct witnesses and effects under that finding.

Return JSON only, matching the schema below. Use `None` when no valid finding
exists. Use `Unsure` only when packet evidence genuinely cannot resolve a
reward-relevant concern; state what evidence is missing.

## `coherent_contract`

Judge whether the agent-visible task defines a coherent, achievable contract and
whether verifier-visible expectations are supported by that contract or by
agent-visible evidence. Do not assess whether the reference solution happens to
implement it; no solution is present. Look for contradictions, impossible
requirements, hidden arbitrary conventions, representation-specific grading,
and instruction/test asymmetry. Allow hidden instances and combinations that
exercise the same inferable model.

## `correct_reference_solution`

Judge whether the reference solution correctly implements the agent-visible
contract across relevant normal, boundary, and interaction cases. Do not inspect
or infer hidden tests; none are present. Check the solution directly against the
instruction and domain semantics. Report only a concrete incorrect behavior,
not missing optimization or preferred style.

## `protected_ground_truth`

Judge whether candidate-controlled code, artifacts, paths, processes, build
hooks, permissions, or network behavior can read, replace, predict, or influence
hidden checks, expected values, or the reward channel. Trace real execution and
ownership paths through tests and environment. A mere filename, conventional
path, or theoretical attack is insufficient without a reachable exploit path.
No solution is present.

## `sound_verifier`

Judge whether the verifier measures the promised behavior, rejects plausible
wrong or incomplete implementations, and avoids rewarding proxy behavior,
Oracle-specific representation, stale binaries, self-controlled comparisons, or
unreachable test cases. Evaluate failure localization and semantic coverage, not
raw test count. No solution is present; do not reconstruct or assume it.

## Required JSON schema

```json
{
  "axis": "coherent_contract | correct_reference_solution | protected_ground_truth | sound_verifier",
  "snapshot_sha256": "<snapshot_sha256>",
  "severity": "None | Minor | Major | Unsure",
  "summary": "one concise verdict",
  "findings": [
    {
      "id": "AXIS-1",
      "severity": "Minor | Major | Unsure",
      "claim": "specific defect",
      "reachable_case_or_path": "concrete reproducer or execution path",
      "graded_effect": "how this changes grading, reward, or solvability",
      "citations": ["relative/path:line"],
      "minimal_repair_boundary": "smallest semantic boundary that must change"
    }
  ],
  "checks_performed": ["bounded checks actually performed"],
  "coverage_sweep": [
    {
      "category": "one judge-guide category or checklist family",
      "status": "checked | not_applicable",
      "evidence": ["relative/path:line"],
      "finding_ids": ["AXIS-1"]
    }
  ],
  "uncertainty": "empty unless severity is Unsure"
}
```

When `severity` is `None`, `findings` must be empty. `coverage_sweep` must still
show that every guide category/checklist family for the axis was checked or was
inapplicable. Do not include prose before or after the JSON.
