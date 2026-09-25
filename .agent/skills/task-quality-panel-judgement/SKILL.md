---
name: task-quality-panel-judgement
description: Run a review-only Terminus 3 quality-panel audit with fresh-context subagents, isolated per-axis file visibility, and evidence-based consolidation. Runs as the pre-submission panel of the default builder_certified task-creation route (five-axis discovery, clearance on changed axes, panel_gate.py packaging receipt), and after a platform quality-panel return (two reviewers on the returned axis). Does not itself authorize repairs or replace deterministic gates or difficulty measurement.
---

# Terminus Quality Panel Judgement

Reviewers are the expensive instrument here. Point them at a known target.

This skill has two jobs. During task creation under the default
`builder_certified` profile it is the **pre-submission panel**: the builder's
receipts show the task agrees with itself, and this panel finds what the
platform panel would return before upload (the two `builder_certified` tasks
submitted on 2026-09-24 without it came back with 37 findings each). After a
platform return it is **diagnosis**: reproduce the reported finding locally on
the axis it names, and prove the repair closes it, rather than resubmitting and
waiting.

Audit one frozen Terminus task snapshot with fresh reviewers, two independently
reviewing the full scope of an axis, across these five:

1. `coherent_contract`
2. `correct_reference_solution`
3. `protected_ground_truth`
4. `sound_verifier`
5. `deterministic_execution`

Reviewers are review-only and must not edit files. Finish every axis you started
on the same snapshot, even when an early one returns a blocker. Never repair
between axis results: partial repair contaminates the shared snapshot and causes
serial fix-review loops.

## Select the operating mode

Use **creation mode** when `task-batch` reaches `builder_certified` step 8
(`../task-batch/references/execution-profiles.md`), after the probe cleared
CORE+. Run the full five-axis discovery panel below (ten reviewers) on the
probed snapshot, consolidate once, and repair in one batch. Choose clearance
axes mechanically, never by judgement:

```bash
python3 .agent/skills/task-quality-panel-judgement/scripts/panel_gate.py \
  clearance-axes <task-dir> \
  --discovery-manifest <discovery packet-manifest.json> \
  --finding-axis <axis-with-retained-blocking-finding>   # repeat
```

Spawn two new reviewers on fresh packets for every axis in `clearance_axes`: the
axes with findings plus every axis whose visible files the repair changed. An
axis in `carried_axes` keeps its discovery verdict because its reviewers would
see identical bytes. Skip clearance when discovery is five-axis non-blocking. A
blocking clearance stops as `rescope_required`, as in orchestrator mode. Before
packaging, `panel_gate.py check <task-dir> --report <report.json>` must pass on
the exact snapshot; see *Record the result* for the fields it reads. Report the
result as a creation-mode panel, not `local_panel_cleared`.

Use **targeted mode** after a platform return. Run **only the
returned axis**, two reviewers, on the exact returned snapshot. For a
`builder_certified` task the resubmission then follows
`../task-revise-flag-remediation/SKILL.md` *Verification under
`builder_certified`*: the returned snapshot's packets are the baseline for
`panel_gate.py clearance-axes`, and `panel_gate.py check` must pass before
upload. Read the platform
report first and classify its findings with
`../task-revise-flag-remediation/SKILL.md`; use this skill to reproduce a finding
you could not confirm by reading, or to show a repair closed it. Two sessions,
not ten. Do not widen to other axes because they are cheap to add — they are not.

Use **orchestrator mode** only when the user explicitly asks for a full panel, or
when the active profile is `panel_ready`. Follow the remaining sections to
prepare all five packets, spawn ten reviewers, and combine their verdicts.

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

When at least one finding is retained, also read
`../task-revise-flag-remediation/references/root-cause-remediation.md` completely
before mapping root causes.
Its editing steps apply only when repairs were requested.

The portal-mirrored docs are authoritative when they conflict with this skill.

## Require the deterministic gate first

The obligation gate now lives with the other gates, in
`../terminus-regular-task-authoring/`: `scripts/panel_precheck.py` and
[`references/panel-precheck.md`](../terminus-regular-task-authoring/references/panel-precheck.md).
Every profile runs it, panel or not.

A passing snapshot-bound `panel_precheck.py --full` is a precondition for
spawning any reviewer. Fix deterministic blockers first — they cost nothing to
find and a reviewer session to rediscover. Do not expose the manifest or the
precheck result to reviewers; they must judge the task surfaces independently.

`mechanically_ready` is not an axis verdict. The script cannot prove semantic
coherence, reference correctness, completeness against an omitted branch, or
acceptance of every alternate valid implementation. Never convert its output
to `None` or skip the semantic panel because the precheck passes.

## Freeze isolated review packets

In orchestrator mode, read
[panel input hygiene](../terminus-regular-task-authoring/references/panel-input-hygiene.md).
Record per-file line/byte counts, largest contributors, and per-axis aggregate
packet bytes in the existing report; label any token estimate with its method.
Over 800 lines is advisory, not a platform cap or reason to edit a frozen task.
Neither short files nor splitting a corpus guarantees complete platform reads.

Before building, trace instruction-referenced normative documents and their
transitive dependencies. Resolve runtime paths using the environment build
layout, not guessed prefix substitutions. For each needed authority record its
task-relative path, citing source, candidate visibility, and dependency links,
and note it with `--contract-file environment/<path>` so the packet manifest
carries the inventory. Every axis packet already contains the whole
`environment/`, so this records an authority rather than granting access to it,
and the orchestrator must still verify semantic dependency completeness.
If an authority is absent, inaccessible, or lives outside `environment/` where
only the withheld tests or solution define it, report an input-preparation
blocker rather than inventing its contents or silently weakening isolation. Do
not start paid reviewers on a known incomplete packet. Keep the dependency
inventory beside the root manifest.

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
| `correct_reference_solution` | instruction, environment, solution | tests, metadata |
| `protected_ground_truth` | instruction, environment, tests | metadata, solution |
| `sound_verifier` | instruction, environment, tests | metadata, solution |
| `deterministic_execution` | instruction, metadata, environment, solution, tests | none |

Every packet also contains the two quality-panel judge documents under
`_panel_docs/` and a snapshot-bound manifest.

These surfaces follow the guide: contract, ground-truth and verifier review
receive the candidate-visible contract/environment plus the tests and never the
reference; reference review receives the contract/environment plus the reference
and never the tests; determinism review inspects all three. Never expose tests to
the reference reviewer, or solution to the `coherent_contract`,
`protected_ground_truth`, and `sound_verifier` reviewers.

`task.toml` is submission metadata whose explanation fields can disclose the
intended solution and verifier, so it stays out of every packet the guide does
not require it in. That is the one deliberate narrowing left, and it removes
disclosure rather than context.

Because every packet now carries the whole environment, `--contract-file` no
longer widens visibility; it records the cited authority in the packet manifest,
which keeps the dependency inventory auditable. Packet recipes include document
hashes and the selected file list; changed recipes preserve earlier packets under
the same task snapshot rather than silently reusing stale judge docs.

## Spawn fresh reviewers

In targeted mode, spawn exactly two reviewers for the one returned axis and stop;
everything below about five packets and ten reviewers applies to a full panel.

Spawn exactly two reviewers (`A` and `B`) for each axis in scope. Keep one packet per axis;
both reviewers of an axis receive the same packet bytes and the same full brief,
not complementary checklist halves. Record unique IDs `<axis>-A` and `<axis>-B`.
Use:

- `fork_turns="none"` (Codex) or a fresh `Agent` subagent with no conversation
  context (Claude Code)
- model `gpt-5.6-sol` on Codex, Opus 5 on Claude Code (`model: "opus"`); never
  mix runtimes within one axis pair
- reasoning effort `medium` (on Claude Code use the `terminus-panel-reviewer`
  agent profile, which pins Opus and medium effort)
- schedule within available slots; with four total slots, use five waves of two
  reviewers (one axis pair per wave), keeping the orchestrator outside the pair

The orchestrator does not take an axis. Each reviewer receives only:

- its assigned axis and reviewer ID;
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
and no cross-reviewer contamination, including within an axis, not merely a new
agent name. Do not reuse a discovery reviewer for clearance. Independence means
separate fresh sessions, not necessarily different model families.

Do not stop after the first blocking or undecided verdict. Collect all ten
responses before adjudication or editing. A crashed, missing, or malformed
response is an incomplete review, never a `None` vote; preserve it and report
the panel incomplete rather than silently reducing to one reviewer per axis.

## Consolidate once

For each axis, take the union of both reviewers' findings and concerns, retaining
source IDs such as `<axis>-A/AXIS-1`. Do not take only the intersection, average
severities, or use a `None` vote to cancel a concrete finding. Agreement alone
also does not prove a finding. After checking all ten responses, adjudicate
each claim against the frozen evidence using the rules below, then produce
five axis verdicts before deduplicating across axes into one remediation batch.

First validate `input_completeness`, `coverage_sweep`, `interaction_sweep`, and
`unresolved_checks`. A checklist assertion without cited inspection is not
coverage. Missing/truncated mandatory evidence or unfinished applicable checks
blocks clearance even if a reviewer says `None`; record review incompleteness,
not a confirmed task defect. Preserve the raw verdict separately.

Accept a finding only when it is:

- valid under the visible contract;
- reachable by a permitted implementation or attack path;
- a concrete contract violation or grading, reward, or solvability defect,
  with severity calibrated using the guide (narrow confirmed defects may be Minor);
- supported by concrete packet citations and a reproducible case or path.

Record `finding_evidence` as `reproduced`, `static_proof`, or
`unverified_hypothesis`, with contract-derived expected behavior, observed or
predicted actual behavior, and the trace/reproduction receipt. Reviewers remain
read-only and do not execute tasks: their traces are static proof, not runs.
The orchestrator may run focused reproductions in disposable copies when safe;
do not mutate the frozen task. Unverified hypotheses go to `unresolved_checks`,
not the repair batch. Resolve or explicitly reject them with evidence; never
repair merely to agree with a model, and never silently discard an unresolved
reward-relevant concern to obtain clearance.

Reject generic best-practice advice, speculative concerns, path guessing,
invented requirements, and requests for an exhaustive suite. Distributed visible
evidence is valid; arbitrary exact conventions still require visible authority.

Do one comprehensive but bounded discovery pass per reviewer. Comprehensive means
covering the whole assigned axis and returning all supported defects; it does not
mean demanding a verifier test for every imaginable input. Do not ask a reviewer
to keep searching after its final response and do not automatically spawn an
eleventh reviewer or third panelist for an axis. The orchestrator may
reject or downgrade a finding only with explicit counter-evidence. If a finding
remains `Unsure` or reviewers would materially conflict, offer a separate fresh
adjudication only when the user requests it. Record unresolved material conflicts
as `Unsure`; do not automatically adopt the higher raw severity. Each merged
axis verdict is the highest confirmed defect severity, or `None` if none remain
and both reviews are complete with all material concerns resolved. Track review
incompleteness separately and block clearance even when defects are confirmed.

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

For every repair group, complete the root-invariant map required by
`../task-revise-flag-remediation/references/root-cause-remediation.md`: contract
authority, violated invariant,
all reachable implementation sites, sibling and interaction variants, chosen
repair boundary, proof obligations, and five-axis regression risks. A platform
reproducer is one witness, not the repair scope. Do not edit until every retained
finding belongs to a complete root-invariant map.

## Repair in one batch when requested

If the user asked only for review, stop after the consolidated report. If the
user also asked to fix the task, or the panel runs in creation mode (a
`task-batch` run authorizes its own repairs), hand the complete batch to one persistent
builder using `task-revise-flag-remediation`. The builder may inspect the whole
task, but must not receive reviewer identities or use reviewers interactively.

Apply all accepted repairs before running another semantic review. During the
repair, use deterministic checks, focused reproductions, Oracle/NOP, mutants,
and full verifier validation as appropriate. Do not respawn an axis reviewer to
check each individual edit.

Repair the invariant at its shared authority boundary. Avoid case-specific
conditions that only satisfy the reported reproducer. Use the repair-option
comparison in `../task-revise-flag-remediation/references/root-cause-remediation.md`:
repair, narrow, remove,
expand only when justified, or retire/redesign. No fixed shrink-first or
add-first order applies. Compare retained task value with coupling, regression
risk and validation cost; inspect prior attempts and stop non-converging symptom
patches. Removing a separable non-core feature must remove its obligations
coherently, not merely its failing tests. Core removal or replacement requires
appropriate user scope. Preserve retired artifacts; do not package or probe a
retired task as if repaired. Add only discriminating witnesses needed for the
retained independent branches and interactions.

Any edit creates a new snapshot and invalidates the discovery verdict. Outside
creation mode, after the
batch passes deterministic validation, run exactly one fresh five-axis clearance
panel with ten new reviewers (two per axis) on the new snapshot. In creation mode
the clearance covers only the axes `panel_gate.py clearance-axes` lists (see
*Select the operating mode*): new packets on the new snapshot, two fresh
reviewers per listed axis. This is 20
reviewer responses across discovery and clearance, not 20 on one snapshot.
If clearance is still blocking, stop and report the
remaining defect; do not automatically enter a third repair-review cycle.
Set the disposition to `rescope_required` when continuing would preserve the
same obligation set. Another authorized attempt must first revise the bounded
scope ledger by moving non-core obligations to supplied support or explicit
non-goals; it is not another clearance round. Do not label iterative panel
rounds as final or increment a task revision for validation/repackaging alone.
Classify remaining clearance findings as a discovery miss, repair-introduced
regression, or unresolved evidence, using before/after receipts where available;
use unknown when the evidence cannot distinguish them. Do not infer that a newly
reported issue was caused by the latest edit.

## Record the result

Write `report.md` and `report.json` under:

```text
workspace/reports/<slug>/quality-panel/<snapshot-sha256>/
```

`report.json` must carry the fields `panel_gate.py check` reads: top-level
`snapshot_sha256` (the snapshot the report certifies) and `axes`, one entry per
axis with `verdict` (`None`, `Minor`, `Major`, `Advisory` or `Unsure`),
`complete` (true only when both reviews finished), and `packet_manifest` (the
root `packet-manifest.json` whose packet that axis's deciding pair reviewed). A
carried axis points at the discovery manifest; a cleared axis at the clearance
manifest. The check fails a stale verdict whenever the task's files for that
axis differ from the reviewed packet, so write the creation-mode report for the
final snapshot, not the discovery one.

Preserve the ten raw responses separately as `reviewers/<axis>-A.json` and
`reviewers/<axis>-B.json`; never overwrite them with merged verdicts. In
`report.json`, each axis's `reviewers` lists the two raw files of the pair that
decided it, and `verdict` is the adjudicated merge of their `severity` fields
(the raw schema calls it `severity`). An axis carried from a platform report
instead sets `"source": "platform"` and `platform_report` to the saved report;
`panel_gate.py check` rejects any other verdict without two raw reviews of that
exact packet. Record
per-reviewer model/effort, packet hash, coverage and completion status. In the
combined report, include each pair's raw verdicts, union finding IDs, per-claim
disposition (`retained`, `rejected`, or `unresolved`) and supporting evidence,
and the five merged axis verdicts. Record retained findings, rejected findings with
counter-evidence, deduplicated root-cause groups, the single remediation batch,
root-invariant maps and closure evidence, packet manifest hashes, reviewer
model/effort, input completeness, interaction sweeps, finding evidence,
unresolved checks, and the overall verdict. Blocking follows the portal
thresholds: `Minor` and `Major` block on `coherent_contract`,
`correct_reference_solution`, `sound_verifier`, and `deterministic_execution`,
while only `Major` blocks on `protected_ground_truth`. Findings this panel
explicitly marks `Advisory` do not block. `Unsure` is not itself a confirmed
defect and does not block on its own, but an incomplete review still blocks
clearance because the axis was never decided; track that separately from
severity.

Report both severities the way the platform does: an **Overall severity**
summarizing the axis ratings and a **Blocking severity** applying the
thresholds above. `Overall severity: Minor` with `Blocking severity: None` is a
valid outcome when the only issue is a `protected_ground_truth` Minor or an
`Advisory` finding. When a reviewer response is missing, crashed, or malformed,
label the run `PANEL INCOMPLETE` and say which axes did finish, since their
findings still block; label it `PANEL DEGRADED` when a configured reviewer was
replaced or substituted, and state where the decision rests on a single review.

Label the result as a local ten-reviewer, five-axis approximation. The guide describes
two judgments per axis and disagreement adjudication, but observed reports also
show smart merges and provider fallbacks. Do not promise an exact runtime model
or platform parity. `None` means no confirmed defect found in this bounded
review, not exhaustive correctness or guaranteed platform acceptance. More
reviewers or higher effort are not automatic remedies for incomplete evidence.
Do not run difficulty after a
blocking result. Any task, verifier, solution, metadata, or environment change
invalidates the report and requires new packets and fresh reviewers for every
axis whose packet files changed; in creation mode `panel_gate.py` decides which
axes those are, and the unchanged ones carry.
