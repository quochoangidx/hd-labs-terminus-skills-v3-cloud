# Axis briefs and reviewer output

Use the shared instructions plus exactly one axis brief in each fresh reviewer's
prompt. Replace placeholders with the assigned axis, reviewer ID, packet path, and snapshot
hash. Do not append historical context.

## Shared instructions

You are independent reviewer `<reviewer_id>` for `<axis>` on frozen snapshot
`<snapshot_sha256>`. Review the entire axis yourself; do not split coverage,
coordinate, or consult the other reviewer. Your verdict must stand on its own.
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

Reconcile the packet manifest with files actually read. Paginate truncated
content; file names, test counts, generator plans, and a claimed checklist sweep
do not substitute for reading the relevant implementation and assertions.
Record missing dependencies, unread ranges, and unsupported formats explicitly.
If a required check cannot be completed, mark it `unresolved`, never `checked`.
File length alone (including over 800 lines) is not a defect. Do not demand
arbitrary splitting, minification, or lost coverage to meet a line count. Small
files also require complete inspection; aggregate tool output can be truncated.

Review in two directions within this single response: each guide family, then
task-relevant interactions between rules. Trace only combinations grounded in
the contract and visible implementation, not a Cartesian product. After finding
a defect, follow its invariant through sibling branches and relevant
interactions before returning. For verifier coverage, identify an assertion
that distinguishes a plausible wrong implementation; a named fixture may mask
the defect because of its other inputs. Do not assume Oracle agreement is an
independent correctness argument.

Return JSON only, matching the schema below. Use `None` when no valid finding
exists and required inspection is complete. Use `Unsure` when packet evidence cannot resolve a
reward-relevant concern; state what evidence is missing.
If confirmed defects coexist with incomplete checks, retain their severity and
list the gaps separately; the panel still cannot clear. Never claim a static
trace was executed. Separate unsupported hypotheses from confirmed findings.

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
  "reviewer_id": "<axis>-A | <axis>-B",
  "snapshot_sha256": "<snapshot_sha256>",
  "severity": "None | Minor | Major | Unsure",
  "summary": "one concise verdict",
  "input_completeness": {
    "status": "complete | incomplete",
    "files_read": ["relative/path"],
    "missing_dependencies": [],
    "unread_or_truncated_ranges": []
  },
  "findings": [
    {
      "id": "AXIS-1",
      "severity": "Minor | Major | Unsure",
      "claim": "specific defect",
      "finding_evidence": {
        "status": "static_proof",
        "expected_behavior": "derived from cited contract, not Oracle output",
        "actual_behavior": "predicted behavior from the cited path",
        "trace_or_receipt": "step-by-step proof; not an execution claim"
      },
      "reachable_case_or_path": "concrete reproducer or execution path",
      "graded_effect": "how this changes grading, reward, or solvability",
      "citations": ["relative/path:line"],
      "root_invariant": "general rule violated by this and sibling cases",
      "authority": ["relative/path:line"],
      "implementation_sites": ["relevant packet path:line"],
      "sibling_variants": ["same invariant on another branch or subtype"],
      "interaction_variants": ["boundary where this invariant meets another rule"],
      "minimal_repair_boundary": "shared semantic boundary that must change",
      "closure_evidence": ["checks or mutants that would prove the invariant-wide repair"]
    }
  ],
  "checks_performed": ["bounded checks actually performed"],
  "coverage_sweep": [
    {
      "category": "one judge-guide category or checklist family",
      "status": "checked | not_applicable | unresolved",
      "reason": "what was checked, why inapplicable, or what is missing",
      "evidence": ["relative/path:line"],
      "finding_ids": ["AXIS-1"]
    }
  ],
  "interaction_sweep": [
    {
      "rules": ["two relevant contract rules"],
      "case_or_path": "concrete interaction traced",
      "status": "checked | not_applicable | unresolved",
      "evidence": ["relative/path:line"],
      "finding_ids": []
    }
  ],
  "unresolved_checks": [
    {
      "concern": "unverified hypothesis or missing mandatory inspection",
      "finding_evidence": "unverified_hypothesis",
      "missing_evidence": "what would resolve it"
    }
  ],
  "uncertainty": "empty unless severity is Unsure"
}
```

When `severity` is `None`, `findings` must be empty. `coverage_sweep` must still
show that every guide category/checklist family for the axis was checked or was
inapplicable, `input_completeness.status` must be `complete`, and
`unresolved_checks` must be empty. Use empty arrays when there are no gaps; do
not copy illustrative unresolved entries. For every finding, the variant lists must cover plausible sibling
branches visible in the packet rather than merely restating its reproducer. Use
an empty list with an explicit reason when no relevant sibling or interaction
is identified; this is not proof that none could exist. Do not include prose before or after the
JSON.
