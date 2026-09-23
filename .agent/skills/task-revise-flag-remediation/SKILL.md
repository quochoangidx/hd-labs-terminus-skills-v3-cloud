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

When the return is a quality-panel report, also read
`docs/testing-and-validation/quality-panel-judge-guide.md` and
`docs/testing-and-validation/quality-panel-examples.md` before classifying any
finding.

For Hardware / CAD, also read
`docs/creating-tasks/cad-task-guidelines.md` before classifying a geometry miss.

Do not infer a defect from a single summary label. Preserve the original task,
reports, and probe artifacts before editing.

## First classification

Classify each failure before changing prose or tests. Every row below has an
unwritten second option — **stop promising the thing** — which is correct
whenever the promise is not core to the hard thing the task tests. The repair
directions named here are what to do when it *is* core; see
[the earn-its-place question](#ask-whether-the-promise-earns-its-place-before-asking-how-to-satisfy-it)
before applying one.

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

## Platform quality-panel returns

A panel return is a separate input from the trial-analysis flags. Read the
report before classifying anything.

### Ask whether the promise earns its place, before asking how to satisfy it

A finding means one of two things: something the task promised is not backed, or
a test does not check what it claims to. There are **two equally valid answers**:

1. **Make it true** — fix or properly defend the behavior.
2. **Stop promising it** — remove the scope or the assertion.

Most revisions take only the first, and that is what produces the revision loop.
A finding reads like a to-do list, so the reflex is to add: more tests, more
contract detail, more edge-case promises. Each addition is new surface the panel
judges, which yields new findings, which invite more additions.

So for every finding, ask first: **does this thing earn its place in the task?**

| Answer | Do |
|---|---|
| Core to the hard thing the task tests | Back it properly, even if that is real work |
| Not core | Remove it — the finding goes away with it |

Remove the obligation, its assertions and its contract prose in one move. A
promise left in the instruction after its test is deleted is still a promise the
panel will enforce, and now nothing defends it — strictly worse than before the
removal. Record the drop in the obligation manifest:

```json
"removed_obligations": [
  {"id": "RETRY", "reason": "not core; the task is about authority selection",
   "former_anchor": {"file": "instruction.md", "anchor": "retries the delivery"}}
]
```

`panel_precheck.py --full` then fails if that sentence still reads in the task,
so a half-removed promise cannot ship quietly. Drop its `wrong_paths`, witnesses
and authority anchors in the same edit.

**Re-measure after removing.** Trimming changes the thing the solvers face, so
every difficulty signal collected before the cut is stale. Rerun the blind solve
probe and confirm the bar still holds; do not carry a tier or a probe result
across a scope change.

This is the intended use, not a loophole. Exhaustive coverage of nit-picky edge
cases is not wanted; a tight task that does one hard thing properly is. Only
promise what the task is actually about.

**Do not cut into difficulty.** The task must still clear the bar — since
2026-09-15 at least 3 of the 8 platform runs must fail. Trimming until the task
is easy swaps one failure for another. **Cut breadth, keep the hard thing.**

### Signs you are already in the loop

- assertions accumulating into the hundreds;
- findings moving to a different axis each round;
- ten or more revision rounds on one task;
- the same axis failing with a new finding every round.

When any of these hold, try the reverse move: take the flagged promise **out**
rather than building on top of it, and see what the next run says. If the core
itself is what cannot be backed, that is a retirement/redesign decision, not
another repair round — see `references/root-cause-remediation.md`.

Read **Blocking severity** as well as **Overall severity**. `Minor` and `Major`
block on `coherent_contract`, `correct_reference_solution`, `sound_verifier`,
and `deterministic_execution`; on `protected_ground_truth` only `Major` blocks.
Findings explicitly marked `Advisory` are excluded from the blocking decision.
`Unsure` or `not finished` is not a confirmed task defect, so do not change a
valid requirement to satisfy one; check the evaluation status instead. An
`Overall severity: Minor` with `Blocking severity: None` needs no repair to
proceed. `PANEL INCOMPLETE` means some review work did not finish, and findings
on axes that did finish still block. `PANEL DEGRADED` means a configured
reviewer was replaced or lost. For a stuck evaluation or an execution error,
request support with the submission identifier and report rather than editing
the task.

### Work from the snapshot the platform judged

Restore the task from the **exact returned artifact** before reading a finding
against it. A working tree that has drifted since the upload is a different task:
a finding may not reproduce on it, or may reproduce for a different reason, and
either way the evidence you collect is about something the panel never saw. Keep
any diverged tree only as a rollback artifact under the report directory.

Record both hashes — the snapshot returned and the snapshot you will resubmit —
in the revision ledger below. Every reproduction receipt binds to the first and
every closure receipt to the second; the gate rejects a reproduction taken on the
repaired tree, because that shows a test passing rather than a defect existing.

### Answer each finding in the ledger

The build path runs on receipts and the revision path used to run on prose. That
asymmetry is where a return gets answered with "repaired" and comes back with the
same finding a round later. Keep
`workspace/reports/<slug>/revision-ledger.json` and validate it:

```bash
GATE=.agent/skills/terminus-regular-task-authoring/scripts/revision_ledger_check.py

# 1. the digest of the artifact the platform judged, from the restored returned tree
python3 $GATE workspace/returned/<slug> x --print-snapshot

# 2. start the ledger, bound to the tree you are repairing
python3 $GATE workspace/tasks/<slug> workspace/reports/<slug>/revision-ledger.json --init

# 3. after answering every finding
python3 $GATE workspace/tasks/<slug> workspace/reports/<slug>/revision-ledger.json \
  --manifest workspace/reports/<slug>/panel-precheck-manifest.json
```

`--manifest` is optional, but without it the gate cannot confirm that a dropped
promise also left the prose. Supply it for any task that has an obligation
manifest; a task returned from before the manifest existed can omit it, and the
`dropped` rows are then trusted rather than checked.

One row per numbered finding, with `decision` one of:

| `decision` | Required evidence |
|---|---|
| `backed` | a reproduction receipt on the returned snapshot **and** a closure receipt on the repaired one. A closure alone shows a test passing that may never have failed |
| `dropped` | the `removed_obligation_id`, cross-checked against the manifest so `panel_precheck.py` can confirm the prose left too |
| `disputed` | the contract passage cited and a reproducible counterexample — a dispute without both is an opinion |
| `acknowledged` | non-blocking findings only; the gate refuses it on a blocker |

Every row also carries `gate`: the rule this finding bought, or
`not_mechanizable` with the reason. And every `P`-finding the report carries
forward needs an explicit `response` — the report omitting one does not resolve it.

Read every numbered finding. One axis can carry several distinct issues, so
resolving the opening example may leave another finding open. For each finding:

1. read the cited files in the submitted version and identify the requirement,
   the affected behavior, and the evidence offered;
2. construct the smallest relevant case — for a verifier finding, an incorrect
   submission that is accepted or a contract-valid submission that is rejected;
   for a reference finding, the input with expected versus actual output;
3. decide whether the promise is core, then either repair the responsible
   component while keeping the intended task intact, or remove the promise with
   its assertions, contract prose and manifest entry together;
4. verify both sides, so the correct solution passes and the specific wrong
   behavior fails, retaining the input, output, command, and result;
5. summarize each resolution, naming the finding, the changed file or rule, and
   the evidence. Dispute a finding with the same level of detail.

An execution line changes what the finding establishes, not whether it must be
answered:

| Report wording | What was observed |
|---|---|
| `Exploit proven by execution` | a submission with the described defect was accepted |
| `Defect proven by execution` | the grader rejected a submission described as contract-valid |
| `Reference failure proven by execution` | the task's own grader did not accept the shipped reference |

A proof demonstrates the tested behavior, not exhaustive coverage, and may raise
an axis from `Minor` to `Major`. The absence of an execution line does not clear
a finding: a defect can be established by reading the files, and an unsuccessful
or unfinished reproduction leaves the finding unchanged. Contract and
determinism findings never use that execution stage. Contest a claim only with
the cited contract passage and a reproducible counterexample, for instance when
the claimed contract validity or reachability is wrong.

A conditional `Previous review` section carries earlier findings forward as
`P1`, `P2`, and so on; its absence does not mean an old finding was resolved.
`closed` means the reviewing models consider it addressed, `STILL OPEN` means at
least one still identifies it, `not_a_defect` means the earlier claim was
rejected on reinspection, and `mixed` or `unanswered` means the history reached
no single answer — those two labels alone do not prove a repair failed. These
are statuses of earlier findings, not replacements for the current axis
verdicts, so a revision can close an old issue and uncover a different one.
Include a short explicit response to each earlier finding in the revision notes.

Passing the panel allows difficulty measurement; it is not task acceptance.

## Expertise-floor (`difficult`) returns

The blocking `difficult` check is separate from both the panel and the tier. It
judges whether the task requires genuine domain expertise — graduate-level
knowledge or several years of professional experience — independently of how
often agents solve it, and it applies at every tier including `base`.

A task returned on this check needs deeper domain reasoning, not a lower pass
rate. Lengthening the work, adding obscure facts, expanding a checklist, or
inflating data volume does not clear the floor. Re-anchor the task on
substantive domain reasoning instead: a choice between valid methods under real
constraints where the wrong choice still looks right, a plausible-but-wrong
result whose shape passes a surface check, or interacting constraints and edge
cases a generic approach misses.

Fix `[metadata].difficulty_explanation` in the same pass when it argues from a
measured pass rate or tier: the field must state why the task is inherently a
challenge for a human expert, which is what this check reads. Do not lower the
declared tier to answer a `difficult` return.

## Six trial-analysis flags

`task_specification` and `reward_hacking` are definite issues: a flag on either
sends the task back. `difficulty_crux`, `near_miss`, `refusals`, and
`low_timeout` must be examined on their own merits — repair the task when the
flag's reason holds up, and otherwise record why it does not rather than
editing to silence it. The multiple-Medium reviewer rule does not apply to
these four.

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

For CAD misses, first verify that the check can observe the claimed feature:
coarse point probes only bound an edge, volume floors are proxies, and reading
a stored parameter does not prove recompute behavior. Measure the Oracle's built
solid, calibrate sampling grain against tolerance, test free pose/construction
choices, and drive a fresh parameter value through recompute before treating a
shared failure as solver difficulty.

### `refusals`

Separate provider/setup failures from agent policy refusals. Reframe harmful or
ambiguous wording while preserving legitimate defensive/educational work. A
refusal provides no difficulty evidence.

### `low_timeout`

Raise `[agent].timeout_sec` when the solver was making progress, up to the
documented ceiling of 18000 seconds (the minimum is 1800). Reduce cold rebuild cost where possible. Time starvation is
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

## Every finding buys a permanent gate

A return is expensive. Spend it once.

After a platform finding is repaired and verified, convert the *class* of defect
into a deterministic rule, so it cannot recur in any future task:

1. Name the class, not the instance. "This task's rounding convention had no
   visible sentence" is an instance; "an exact convention with no authority
   anchor" is the class.
2. Add the rule to `panel_precheck.py` (or the relevant gate script) with a test
   that fails on the shape you just fixed and passes on the repaired snapshot.
3. Run the new rule over the existing corpus before committing it. **Any failure
   on a task that already passed the platform is a bug in the rule until proven
   otherwise** — roughly four in five such rows have been. Fix the rule to judge
   the property rather than one spelling; do not edit the passing tasks.
4. If the class cannot be mechanised — it needs semantic judgement — record it in
   `AGENTS.md` §2 as a known exposure, naming what no script will catch.

Skipping this turns each return into pure cost. Under `builder_certified`, where
gates stand in for a review panel, it is the only mechanism by which the process
improves at all.

A gate the builder believes is wrong is recorded as a `documented_exception` in
the manifest with its reason and contract citation. Never silently reshape a task
to satisfy a rule you think is mistaken: with no panel above the scripts, a wrong
gate otherwise rewrites correct work without anyone noticing.

## Revision verification

For quality-panel-driven repairs, read
[root-cause remediation](references/root-cause-remediation.md)
before choosing edits. Compare repair, narrowing, removal, justified expansion,
and retirement/redesign per confirmed root cause; the smallest textual patch
is not necessarily the smallest total repair. Use prior attempts and concrete
closure evidence to abandon non-converging strategies, not model verdict counts.
Drop separable low-value surface coherently when authorized; never delete a
failing test while retaining its promise. If only the core can be removed, stop
and propose task retirement/redesign unless that decision is already authorized.
Preserve artifacts; this is not authorization for destructive deletion.

When the input is a five-axis quality-panel report, collect and adjudicate every
axis before editing. Deduplicate overlapping findings into one dependency-ordered
repair batch, apply that batch once, and run deterministic validation after all
edits. Do not alternate between fixing one axis and respawning its reviewer. Run
one fresh five-axis clearance panel only after the revised snapshot is complete;
if it remains blocking, report the remainder instead of automatically starting a
third repair-review cycle.

After any content change:

Apply this verification sequence to a retained task heading for handover, not a
retired design. A confirmed redesign/retirement stop ends expensive probes and
packaging. For panel-only remediation, do not duplicate the single clearance
panel in step 8; additional fairness/difficulty runs require the applicable
handover scope or explicit request.

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
8. repeat the five-axis quality-panel review on the exact snapshot across
   `coherent_contract`, `correct_reference_solution`, `protected_ground_truth`,
   `sound_verifier`, and `deterministic_execution`; `Minor` and `Major` block
   on every axis except `protected_ground_truth`, where only `Major` blocks,
   `Advisory` findings do not block, and an undecided `Unsure` axis is not a
   confirmed defect but is also not cleared;
9. freeze the new snapshot and rerun fresh counted difficulty trials because
   old probe snapshots are stale;
10. update `difficulty` and the external submission prose from the newly measured
   facts, run the submission-only style audit, then regenerate and review the
   exact final ZIP and submission packet.

Report the newly measured tier honestly. For a new submission the platform also
requires at least 3 failures across its 8 runs, so no more than 5 may pass and a
re-measured result above 62.5% accuracy cannot proceed; `base` and a 75% `core`
outcome remain valid only for a task grandfathered on the platform by the
morning of Sep 11, 2026, including this revision of it. Never prune passing
cases or tighten a threshold to manufacture a qualifying number — repair the
underlying challenge. Under an explicit Advanced+ campaign, preserve lower-tier
evidence but do not count it toward the campaign quota.

## Revision report

Return a compact table with:

- platform flag or reviewer claim;
- raw evidence and affected tests/runs;
- root-cause class;
- docs-aligned decision;
- selected repair/narrow/remove/expand/retire option and why alternatives lose;
- prior failed strategies and the evidence-based stop/switch condition;
- retained core, removed obligations, necessary additions and recoverable snapshot;
- files changed;
- oracle/NOP and verifier results;
- V3 inferability verdict;
- fresh empirical tier signal;
- remaining uncertainty or platform-only validation need.
