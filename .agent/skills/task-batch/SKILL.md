---
name: task-batch
description: "Use when the user sends `task-batch N` or `/task-batch N`, where N is a positive integer, to autonomously create exactly N brand-new Terminus 3 tasks. Defaults to builder-certified: no quality panel, no fairness reviewer, no auditor, one reviewer plus a two-solver blind probe at a CORE+ bar. Supports explicit campaign-ready and panel-ready. Do not use for ports or returned-task remediation."
---

# Task Batch Router

Create exactly `N` fresh Terminus 3 tasks using one explicitly selected
execution profile. Treat `N` as the delivery count, not an attempt count.

## Select one profile before Stage A

Read [execution profiles](references/execution-profiles.md), record the selected
profile in the batch index and never mix receipts or result labels between
profiles.

- **Default to `builder_certified`.** A bare `task-batch N` selects it: no quality
  panel, no fairness reviewer, no auditor. Read this router,
  `references/execution-profiles.md`, `references/single-reviewer-workflow.md`,
  the bounded-design and contract-closure references, and
  `task-local-solve-probe`. Do not load the campaign workflow, quota hooks,
  fairness workflow or the quality-panel skill.
- Select `campaign_ready` only when the user explicitly asks for the full
  campaign, measured difficulty beyond CORE+, or `candidate_ready`. Read
  [the complete campaign workflow](references/campaign-ready.md) before acting.
- Select `panel_ready` only when the user explicitly asks to retain the quality
  panel while omitting fairness/auditor roles and difficulty probes. Read only
  this router, `references/execution-profiles.md`, the bounded-design reference
  and the quality-panel skill/resources needed by that path. Do not load the
  campaign workflow, quota hooks, fairness workflow, solve-probe, rubric or
  style skills.

The default carries its own design contract, so a bare `task-batch N` still
produces a task built to the seeded-departures pattern: the
[contract closure](../terminus-regular-task-authoring/references/contract-closure.md)
reference is mandatory reading on this route, not something the user has to ask
for in the prompt.

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
5. Run one ten-reviewer discovery panel: five isolated packets, two fresh
   independent reviewers per axis. Collect all ten complete responses before
   adjudicating or editing.
6. If discovery is already five-axis `None` with complete mandatory coverage,
   package the unchanged snapshot without duplicate clearance. Otherwise
   verify findings, remove speculation, deduplicate by root invariant and apply
   exactly one consolidated remediation batch. Rerun affected checks, strict
   Docker closure and full precheck.
7. Run exactly one fresh ten-reviewer clearance panel. If any axis remains
   blocking or mandatory coverage is incomplete, stop that obligation
   set as `rescope_required`; do not run another repair/clearance under a renamed
   phase. Move to a new candidate only when the batch/user authority permits.
8. Package only the exact snapshot whose deterministic gates and five semantic
   axes passed. Count it as `local_panel_cleared`, never `candidate_ready` or a
   measured tier.

Minimal wrong-path closure is verifier-quality evidence, not a campaign mutant
suite or difficulty probe. `mechanically_ready` from the precheck is not a
quality-axis `None`; the semantic panel remains mandatory.

## `builder_certified` route

Use `task-miner`, `task-clone`, `terminus-regular-task-authoring`,
`task-local-solve-probe`, deterministic `task-client-feedback-review`,
`task-harbor-runner` and `task-zip-submit` as their stages become relevant.

The five quality axes are carried by executable receipts, not by reviewers:

| Axis | What stands in for a reviewer |
|---|---|
| `coherent_contract` | closure clauses present and anchored; every exact convention cites a visible authority sentence; the blind solver's failures read for cause |
| `correct_reference_solution` | the expectation model is derived from the authority independently of the Oracle, so Oracle=1 is a non-circular agreement; `solve.sh` carries a contract header |
| `sound_verifier` | no orphan test and no witnessless obligation; a wrong-path receipt per core obligation; differential preservation for untouched behavior |
| `protected_ground_truth` | isolation run and recorded: unprivileged candidate, closed source tree, restricted `/tests` and `/logs/verifier`, and no reachable way for demoted code to regain privilege (`--no-new-privs` unless nothing setuid or capability-bearing exists) |
| `deterministic_execution` | repeat and shuffled runs agree; no network, no clock or ordering dependence |

Follow the numbered path in `references/execution-profiles.md`. Two rules govern
the whole route:

- **Receipts, not claims.** The builder reports only what a receipt file bound to
  the snapshot hash shows. A gate with no receipt did not run, and saying it
  passed is a fabrication.
- **A disputed gate is recorded, never worked around.** With no panel above the
  scripts, silently editing the task to satisfy a rule the builder believes is
  wrong turns a correct task into a broken one. Write a `documented_exception`.

## Result labels and stopping

- `campaign_ready` follows `references/campaign-ready.md` and may reach
  `candidate_ready` only through its real handover gate.
- The difficulty bar on the default route is CORE+: at most one of the two blind
  solvers succeeds. Do not keep hardening a task that already clears it in order
  to reach `advanced` or `frontier`, and do not reject one that lands at CORE.
- `panel_ready` stops at `local_panel_cleared`; difficulty is `not measured` and
  platform acceptance is not guaranteed.
- `builder_certified` stops at `builder_certified`. Report it with the reviewer
  and probe evidence actually collected, and state plainly that no quality panel
  ran. Never upgrade it to `local_panel_cleared`.
- Stop when the profile-specific accepted count reaches `N`, the explicit
  attempt budget is exhausted, the user stops, or a concrete external blocker
  prevents all useful progress. Never count a rejected, merely packaged or
  deterministically green task as accepted.

Return task/ZIP paths and hashes, category/subcategory, deterministic results,
profile-specific review/probe evidence, accepted status, and concise rejected
candidate dispositions. Clearly distinguish unavailable checks and unmeasured
difficulty from verified results.
