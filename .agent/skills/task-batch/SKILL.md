---
name: task-batch
description: "Use when the user sends `task-batch N` or `/task-batch N`, where N is a positive integer, to autonomously create exactly N brand-new Terminus 3 tasks. Defaults to full campaign-ready; supports explicit panel-ready without fairness, auditor, or difficulty probes. Do not use for ports or returned-task remediation."
---

# Task Batch Router

Create exactly `N` fresh Terminus 3 tasks using one explicitly selected
execution profile. Treat `N` as the delivery count, not an attempt count.

## Select one profile before Stage A

Read [execution profiles](references/execution-profiles.md), record the selected
profile in the batch index and never mix receipts or result labels between
profiles.

- Default to `campaign_ready`. Read
  [the complete campaign workflow](references/campaign-ready.md) before acting.
- Select `panel_ready` only when the user explicitly omits ordinary
  fairness/auditor roles and difficulty probes. Read only this router,
  `references/execution-profiles.md`, the bounded-design reference and the
  quality-panel skill/resources needed by that path. Do not load the campaign
  workflow, quota hooks, fairness workflow, solve-probe, rubric or style skills.

User-specified category, language, attempt and time budgets override profile
defaults. Record an attempt when the user's definition says it begins. Keep one
active candidate at a time unless the user explicitly authorizes isolated
parallel candidates.

## Shared invariants

- Every task is genuinely new: no port, reskin, reused corpus or previously
  submitted topology presented as a new task.
- Choose exactly one current Title Case category and one valid matching
  subcategory by domain, not by the repair verb.
- Use one persistent builder for a candidate. Preserve its evidence when the
  candidate is rejected or requires rescope.
- Start from one primary outcome and a bounded connected causal core. Do not add
  functions, behaviors, corpus families, malformed-input domains, tests or
  exact-output conventions to satisfy a count or imply difficulty.
- Keep arbitrary public conventions explicit and agent-visible. Hidden cases
  may vary instances and interactions only under the same inferable model.
- Treat infrastructure/setup failures as infrastructure evidence, never task
  difficulty. Never claim a command, reviewer, result, model or hash that was
  not observed.
- Evidence is immutable and snapshot-bound. Any semantic task change
  invalidates dependent checks, packets and reviews.
- Harbor API-key-dependent agent runs are not required. Run the applicable
  local Docker and non-API checks selected by the profile.

## `panel_ready` route

Use `task-miner`, `task-clone`, `terminus-regular-task-authoring`,
`task-quality-panel-judgement`, deterministic `task-client-feedback-review`,
`task-harbor-runner`, and `task-zip-submit` only as their stages become
relevant. Read each selected skill completely before using it.

For each candidate:

1. Mine a fresh domain-native candidate and create the scope ledger required by
   [bounded task design](../terminus-regular-task-authoring/references/bounded-task-design.md).
2. Create `workspace/reports/<slug>/panel-precheck-manifest.json` and run the
   quality-panel `panel_precheck.py --design-only`. Reject or rescope a
   disconnected core, standalone subtask bundle or serialization-only join
   before scaffold expansion.
3. Build only the retained contract, supplied support plumbing, Oracle and
   obligation-driven verifier. Run deterministic structure, isolation and
   compatibility checks.
4. Run strict Docker Oracle=1, NOP=0 and noexec Oracle=1. Bind the verifier
   inventory and minimal natural wrong-path/harness-bypass receipts, then run
   `panel_precheck.py --full` on the exact snapshot. Do not spend reviewer
   sessions while it is red.
5. Run one eight-reviewer discovery panel: four isolated packets, two fresh
   independent reviewers per axis. Collect all eight complete responses before
   adjudicating or editing.
6. If discovery is already four-axis `None` with complete mandatory coverage,
   package the unchanged snapshot without duplicate clearance. Otherwise
   verify findings, remove speculation, deduplicate by root invariant and apply
   exactly one consolidated remediation batch. Rerun affected checks, strict
   Docker closure and full precheck.
7. Run exactly one fresh eight-reviewer clearance panel. If any axis remains
   blocking/`Unsure` or mandatory coverage is incomplete, stop that obligation
   set as `rescope_required`; do not run another repair/clearance under a renamed
   phase. Move to a new candidate only when the batch/user authority permits.
8. Package only the exact snapshot whose deterministic gates and four semantic
   axes passed. Count it as `local_panel_cleared`, never `candidate_ready` or a
   measured tier.

Minimal wrong-path closure is verifier-quality evidence, not a campaign mutant
suite or difficulty probe. `mechanically_ready` from the precheck is not a
quality-axis `None`; the semantic panel remains mandatory.

## Result labels and stopping

- `campaign_ready` follows `references/campaign-ready.md` and may reach
  `candidate_ready` only through its real handover gate.
- `panel_ready` stops at `local_panel_cleared`; difficulty is `not measured` and
  platform acceptance is not guaranteed.
- Stop when the profile-specific accepted count reaches `N`, the explicit
  attempt budget is exhausted, the user stops, or a concrete external blocker
  prevents all useful progress. Never count a rejected, merely packaged or
  deterministically green task as accepted.

Return task/ZIP paths and hashes, category/subcategory, deterministic results,
profile-specific review/probe evidence, accepted status, and concise rejected
candidate dispositions. Clearly distinguish unavailable checks and unmeasured
difficulty from verified results.
