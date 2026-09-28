# Reviewer instructions: sound_verifier (tbrain-linux-host-intrusion-triage, creation-mode panel)

Packet (read only this directory): /Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3/workspace/reports/tbrain-linux-host-intrusion-triage/quality-panel-packets/fa3d5d1ee0370a144e73521d4f98adcc12f305c4fc6402caf6137800aa961dbf/4c0892743df059b6166221d6db6f617e85f6b0812c8fac412ea8bed85d672d0c/sound_verifier
Packet manifest: /Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3/workspace/reports/tbrain-linux-host-intrusion-triage/quality-panel-packets/fa3d5d1ee0370a144e73521d4f98adcc12f305c4fc6402caf6137800aa961dbf/4c0892743df059b6166221d6db6f617e85f6b0812c8fac412ea8bed85d672d0c/sound_verifier/packet-manifest.json

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
reward-relevant concern; state what evidence is missing. Use `Advisory` for a
supported recommendation that you are deliberately excluding from the blocking
decision, such as a requirement exercised only by one easy case with no
demonstrated incorrect outcome; `Advisory` is not a weaker `Minor`, so do not
use it to soften a defect whose wrong grading effect you can show. Blocking
thresholds are applied by the orchestrator, not by you: `Minor` and `Major`
block on every axis except `protected_ground_truth`, where only `Major` blocks.
If confirmed defects coexist with incomplete checks, retain their severity and
list the gaps separately; the panel still cannot clear. Never claim a static
trace was executed. Separate unsupported hypotheses from confirmed findings.

## `sound_verifier`

Judge whether the verifier measures the promised behavior, rejects plausible
wrong or incomplete implementations, and avoids rewarding proxy behavior,
Oracle-specific representation, stale binaries, self-controlled comparisons, or
unreachable test cases. Evaluate failure localization and semantic coverage, not
raw test count. This axis sees the instruction, environment, and tests; no
solution is present, so do not reconstruct or assume it. Judge the verifier
against the contract and the candidate-visible code it grades, not against a
guessed reference. For contract-relevant state machines, inspect whether the
initialization-to-first-event transition can affect a graded result. For signed
derived quantities, check that legal sign partitions are discriminated. Do not
treat approximate equality to zero as proof of a one-sided invariant. Finally,
distinguish semantic content from native encoding, inode/layout, package shape,
or candidate diagnostic output; report a gap only when the contract retains that
representation promise, and report a false rejection when the verifier imposes
one that it does not.

## Required JSON schema

```json
{
  "axis": "coherent_contract | correct_reference_solution | protected_ground_truth | sound_verifier | deterministic_execution",
  "reviewer_id": "<axis>-A | <axis>-B",
  "snapshot_sha256": "<snapshot_sha256>",
  "severity": "None | Advisory | Minor | Major | Unsure",
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
      "severity": "Advisory | Minor | Major | Unsure",
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

## Evidence readability note
tests/evidence/*.tar.gz are gzip tar packs of the graded evidence sets and cannot be opened with read-only tools. Every expected report and each case's range facts are plain JSONL in tests/expected/. A plain-text extraction of one sealed set (tests/evidence/edge_hi.tar.gz: gz logs gunzipped to .txt, wtmp/btmp decoded to text as documented in environment/app/docs/record-formats.md) is at /Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3/workspace/reports/tbrain-linux-host-intrusion-triage/quality-panel-packets/readable-evidence/ (about 49 KB); the visible environment/app/evidence/case-1 is the same format and is also sealed as tests/evidence/case1.tar.gz.
