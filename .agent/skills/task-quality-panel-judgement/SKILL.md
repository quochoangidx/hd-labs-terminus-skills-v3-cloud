---
name: task-quality-panel-judgement
description: Run a review-only Terminus 3 quality-panel audit with four fresh-context subagents, one per platform axis and with axis-specific file visibility. Use before submission, after a platform quality-panel return, or when checking whether a frozen task snapshot is ready for the pre-difficulty gate. Do not use it to fix the task, measure difficulty, or replace deterministic preflight.
---

# Terminus Quality Panel Judgement

Audit one frozen Terminus task snapshot with exactly four fresh reviewers:

1. `coherent_contract`
2. `correct_reference_solution`
3. `protected_ground_truth`
4. `sound_verifier`

The four reviewers are review-only and must not edit files. Always finish all
four axes on the same snapshot, even when an early axis returns a blocker. Never
repair between axis results: partial repair contaminates the shared snapshot and
causes serial fix-review loops.

## Select the operating mode

Use **orchestrator mode** when the user asks to run the whole panel on a task.
Follow the remaining sections to prepare packets, spawn reviewers, and combine
their verdicts.

Use **isolated reviewer mode** when the prompt assigns exactly one axis and one
packet path. Loading this `SKILL.md` is required by Codex skill dispatch and does
not count as task evidence. After loading it, do not read any other repository
path, prepare packets, spawn reviewers, or follow orchestrator steps. Read only
the assigned packet, including its `_panel_docs/`, and return the JSON required
by `references/axis-prompts.md` as reproduced in the prompt.

## Read the current judge contract

Before preparing packets, read these repository docs completely:

- `docs/testing-and-validation/quality-panel-judge-guide.md`
- `docs/testing-and-validation/quality-panel-examples.md`
- `references/axis-prompts.md`

The portal-mirrored docs are authoritative when they conflict with this skill.

## Freeze isolated review packets

Run:

```bash
python3 .agent/skills/task-quality-panel-judgement/scripts/prepare_packets.py \
  <task-dir> \
  --output workspace/reports/<slug>/quality-panel-packets
```

Use only the packet paths printed by the script. Do not point a reviewer at the
live task, its parent directory, reports, prior reviews, probes, `AGENTS.md`, or a
submission ZIP. Treat an escaping symlink as a blocker.

The packet builder enforces these visibility boundaries:

| Axis | Included task surfaces | Withheld task surfaces |
| --- | --- | --- |
| `coherent_contract` | instruction, metadata, environment, tests | solution |
| `correct_reference_solution` | instruction, solution | tests, metadata, environment |
| `protected_ground_truth` | environment, tests | instruction, metadata, solution |
| `sound_verifier` | instruction, tests | metadata, environment, solution |

Every packet also contains the two quality-panel judge documents under
`_panel_docs/` and a snapshot-bound manifest.

## Spawn four fresh reviewers

Spawn exactly one reviewer for each axis. Use:

- `fork_turns="none"`
- model `gpt-5.6-sol`
- reasoning effort `medium`
- two waves of two reviewers when only four total agent slots are available

The orchestrator does not take an axis. Each reviewer receives only:

- its assigned axis;
- its isolated packet path;
- the matching brief from `references/axis-prompts.md`;
- instructions to stay read-only, packet-only, and return the required JSON.

Each reviewer must inspect its entire allowed packet and complete every category
and checklist family for its assigned axis before returning. It must return all
independent, evidence-backed findings discovered in that one response, not only
the first or strongest blocker. Do not cap the number of findings. Merge multiple
manifestations only when they share the same root cause and retain every distinct
witness in that finding.

Tell reviewers not to spawn children. Do not reveal platform findings, previous
claims, expected verdicts, Oracle/NOP results, revision history, difficulty
results, or another reviewer's output. Fresh context means no conversation fork
and no cross-axis contamination, not merely a new agent name.

Do not stop after the first `Minor`, `Major`, or `Unsure`. Complete both waves and
collect all four verdicts before adjudication or editing.

## Consolidate once

Accept a finding only when it is:

- valid under the visible contract;
- reachable by a permitted implementation or attack path;
- capable of changing grading, reward, or task solvability;
- supported by concrete packet citations and a reproducible case or path.

Reject generic best-practice advice, speculative concerns, path guessing,
invented requirements, and requests for an exhaustive suite. Distributed visible
evidence is valid; arbitrary exact conventions still require visible authority.

Do one comprehensive but bounded discovery pass per axis. Comprehensive means
covering the whole assigned axis and returning all supported defects; it does not
mean demanding a verifier test for every imaginable input. Do not ask a reviewer
to keep searching after its final response and do not automatically spawn a
fifth reviewer. The orchestrator may
reject or downgrade a finding only with explicit counter-evidence. If a finding
remains `Unsure` or reviewers would materially conflict, offer a separate fresh
adjudication only when the user requests it.

Before any edit, deduplicate retained findings by root cause. One contract defect
may appear independently under several axes; represent it as one repair group
with every affected axis and witness attached. Order the groups by dependency:

1. contract and evidence authority;
2. reference-solution correctness;
3. verifier semantics and coverage;
4. ground-truth and reward-channel protection;
5. regenerated hashes, manifests, and submission material.

Produce one consolidated remediation batch containing all retained groups. Do
not emit a sequence of axis-by-axis repair requests.

## Repair in one batch when requested

If the user asked only for review, stop after the consolidated report. If the
user also asked to fix the task, hand the complete batch to one persistent
builder using `task-revise-flag-remediation`. The builder may inspect the whole
task, but must not receive reviewer identities or use reviewers interactively.

Apply all accepted repairs before running another semantic review. During the
repair, use deterministic checks, focused reproductions, Oracle/NOP, mutants,
and full verifier validation as appropriate. Do not respawn an axis reviewer to
check each individual edit.

Any edit creates a new snapshot and invalidates the discovery verdict. After the
batch passes deterministic validation, run exactly one fresh four-axis clearance
panel on the new snapshot. If clearance is still blocking, stop and report the
remaining defect; do not automatically enter a third repair-review cycle.

## Record the result

Write `report.md` and `report.json` under:

```text
workspace/reports/<slug>/quality-panel/<snapshot-sha256>/
```

Record each axis verdict, retained findings, rejected findings with
counter-evidence, deduplicated root-cause groups, the single remediation batch,
packet manifest hashes, reviewer model/effort, and the overall verdict. Only four
`None` verdicts pass. `Minor`, `Major`, and `Unsure` block.

Label the result as a local four-reviewer approximation. The platform panel uses
two independent frontier-model judgments per axis and adjudicates disagreement,
so this skill does not claim platform parity. Do not run difficulty after a
blocking result. Any task, verifier, solution, metadata, or environment change
invalidates the report and requires new packets and fresh reviewers.
