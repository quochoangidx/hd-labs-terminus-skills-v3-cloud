---
name: task-clone
description: "Use when transforming a mined candidate into a Terminus 3 task under workspace/tasks/tbrain-* folders. Consumes mined_candidate artifacts when available, avoids re-mining GitHub, applies prompt sanitization, repo slimming, isolated behavioral verifier design, oracle creation, and Harbor validation. All seven Terminus 3 categories are open; category and subcategory must match the task's domain."
---

# Task Clone

Before freezing a built task, read
[panel input hygiene](../terminus-regular-task-authoring/references/panel-input-hygiene.md).
Assess large task files and aggregate review input, using 800 lines only as a
soft warning; preserve necessary source, evidence, and verifier discrimination.

Use this skill when the user wants to turn a mined candidate into a Terminus 3 task. Candidates may be upstream bugfixes or explicit category-profile tasks. Preserve the artifact's category and subcategory unless either is invalid or the task's domain clearly belongs elsewhere.

> **Terminus 3 operational baseline (2026-07-31).** Every task uses one of the
> seven Title Case category families plus exactly one taxonomy subcategory,
> difficulty `frontier|advanced|core|base`, top-level `artifacts`, an isolated
> verifier built from `tests/Dockerfile`, `network_mode` instead of
> `allow_internet`, and an agent timeout between 1800 and 18000 seconds.
> Milestones, `codebase_size`, the old `subcategories` list, and the Python-must-
> be-hard rule are gone. Historical Terminus 2 evidence later in this file may
> still describe old labels; it is calibration evidence, not current metadata.

Preferred split:

```text
mine = candidate discovery + scoring only
clone = transformation + packaging only
```

If a mined candidate artifact exists, consume it and do not repeat the mining pass unless required fields are missing.

## Core Rule

Task folder names must be:

```text
tbrain-<problem-slug>
```

Task folders must be created under the workspace directory:

```text
workspace/tasks/tbrain-<problem-slug>/
```

Do not include repo/tool/domain filler in the slug. Prefer the behavior or bug:

- Good: `tbrain-maxfail-teardown-reporting`
- Good: `tbrain-timezone-cutoff-reconciliation`
- Good: `tbrain-async-cancel-cleanup`
- Bad: `tbrain-pytest-maxfail-teardown-reporting`
- Bad: `tbrain-django-async-cancel-cleanup`

Exception: keep a domain word only when it is part of the actual problem concept, not just the source repo name.

Name-shape dedupe (mandatory, RELATIVE — no fixed banned-word list): name the
task after the domain problem a real team's ticket would describe, never after
the lever/mechanism it was built from. The check is against the CURRENT
portfolio, not a word list: before creating the folder, grep
`mined-candidates/index.jsonl` and the gallery snapshot for the slug's final
noun and overall shape; if a similar name already appears ≥2 times, pick a
different name (and, for synthetic tasks, a different domain skin). Identical
suffixes signal near-duplicate tasks to reviewers even when the logic differs —
the 2026-07 portfolio accumulated eight `tbrain-*-ledger` tasks this way, but
the over-used word will drift over time; trust the grep, not any remembered
list. Varying the name grammar across a batch helps too.

## Inputs

Accept any of:

- a `mined_candidate.json` or equivalent compact artifact
- a GitHub issue URL
- a GitHub PR URL
- `owner/repo` plus a requested domain
- a rough task idea plus a source repo

If a source URL is given without a mined artifact, browse or use `gh` only enough to verify it is closed/merged and identify the fixing PR/commit. Do not perform broad mining inside clone.

## Mined Artifact Contract

When available, clone should start from:

```yaml
candidate:
  category:
  subcategory:             # exact Terminus 3 taxonomy value
  target_difficulty:       # frontier | advanced | core | base
  artifacts:               # final paths the isolated verifier receives
  closest_gallery_task:
  gallery_novelty:         # novel | twist-on-existing | duplicate — Terminus 3 submissions require novel; reject twist-on-existing and duplicate
  subtype_profile:         # per-subtype details (tool/mock_plan/db_engine/…) when a subtype is set
  objective_type:
  design_pattern:
    track:                 # established | derived
    pattern_ids:           # established P* IDs directly applied
    parent_pattern_ids:    # derived only
    derived_pattern_id:    # derived only, candidate-local X-* ID
    transformation_operators:
    causal_graph:
    causal_topology_delta:
    work_surface_delta:
    verifier_delta:
    failure_geometry_delta:
    non_equivalence_rationale:
    closest_portfolio_pattern_instance:
  source_url:
  issue_or_pr_id:
  repo:
  base_commit:
  parent_commit:
  fixing_commit:
  task_slug:
  bug_signature:
  touched_files:
  subsystem_tags:
  runtime_class:
  external_requirements:
  repro_summary:
  current_pipeline_summary:
  target_behavior:
  required_work:
  input_fixtures:
  output_contract:
  bad_behavior:
  expected_behavior:
  preserved_behavior:
  edge_cases:
  difficulty_rationale:
  reasoning_bottlenecks:
  tempting_partial_fixes:
  semantic_mechanisms:
  semantic_interactions:
  public_surfaces:
  verifier_architecture:  # must pass the mining plan gate before scaffolding
    schema_version: 1
    status: pass
    profile:              # cheap_deterministic | expensive_stateful
    planned_platform_visible_unit_count:
    semantic_clusters:
    public_surface_ids:
    public_surface_cluster_ids:
    cross_cluster_scenarios:
    verifier_shapes:
    platform_visibility_strategy:
    nop_discrimination_strategy:
  domain_rationale:
  test_surface:
    primary_api:
    secondary_apis:
    constructor_contracts:
    offline_fixtures:
    skip_guard_policy:
  scoring:
    subsystem_interaction:
    deterministic_reproducibility:
    offline_viability:
    anti_shortcut_hardness:
    verifier_complexity:
    runtime_cost:
    leakage_risk:
  patch_shape_gate:        # pass | fail — fail means no credible high-tier signal
  patch_shape_evidence:
  v3_shape_screen:         # pass | fail — clear goal, inferable model, interacting axes, semantic deliverable
  conformance_collapse_screen: # pass | fail | not_applicable
  family_key:              # library + bug_family, for the family ledger
  agent_probe:             # {ran, passed_oneshot} — blind-probe evidence backing the difficulty claim
```

If this exists, inspect only touched files, focused upstream tests, and support files needed to stage/build/run the task. Do not rescan large repo history or re-open unrelated issues.

Before scaffolding, validate `design_pattern` against
`.agent/skills/task-miner/frontier_task_design_patterns.md`. Preserve its track
through cloning: do not silently convert a rejected derived slot into an
established slot or relabel an established task as derived. A derived candidate
must materially change at least two of causal topology, work surface, verifier
architecture, and expected failure geometry; a repository, language, artifact
format, or narrative change alone returns to mining as a reskin.

If the artifact is missing `test_surface` details for a secondary implementation
that tests will cover, fill that gap before writing verifier tests. Do not guess
constructor signatures from class names. Before scaffolding, require the
`verifier_architecture` plan and pass:

```bash
python3 .agent/skills/terminus-regular-task-authoring/scripts/verifier_architecture_check.py \
  plan <mined-candidate.json>
```

A failed breadth plan returns to mining. Do not create a task folder and hope
the final handover will catch it.

For domain-profile artifacts, treat `category`, `subcategory`, `target_behavior`,
`required_work`, `input_fixtures`, and `output_contract` as the source of truth.
Do not rewrite the task as a bugfix just because the source has issues or PRs.

## Dedupe Registry

Before cloning, check:

```text
mined-candidates/index.jsonl
```

If a shared team registry exists, check it too. Treat any matching `repo + fixing_commit`, `repo + issue_or_pr_id`, `repo + bug_signature`, `category + source + task_slug`, or `repo + base_commit + target_behavior` with status `claimed`, `cloned`, or `submitted` as already taken unless the user explicitly wants a variant.

During clone, update or append a compact JSON line:

```json
{"category":"Software","subcategory":"Languages","repo":"pytest-dev/pytest","issue_or_pr_id":"14465","source_url":"...","fixing_commit":"...","parent_commit":"...","bug_signature":"maxfail session fixture teardown reporting","task_slug":"tbrain-maxfail-teardown-reporting","status":"cloned","rejection_reason":null}
```

Use `bug_signature` for near-duplicate detection when issue and PR URLs differ but the fix is the same behavior.

## Candidate Selection

For upstream bugfix candidates, prefer:

- a real bug, not docs-only text
- a fix that changed tests upstream
- 50-500 meaningful LOC, or a smaller fix involving subtle cross-module behavior
- deterministic local reproduction
- no live credentials, no external service, no network needed at runtime
- at least two interacting subsystems

For category-profile candidates, prefer:

- a clear category-primary activity, not a cosmetic label
- a target behavior that can be stated without source issue/PR leakage
- deterministic offline verifier inputs and outputs
- enough existing code/config/data for real discovery work
- at least four focused verifier assertions covering variants and preservation

Reject all candidates that are:

- docs-only, typo-only, dependency bump, CI-only, release metadata
- single-line validation or obvious message change
- tiny one-file patches where the likely solution is one branch or one flag check
- tasks whose verifier cases are mostly variants of the same condition
- too broad to isolate into one task
- impossible to test offline in Docker
- likely to pass current frontier agents in one shot

Difficulty is language-independent. Keep a candidate only when it is non-trivial
and likely to produce at least three failures in the eight-run measurement; do not
force Python into a special tier.

## Difficulty Design

Decide difficulty here, before scaffolding. Difficulty checked only at
packaging is difficulty you cannot change without rebuilding the task.

Two quantities move independently:

```text
difficulty    ∝ coupling between obligations
panel risk    ∝ count of obligations
```

Each retained obligation creates five proof duties, one per panel axis:
contract wording, Oracle branch, ground-truth surface, discriminating witness,
and determinism. Count raises all five at once; coupling raises none of them.
So a task gets harder by tightening the causal graph over the obligations it
already has, never by adding obligations. `bounded-task-design.md` governs what
enters the core; this section governs how much the core must interact.

### Coupling is the lever

An obligation set is coupled when a plausible repair of one obligation changes
the correct behavior of another before serialization. Record the causal graph
in the scope ledger and require, for the causal core:

- at least one genuine result-changing interaction, per the semantic-coverage
  gate; for an Advanced+ claim, prefer a core where most obligation pairs
  interact rather than one interacting pair bolted onto independent work;
- at least two natural-but-wrong repairs that fail on **disjoint** witness sets;
- each plausible wrong repair cheaper than the correct one. A trap as expensive
  as the real fix catches nobody and contributes no failures to the 8-run gate.

Counts stay diagnostics. `bounded-task-design.md` is explicit that no number of
mechanisms, interactions, or traps proves a tier, and a naturally thin candidate
is redesigned or rejected rather than padded to reach a number. Use the observed
portfolio only to notice an outlier worth re-reading, not as a target:
`tbrain-c1-security` froze at six mechanisms, four interactions, ten mutants.

### Three axes of difficulty

Classify the candidate's difficulty source before choosing a pattern:

```text
A  inference depth      the contract must be reconstructed from distributed evidence
B  coupling degree      several obligations must hold simultaneously
C  verification reach   hidden checks probe understanding, not example-matching
```

Roughly, `P3`/`P5` supply A, `P1`/`P2`/`P8` supply B, and `P4`/`P6`/`P7` supply
C. A task strong only in A tends to produce `near_miss`: the agent models the
domain correctly and slips on isolated cases. A task strong only in B without
inference is length, which `difficulty-guidelines.md` rejects. Aim for A and B
together with enough C to discriminate; all three maximal usually fails
`coherent_contract` because the contract outgrows what the instruction can
state.

### Difficulty operators

These are transformations applied within a pattern, not patterns themselves. A
pattern fixes the causal topology; an operator raises the cost of solving it.
Recording an operator never substitutes for the pattern-blind crux.

- **Defensive documentation.** Comments, docstrings, or design notes justify the
  incorrect behavior in plausible domain language. Legitimate only when
  agent-visible evidence — data, runtime behavior, an in-repo test — refutes the
  prose without outside knowledge. If the prose is the only authority, this is
  unstated-requirement ambiguity and the task is broken.
- **Symptom-cause displacement with a cheap decoy.** The most reproducible
  symptom has a local repair that is genuinely cheaper than the correct one and
  fails only on interaction witnesses. This is the concrete form `P1` assumes;
  state which decoy and which witnesses separate it.
- **Cross-representation disagreement.** Two visible representations of the same
  fact disagree — schema against migration, documentation against
  implementation, configuration against live state — and precedence is inferable
  from evidence. A static, cheaper relative of
  `X-dynamic-authority-reconciliation`, which needs an event schedule.
- **Verifier-aware adversarial pass.** See Workflow step 15.

### Size budgets

Instruction length is not a difficulty lever. Research on terminal-agent
benchmark design finds the strongest tasks fit roughly two paragraphs and assume
an experienced engineer; long instructions usually describe procedure, which
hands over the solution, or output format, which measures compliance rather than
capability and surfaces later as a `task_specification` flag.

Advisory, from the frozen portfolio — a breach is a prompt to re-read, not a
failure:

| Surface | Observed range | Read again when |
| --- | --- | --- |
| `instruction.md` | 3–27 lines | over ~60 lines |
| `solution/` implementation | ~490–1400 LOC | the Oracle cannot cover every branch |
| `tests/test_outputs.py` | ~70–280 lines | logic grows past a corpus driver |
| graded corpus cases | 28–219 | cases outnumber distinguishable rules |

Corpus size is not semantic rank: a large matrix over one branch remains one
mechanism. The verifier body stays small because cases live in
`tests/corpus.json` and are generated through `_make_case`; grading logic that
grows instead of the corpus usually signals obligations that never coupled.

### Design sheet

Write this before scaffolding; materialize it as
`workspace/reports/<slug>/difficulty-design.json` at Workflow step 7 alongside
the scope ledger.

```yaml
crux:        # one sentence, no catalog vocabulary (P*, X*, coupled-invariant)
evidence:    # visible sources from which the crux is inferable
deliverable: # the artifact and its consumers
coupling:    # edges: obligation -> obligation, and what changes
traps:       # >=2 cheap wrong repairs, each with its disjoint witness IDs
cheats:      # shortest paths to reward without the work, and the block for each
axes:        # {inference: low|med|high, coupling: ..., verification: ...}
operators:   # applied difficulty operators, if any
```

If the crux cannot be stated without catalog vocabulary, the candidate is a
reskin: return it to mining. This is the pattern-blind crux gate in
`frontier_task_design_patterns.md`, in the form used during cloning.

### Every difficulty decision carries a receipt

Each lever threatens one axis and is cleared by one existing artifact. No new
receipts are introduced here; the change is that they are owed at design time
rather than discovered at packaging.

| Lever | Axis at risk | Receipt |
| --- | --- | --- |
| Contract inferred from evidence | `coherent_contract` | `instruction-sufficiency.json` maps every static test to a contract row or inference family |
| Coupled obligations | `sound_verifier` | one killed mutant per mechanism and interaction in `semantic-coverage.json` |
| Defensive documentation | `coherent_contract` | the refuting visible evidence, cited in the sufficiency manifest |
| Hidden variation | `coherent_contract` | variation changes values, sequences, layouts, or combinations only — never policy |
| Hardened anti-cheat | `correct_reference_solution` | Oracle rerun after each tightening |
| Graded secondary observable | `deterministic_execution` | derived from artifact or runtime state, never wall-clock |

## Workflow

1. Load the mined artifact or verify the source URL with the smallest needed browse/`gh` pass.
2. Read `task-miner/frontier_task_design_patterns.md`, validate the candidate's
   established/derived track and causal-graph evidence, then gate the domain
   before scaffolding with `task-miner/category_rules.md`.
   Record exactly one Title Case category/subcategory pair and explain which
   domain evidence makes it necessary. Do not classify by verbs such as
   implement, parse, or repair: a training-loop repair is `ML / Training`, while
   a compiler repair is `Software / Languages`.
   In the same gate, check the TEMPLATE shape: the CI `template_detection` check
   (first observed 2026-07-13) blocks submissions matching a named template —
   confirmed `rust_cli` = minimal single-source-file stub project, stdin→stdout
   batch binary, "extend the starter" instruction, and hidden vector-corpus verifier;
   assume per-language siblings. Scaffold away from
   that shape from the start (realistic multi-module repo, in-repo tests,
   domain-authentic file I/O); if flagged anyway, mark
   `template_detection_<template_name>` and see AGENTS.md §9 for current
   (UNVERIFIED) remediation levers.
3. Choose the parent commit before the fix for upstream bugfixes, or the artifact's `base_commit` for category-profile tasks.
4. Create `workspace/tasks/tbrain-<problem-slug>` by running
   `scripts/new-task.sh <slug> <lang> <category> <subcategory>`. Do not hand-write
   `task.toml`, `.dockerignore`, or `tests/test.sh`; custom generators must call
   the scaffolder first and then edit task-specific surfaces only.
5. Stage the repo or focused subset under `environment/repo`, not by runtime network fetch.
6. Slim the repo to task-relevant modules, support utilities, fixtures, and minimal build config.
7. Write sanitized `instruction.md` from observable behavior only, then run the real-user prompt test before building the verifier.
   First apply
   [bounded task design](../terminus-regular-task-authoring/references/bounded-task-design.md):
   classify every planned obligation as core, supplied support, or non-goal.
   In the same pass, complete the `## Difficulty Design` sheet and write
   `workspace/reports/<slug>/difficulty-design.json` beside the scope ledger.
   State the crux without catalog vocabulary, record the coupling edges, and
   name at least two cheap wrong repairs with disjoint witness sets. Return an
   uncoupled or decoy-free core to mining rather than scaffolding it.
   Do not expose generic parser/schema/serialization hardening as solver work
   unless it is the task's primary domain outcome.
   For a `panel_ready` build, materialize this ledger as the quality-panel
   precheck manifest and pass `panel_precheck.py --design-only` before expanding
   the scaffold. Do not proceed when core obligations are disconnected,
   separable standalone deliverables, or joined only by output serialization.
8. Write Terminus 3 `task.toml` with top-level `artifacts`, one exact category/subcategory pair, descriptive fields under `[metadata]`, `environment_mode = "separate"`, explicit per-phase `network_mode`, and realistic resources/timeouts.
9. Write `environment/Dockerfile` with digest-pinned `FROM`, `tmux`, `asciinema`, `bash`, useful search/edit tools, and required pinned deps.
10. Write `tests/Dockerfile`, behavioral `tests/test_outputs.py`, and offline
    `tests/test.sh`; ensure every declared artifact has a landing directory in
    the verifier image.
11. Collect the actual platform-visible test IDs, create
    `workspace/reports/<slug>/verifier-matrix.json`, and run the verifier
    architecture integrity gate with `--allow-missing-ctrf`. Counts are
    diagnostics. Stop when a promised surface lacks a discriminating witness or
    the task reaches apparent depth only through unrelated breadth; do not write
    the Oracle, build Docker images, or run probes until the scope is coherent.
12. Write `solution/fix.patch` and `solution/solve.sh` that apply a generalized
    fix and rebuild if needed.
13. Validate the exact Docker baseline: NOP fails for the intended reason only;
    Oracle passes all verifier tests, including under noexec `/tmp`. Bind the
    Oracle CTRF to `verifier-matrix.json` and rerun the gate without
    `--allow-missing-ctrf`; its IDs must exactly match the declared behavior and
    non-behavior units.
14. Complete V3 evidence inferability, public-surface coverage, the semantic
    mechanism/interaction map, and executable partial-fix mutation evidence.
15. Run the verifier-aware adversarial pass before freezing. Assume the
    candidate can read the verifier source, then walk the exploit-class table in
    `## Verifier Pattern` and try to reach reward without doing the work. Patch
    each reachable class and **rerun the Oracle after every tightening**: a patch
    that also rejects the reference solution is over-restrictive and must be
    replaced, not kept. Record the classes checked, exploits found, patches, and
    post-patch Oracle results in
    `workspace/reports/<slug>/adversarial-pass.json`. This is a bounded single
    pass, not an open-ended hardening loop.
16. Run the folder-level client/manual review and task-visible style audit;
    clear findings, then freeze the full task/verifier snapshot.
17. Run counted real-agent trials. Package only after the difficulty gate;
    then write and separately style-audit reviewer-facing Difficulty, Solution,
    and Verification explanations outside the task folder.

> Terminus 3 explicitly values domain inference, live state, native artifacts,
> and interacting constraints. The archetypes in
> `.agent/skills/task-miner/interaction_shape_recipe.md` are open candidate
> shapes again, but their old Terminus 2 results remain negative priors for the
> exact canonical restoration/migration recipes that collapsed. Use fresh
> evidence and varied domain structure. An exploratory skeleton probe may reject
> an idea cheaply but cannot qualify difficulty; do not assume either
> Frontier or Base from the archetype name.

The current preferred shapes and adaptive established/derived candidate policy
live in `.agent/skills/task-miner/frontier_task_design_patterns.md`. Pattern
membership is a design receipt, not a difficulty claim. The completed verifier
must still prove every candidate-specific mechanism and interaction with
dedicated mutants and frozen probes.

## Regular Layout

```text
workspace/tasks/tbrain-<problem-slug>/
├── instruction.md
├── task.toml
├── environment/
│   ├── .dockerignore
│   ├── Dockerfile
│   └── repo/
├── solution/
│   ├── solve.sh
│   └── fix.patch
├── tests/
│   ├── Dockerfile
│   ├── test.sh
│   └── test_outputs.py
└── reports/                    # optional local notes; exclude from ZIP
    └── mining_notes.md
```

For a small app task, `environment/app/` is acceptable, but cloned upstream bug tasks should normally use `environment/repo/`.

Prefer external notes under `workspace/reports/<task-slug>/` when possible so submission zips do not accidentally include them.

For the current platform submission form, create:

```text
workspace/reports/<task-slug>/submission-explanations-source.md   (factual source notes)
workspace/submissions/SUBMISSION-<task-slug>.md                   (the UI-ready platform packet — single canonical name)
```

Packet contents and format: the "platform packet" section near the end of
this skill. Never place either file under the submitted task root or ZIP.

## Metadata Defaults

Use the artifact's Terminus 3 category/subcategory pair when valid. Choose by
the domain knowledge needed to solve the task, not by the mere presence of code.
For example, repairing a training loop is `ML / Training`; reserve `Software`
for tasks whose subject is software engineering itself.

```toml
artifacts = ["/app/output.json"]
name = "<task-slug>"

[metadata]
author_name = "anonymous"
author_email = "anonymous"
difficulty = "<frontier|advanced|core|base>"
category = "<exact Title Case category>"
subcategory = "<exact matching Title Case subcategory>"
languages = ["<main implementation language>"]
tags = ["<3-6 useful tags>"]
expert_time_estimate_hours = 6
difficulty_explanation = "<why this is inherently a challenge for a human expert>"
solution_explanation = "<oracle approach>"
verification_explanation = "<behavior and artifact checks>"
relevant_experience = "<author background>"

[verifier]
timeout_sec = 1800
environment_mode = "separate"
network_mode = "no-network"

[agent]
timeout_sec = 5400      # minimum 1800, ceiling 18000
network_mode = "no-network"

[environment]
network_mode = "public" # required on every task; build/harness phase stays public
build_timeout_sec = 1800
cpus = 2
memory_mb = 8192
storage_mb = 10240
```

Valid taxonomy pairs are:

```text
Science: Biology, Chemistry, Physics, Earth, Robotics, Math, Linguistics
Software: Algorithms, Systems, Databases, Data engineering, Frontend, Languages
ML: Training, Inference, Evaluation, Kernels
Operations: Finance, Logistics, Supply chain, Claims, Compliance, Marketing
Security: Cryptography, Reverse engineering, Forensics, AppSec
Hardware: CAD, RTL
Media: Music, Design
```

`artifacts` is top-level. Declare only final paths needed for grading; the
isolated verifier cannot browse the rest of the agent filesystem. Create every
artifact parent directory in `tests/Dockerfile` before Harbor uploads files.

`languages` should list the main language(s) the agent works in or the oracle
solution changes. Do not include Python solely because the verifier is written
in pytest. Use LOWERCASE slugs: `["rust"]`, `["go"]`, `["c"]`, `["typescript"]`
— NOT `["Rust"]`/`["Go"]` (reviewers return capitalized values; the docs examples
are all lowercase).

Do not carry removed Terminus 2 keys into the manifest: `version = "2.0"`,
`number_of_milestones`, `codebase_size`, `subcategories`, `allow_internet`,
`expert_time_estimate_min`, and `junior_time_estimate_min` are obsolete.

## Rubric quality (rubric is entered in the UI, NOT in the ZIP — see task-zip-submit)
Rubrics grade trace-evidenced engineering behavior, not the final pytest result.
Do not add generic meta-criteria for reading instructions or routine commands
that say nothing task-specific. Keep diagnostic, binary criteria tied to the
actual domain workflow, include at least one negative criterion, use only
±1/2/3/5 with signed positives, and keep the positive total between 10 and 40.

## Contract Closure

Read
[contract closure](../terminus-regular-task-authoring/references/contract-closure.md)
before writing `instruction.md`. It carries the rules that let a task answer the
five quality axes on receipts rather than reviewer opinion, and every one of them
is checked by `panel_precheck.py`:

- one authority, plus a universal-rule clause and a silence clause that close the
  rest of the input domain (an entry-point scope clause too, when tests drive
  helpers directly);
- a coverage-envelope paragraph naming the hidden input families and no values;
- an authority sentence behind every exact convention the verifier pins;
- restrictions listed with their legal exceptions, each backed by a mechanical
  audit;
- expectations derived from the authority independently of the Oracle, written
  before the Oracle exists;
- a differential guarding whatever the silence clause promised to leave alone.

An instruction that carries this much contract will run past the advisory word
and backtick counts in `instruction_preflight.py`. That is expected. Trim
narration, never contract.

## Instruction Style

After writing or editing `instruction.md`, run the mechanical pre-flight and
fix every finding (structure, length, hint phrases, leakage) before the first
platform check:

```bash
scripts/python3 .agent/skills/terminus-regular-task-authoring/scripts/instruction_preflight.py <task-folder>
```

Write like a real engineer describing the requested observable work:

- Prefer 1-3 short FLOWING paragraphs, but treat that as guidance rather than a
  hard cap — never a spec sheet. Do NOT use `## Input` /
  `## Output` / `## Build` (or any similar) section headers, format tables, or
  bulleted "rules" lists. The platform `instruction_check` reviewer flags a
  section-structured instruction as a "design document that prescribes
  implementation" and warns even after the rule enumeration is removed (confirmed
  twice, 2026-06-21: rule-free-but-sectioned still warned; the prose rewrite
  cleared it). Weave the stdin/stdout format, constraints, and the build note
  into narrative sentences that explain *why* each part matters. A longer
  instruction is acceptable when the contract genuinely needs the space and
  does not leak implementation steps. When the
  behaviour follows a known standard or tool, reference it ("the result must
  match `git check-ignore`") instead of restating its rules.
- Before the first platform check, run the `instruction_check` binary preflight
  in `terminus-regular-task-authoring` (Prompt Rules). The escape hatches for a
  flip-flopping verdict, test-pinned literals, and custom output formats live in
  `.agent/skills/task-miner/lever_patterns.md` (L1 step 9): ship the non-blocking
  ⚠️ when the flagged items are test-pinned, use natural JSON + a semantic
  verifier instead of a bespoke byte format, and move unavoidable disclosures
  into an in-env reference file with a one-line pointer. Treat paragraph and
  bullet-count findings as style guidance, not standalone rejection reasons.
- Absolute paths only, such as `/app` and `/app/src/module.py`.
- State observable contract and exact user-facing strings only if tests assert them.
- No issue URLs, PR numbers, test names, rubrics, or solution hints.
- No step-by-step implementation guide.
- No task name in the prompt.
- No canary strings.
- Apply the real-user prompt test to every sentence: would a developer who did
  not already know the solution naturally include this detail? If the detail is
  useful mainly because it points to the fix path, remove it or restate it as an
  observable requirement.
- If tests require a secondary implementation that is not obvious from the
  public behavior, name the relevant module or file path without giving the
  exact patch. This clarifies public scope without disclosing the inferred
  model or solution.

**Do not narrate the internal mechanism or root cause (the #1 client reject,
June 2026 trial feedback).** The most common rejection is a prompt that "gives
away the solution": it explains how the code is wrong internally, or which code
path is already correct, so the agent only has to read the prompt rather than
reason about the code. Describe the OBSERVABLE symptom a real user would hit and
the DESIRED outcome; let the agent find the cause and the fix.

- Cut "Right now the parser does X internally" sentences. State the observable
  instead: not "the parser ignores the algorithm name and trusts the embedded
  curve" but "a key labeled `nistp384` that actually carries a `nistp256` curve
  is accepted."
- Cut "the other path already handles it" tells (e.g. "the ordinary callback
  enforces this but the new one does not"). They point the agent at where to
  copy the fix from. State only that the behavior is missing where the user
  observes it.
- Cut fix-shaped requirements that restate the implementation (e.g. "reject a
  line whose host field begins with `@`"). State the requirement behaviorally
  ("reject a line with more than one marker or an unknown marker").
- Litmus test: if a sentence would be strange for a user who did NOT know the
  fix to write, it is a hint. If removing a sentence makes the task unsolvable,
  it was probably a hint, not a requirement.
- KEEP test-asserted contracts that are genuine spec, even when specific:
  thresholds (`> 8192 bits`, `2048` rounds, `160`-bit), the public API the tests
  drive, named exempt contexts, and every preservation/edge case a test checks.
  These satisfy instruction/test symmetry. The goal is to remove root-cause and
  implementation narration, not the behavioral contract.

Prompt sanitizer must remove:

- issue URLs, PR numbers, commit hashes
- upstream test names and fixture names copied from the PR
- internal helper/function names unless they are public API
- implementation guidance such as "change `nextitem`" or "edit `runtestprotocol`"
- benchmark meta language such as verifier, oracle, hidden tests, rubric, or CI

Environment files must not smuggle the solution:

- README, config, scripts, comments, TODOs, and source files must not contain
  step-by-step walkthroughs, procedural hints, or commented solution plans.
- `spec.md`, README, and architecture docs may define schemas, protocols, API
  contracts, or business rules, but they must describe what is required, not
  how to implement the fix.
- Do not split the task's prompt/goals out of `instruction.md` into
  environment docs to satisfy length limits. Supporting docs should look like
  realistic engineering artifacts, not LLM-style prompt extensions.

Good bugfix shape:

```md
The package in `/app` mishandles <scenario>. A user who <does normal workflow> currently sees <bad observable behavior>.

Fix it so `<public command or API>` <observable result>. The run should still <preserve important behavior>, and <edge case contract>.
```

Good domain-profile shape:

```md
The tool in `/app` needs to produce <target artifact or behavior> from <input surface>. Implement support for <public command/API/workflow> so it follows <observable contract>.

The output must <format/schema/order/tolerance requirements>. Preserve <existing mode or compatibility behavior> for <normal workflow>.
```

## Docker Rules

`environment/Dockerfile` must:

- use `FROM ...@sha256:<digest>` on every stage
- keep every Dockerfile cloud-builder compatible: `COPY --chown=` uses numeric
  IDs (for example `0:0` or `1000:1000`), and an external-image
  `COPY --from=` uses `image@sha256:<digest>` with no tag. `FROM
  image:tag@sha256:<digest>` and `COPY --from=<stage-name>` remain valid.
- use a **canonical Terminal-Bench base image** for the final runtime stage when
  one matches the task's language (exact digest-pinned refs):
  - Python: `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb`
  - Node: `public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383`
  - Go: `public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac`
  - Rust: `public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36`
  - Java (JDK): `public.ecr.aws/docker/library/eclipse-temurin:21-jdk-jammy@sha256:25d1276565738d3c805e632a4542c3a7598866ef967f4def6544c15de3a74b14`
  - C/C++ (GCC): `public.ecr.aws/docker/library/gcc:13-bookworm@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c`
  - Ruby: `public.ecr.aws/docker/library/ruby:3.3-slim-bookworm@sha256:e76733e94b3a5893e4a141024ef3a583dc10781dc24becebf74f9c9f9a33e3df`
  - Maven: `public.ecr.aws/docker/library/maven:3.9.9-eclipse-temurin-21@sha256:3a4ab3276a087bf276f79cae96b1af04f53731bec53fb2e651aca79e4b10211e`
  - Debian: `public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d`
  - Ubuntu: `public.ecr.aws/docker/library/ubuntu:24.04@sha256:0d39fcc8335d6d74d5502f6df2d30119ff4790ebbb60b364818d5112d9e3e932`

  A non-canonical base is allowed ONLY with a brief, credible justification (as a
  `Dockerfile` comment or in the task `README.md`) — e.g. a runtime the list
  doesn't cover. Missing/vague/boilerplate justification, or one that matches an
  existing canonical entry, is **blocked** by `check_sanctioned_base_images`.
- **languages without a canonical base = canonical Debian/Ubuntu base + a pinned
  apt toolchain, NOT a third-party language image.** Lua, PHP, Perl, OCaml,
  Haskell (ghc), Erlang/Elixir, Common Lisp (sbcl), SWI-Prolog, R and similar all
  install offline from apt in the same clean transaction as `tmux`/`asciinema`,
  which keeps `check_sanctioned_base_images` green with no justification needed;
  Fortran rides the canonical gcc image (gfortran included). The login-shell
  PATH, warm-build, and cache-retention rules below still apply — sanity-check
  with `bash -lc 'which <tool>'`. Do NOT introduce pre-1.0 / fast-churn
  toolchains (Zig, Nim, Crystal, V): frontier agents emit version-skewed code
  there, yielding timeout/0/N tooling failures instead of difficulty. New
  languages beyond the apt lane are added lazily per the expansion policy in
  `lever_patterns.md` ("Widen the language axis").
- install `tmux`, `asciinema`, `bash`, and usually `util-linux`
- include practical agent tools such as `git`, `ripgrep`, and `sed`/`coreutils` when the base image lacks them
- **expose the language toolchain on `/usr/local/bin`.** The agent runs in a LOGIN
  shell that resets PATH to `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`
  and drops any Docker `ENV PATH` additions. The Go image keeps `go`/`gofmt` in
  `/usr/local/go/bin` and the Rust image keeps `cargo`/`rustc` in `/usr/local/cargo/bin`,
  neither of which is on that login PATH, so the agent cannot invoke the compiler
  even though oracle/nop can (they run in a non-login shell with PATH intact).
  Symlink them: Go `RUN ln -sf /usr/local/go/bin/go /usr/local/bin/go && ln -sf /usr/local/go/bin/gofmt /usr/local/bin/gofmt`;
  Rust `ln -sf /usr/local/cargo/bin/cargo /usr/local/bin/cargo && ln -sf /usr/local/cargo/bin/rustc /usr/local/bin/rustc`;
  Java `ln -sf "${JAVA_HOME}/bin/javac" /usr/local/bin/javac` (+ `java`).
  `node`/`gcc` images already place tools in `/usr/local/bin`.
  Confirmed 2026-07-01: a Go task omitted this and ~3/10 agent trials failed with
  "no Go toolchain, unable to compile", scoring 0 for a pure environment reason
  while oracle stayed green. Verify with
  `docker run --rm --entrypoint bash <img> -lc 'command -v go'`.
- **initialize a git repo in the task workdir** (after the final source `COPY`)
  so the agent's edit tooling works. Many agents apply edits via `git apply` and
  self-check with `git diff`; if the cloned repo's `.git` was stripped (and
  `.dockerignore` excludes `.git` from the build context anyway), `/app` is NOT
  a git repo at runtime, `git apply` silently fails, `git diff` shows nothing,
  and agents that understood the fix perfectly still score 0 (confirmed June
  2026: a grpc-go task got 0/3 agent trials purely because patches never landed,
  flagged "Some tests not passed by any agent run"). Add after the source COPY
  and build:
  ```dockerfile
  RUN git init -q \
      && git config user.email task@example.com \
      && git config user.name task \
      && git add -A \
      && git commit -q -m "initial task state"
  ```
  This runs inside the image (not the build context), so it does not trip the
  `check_dockerfile_hygiene` `.git`-in-context warning. Oracle/nop are unaffected
  (oracle applies `fix.patch` with `patch -p1`, not git).
- install build tools only when the agent must rebuild source
- **warm the build during image build whenever the agent must rebuild** (any
  compiled or heavy-build language — Rust, Go, C/C++, TypeScript, Java, Scala).
  Run one full build of the *unmodified* repo in the Dockerfile so every
  dependency is fetched and compiled and the build cache is populated; the
  agent's post-edit rebuild is then incremental (seconds), not cold (minutes).
  e.g. `RUN cargo build --tests`; `RUN go build ./... && go vet ./...`;
  `RUN npm ci && npm run build`; configure + `make` for autotools/CMake. A cold
  per-edit rebuild is the #1 cause of the Agent Timeout Gate (see that section).
- login-shell PATH: covered by the "expose the language toolchain on
  `/usr/local/bin`" bullet above — the same symlink rule applies whenever the
  agent must rebuild. Sanity: `bash -lc 'which <tool>'`.
- pin Python/package dependencies exactly
- avoid `COPY tests/` and `COPY solution/`
- avoid creating `/tests`, `/oracle`, `/solution`, or `/logs/verifier`
- bake every dependency at build time; keep `[environment].network_mode =
  "public"`, and explicitly set `[agent]`/`[verifier]` to `"no-network"` unless
  that phase genuinely needs internet access
- avoid heredocs and opaque generated source in the Dockerfile; store source as
  files and `COPY` it
- use one clean apt transaction per stage with `--no-install-recommends` and
  remove `/var/lib/apt/lists/*`
- pin downloaded binaries by version and checksum; avoid `curl | sh`
- order layers from stable manifests/dependencies to volatile task source
- extract copied archives during build and remove the archive in the same stage
- avoid broad recursive `chmod -R` or `chown -R`; use targeted `COPY` metadata
- keep package-manager caches, compiler caches, and unused build outputs out of
  the final image — **exception:** when the agent must rebuild, KEEP the
  warmed build/dependency cache (`target/`, `GOCACHE`, `node_modules`,
  `~/.cargo/registry`, `~/.cache`, etc.) so the agent's rebuild stays
  incremental. Solvability under the timeout gate beats image slimness here, and
  `check_no_build_tools_in_final_image` already permits the toolchain for
  rebuild-required tasks. Strip only caches the agent will never reuse.

Do not add root-level `pyproject.toml` as a submission artifact. If local ruff
or editor tooling needs to exclude `environment/repo`, keep that configuration
outside the submitted task or remove it before packaging.

Remove macOS junk and secret-shaped files:

```bash
find <task> \( -name '.DS_Store' -o -name '._*' -o -name '__MACOSX' \) -print
find <task>/environment -type f \( -name '*.key' -o -name '*.pem' -o -name '*.crt' -o -name 'id_rsa*' \) -print
find <task>/environment -type f \( -name 'CLAUDE.md' -o -name 'skills.md' -o -name 'AGENTS.md' \) -print
```

Do not leave AI-framework scaffolding filenames such as `CLAUDE.md`,
`skills.md`, or similar files in `environment/`.

## Agent Timeout Gate

Terminus 3 requires `[agent].timeout_sec` between **1800 and 18000 seconds**;
1800 is the minimum, not the old maximum. Most substantial tasks should use
3600–5400 seconds. Set the value to the real work budget and raise it when trial
analysis flags `low_timeout`.

A timeout is still not difficulty. Warm and slim the environment so the agent
spends its budget on the domain problem rather than cold tooling:

- **Warm the build in the Dockerfile** so the agent's post-edit rebuild is
  incremental, not cold (see the Docker Rules bullet above). This is the single
  biggest lever.
- **Keep the warmed build/dependency cache in the final image** (the explicit
  exception in Docker Rules). A warm Dockerfile build is wasted if the cache is
  stripped before runtime.
- **Budget the edit→build→test cycle.** Time one warm cycle locally and leave
  enough room for repeated inspection, editing, and validation.
- **Slim the repo** so navigation and `grep`/`rg` are cheap (see
  `upstream-repo-sanitizer`); a multi-thousand-file tree wastes agent steps
  before any reasoning starts.
- **Keep the verifier fast** — focused reproducer tests with short
  per-subprocess timeouts, never a full upstream suite
  (`terminus-hard-python-verifier`).
- Set the timeout honestly within 1800–18000; do not pad a short task to make it
  look substantial or starve a long task to manufacture failures.

Pre-check before spending real-agent budget — time the warm oracle cycle:

```bash
stb harbor run --force-build -a oracle -p <task-folder>   # build the image once
time stb harbor run -a oracle -p <task-folder>            # reuse cached image: this ~= the agent's per-cycle cost
```

The oracle does less than a solving agent. If it already consumes a large share
of the configured agent budget, warm/slim the build or raise the honest timeout
before running agents.

## Oracle Pattern

For cloned repo tasks:

```bash
#!/bin/bash
set -euo pipefail

cd /app
patch -p1 < /solution/fix.patch
python -m pytest <focused smoke test or upstream regression>
```

If the project requires build artifacts, rebuild them in `solve.sh`. The patch must solve the general bug, not only verifier examples.
For domain-profile tasks, the patch must implement the general
target behavior, not only the concrete verifier fixtures.

A green oracle run proves that the task executes, not that the reference is
correct. Independently derive the expected result for several hard/edge inputs
outside the tuned fixtures and reconcile the oracle with the visible contract.

## Verifier Pattern

`tests/test_outputs.py` runs inside the isolated verifier container. It may see
only `/tests` plus the paths listed in top-level `artifacts`; it cannot browse
the agent filesystem. Choose artifacts to match the deliverable:

- file/report tasks: declare the final files or directories and inspect them
- executable tasks: declare the built executable and run it with hidden inputs
- source-repair tasks: declare the source/project directory, bake the required
  compiler/toolchain into `tests/Dockerfile`, and rebuild there before testing
- service/state tasks: export deterministic state or another portable artifact
  that the verifier can inspect; do not assume the agent container remains live

Before difficulty probing, prove that the verifier rejects a deliberately wrong,
incomplete, or lazy solution. Nop=0 alone is not enough. Rebuild submitted source
inside the verifier when the contract requires source changes; never trust a
delivered binary on one fixed input. Keep held-out inputs separate from their
goldens and remove any predictable prior output before the graded run. Assert
actual values, not only counts/endpoints/field presence. If the candidate controls
two related artifacts, grade their equivalence with verifier-owned inputs or a
verifier-owned consumer. Invoke every documented command/mode, and make each
rule-carrying fixture exercise the hard case that distinguishes an incomplete fix.

### Exploit classes

The detailed incident notes below are organized by discovery date. Use this
table to find the class that applies to the task at hand, then read the matching
note. Workflow step 15 walks every row; an audit of 1,968 tasks across five
terminal-agent benchmarks found 16% reward-hackable, so treat a clean sweep as
evidence only for the classes actually exercised.

| Class | Reaches reward by | Where covered |
| --- | --- | --- |
| Answer key reachable | Reading a `/tests` corpus, or a golden staged beside its input | corpus hiding note below |
| Privileged candidate | Running as root and reading verifier-owned state | run-as-`nobody` note below |
| Build bypass | Grading a delivered binary never rebuilt from source | checker-owned compile note below |
| Hollow assertion | Satisfying a count, field presence, or first element | "assert actual values" above |
| Timing manipulation | Patching the clock or counter a performance check reads | below |
| Deferred computation | Returning a lazy or proxy object that passes a shape check | below |
| Subprocess injection | Spawning a background worker that finishes before verification | below |
| Binary wrapping | Shadowing a system utility the verifier invokes | below |

The last four classes matter most for `P4` secondary-observable and `P6`
holistic tasks, whose graded observable is a runtime measurement rather than a
returned value:

- **Timing manipulation.** Never grade a duration the candidate's process can
  report or influence. Measure from the verifier's own process around a
  candidate invocation it controls, or grade a structural proxy — an operation
  count, an emitted plan, an allocation profile — read from an artifact the
  candidate cannot rewrite after the fact. A candidate that can `import` the
  timing module the check uses can redefine it.
- **Deferred computation.** Force materialization before asserting. Check the
  concrete type, not just the interface; a wrapper that defers work until the
  result is consumed passes a shape assertion and never computes anything.
- **Subprocess injection.** Reap the candidate's process group and confirm it
  exited before reading artifacts. The existing `_kill_process_group` helper is
  the mechanism; the rule is that no candidate-spawned process may outlive the
  invocation whose output is graded.
- **Binary wrapping.** Invoke system utilities by absolute path from the
  verifier image, never through a `PATH` the candidate can prepend to. A
  candidate-supplied `python`, `bash`, or `curl` earlier on `PATH` intercepts
  the verifier's own tooling.

No single defense is sufficient; hardening composes, and each layer must leave
the reference solution passing.

Verifier-only tests and expected data stay under `tests/` and are copied into
the verifier image with `COPY . /tests/`; they are never staged in the agent
environment. Create every artifact parent directory in `tests/Dockerfile`.

**Re-check the RESOURCE is novel before scaffolding a conformance-style task.**
The named-suite universe (WHATWG / Unicode UTS-UAX / RFC CTS / JSON-Schema /
TOML toml-test …) is small and SHARED across teammates, so a slug-distinct task
built over the SAME official suite is still a duplicate. Before cloning, confirm
the artifact's `conformance_suite`+`spec` is not already `claimed`/`submitted`
in `mined-candidates/index.jsonl` (human mirror: the L1 claimed-resource ledger
in `.agent/skills/task-miner/lever_patterns.md`). If it is taken, STOP and
re-target the same lever onto a fresh spec+suite rather than cloning — learn the
pattern, not the resource.

**Expected-output DATA is a test vector too -- keep the answer key out of
`environment/repo`.** For conformance-style tasks graded against an official
suite, the `(input, expected-output)` vector table lives ONLY under `tests/`
(embedded in `test_outputs.py` or a `tests/*.json` data file the verifier reads).
NEVER commit the answer table into `environment/repo` -- e.g. a `cases.rs` /
`vectors.json` plus a repo `selftest` subcommand that a verifier test invokes.
The agent reads the shipped repo, so a repo-embedded answer table hands over the
expected outputs and the task collapses to trivial. If you want a fast in-process
full-suite check, feed the vectors from a `tests/` file into the binary at verify
time (or have the binary read a path under `tests/`); do not compile them into the
shipped crate. Before shipping, grep the repo for answer-shaped data:
`grep -rlE 'expected|TEST_CASES|÷|<the exact output token>' <task>/environment/repo`.
Confirmed 2026-07-01: a UAX-14 line-break task shipped `src/cases.rs` with all
19338 `(input, expected ÷/× marker)` vectors so a repo `selftest` could check them
-- that leaked the entire answer key; the fix was to move the check to the hidden
`tests/` vectors and delete the repo table.

**Anti-cheat: a `/tests`-readable expected-output corpus + candidate-run-as-root
is a reviewer-blocking cheat surface (2026-07-18, sbom-purl-key + lowess —
AGENTS.md §3).** A candidate that just reads the `/tests` corpus and echoes each
row's `expected` passes every case with zero logic. For any conformance-style
clone, stack ALL of these (difficulty-neutral):
1. `_hide_corpus()` — load the corpus into memory, then (only when
   `dirname(CORPUS) == "/tests"`) `os.unlink` the corpus file AND
   `os.chmod("/tests", 0o700)` BEFORE compiling or running any candidate code.
2. Run the candidate as an unprivileged user — `subprocess.run(...,
   user="nobody", group="nogroup")` iff `os.geteuid() == 0` (else no kwargs, so
   local non-root runs keep working) — and `chmod -R a+rX` the temp build dir
   (plus `0644` file-argument inputs / `0755` their dirs) so `nobody` can read
   root-owned artifacts.
3. Checker-owned compile: never run a submitted Makefile/executable while the
   corpus is readable; compile the submitted source with the verifier's own
   command. Remove `/solution` in the build fixture (the oracle's solve.sh has
   already copied its source into `/app` by verify time) and reject a
   translation unit that is a symlink, resolves outside `/app`, or `#include`s
   an absolute, `..`-containing, or `solution`-named path.
4. Run pytest as `python3 -I -m pytest` from a fresh verifier-owned dir — this
   blocks an agent-planted `/app/sitecustomize.py` that `os._exit(0)`s the
   interpreter into a free reward.
5. Prove it with a cheat-emulation: a corpus-reading candidate must pass the
   OLD verifier (reward 1) and fail the NEW one (reward 0), while oracle stays
   1 and nop 0. Sweep every language sibling of a shared-corpus port series —
   they share the hole.
6. Stage anything the verifier execs on an exec-capable base (`/app`,
   `/var/tmp`, `/dev/shm`), never bare `/tmp` — the platform mounts `/tmp`
   noexec; the `scripts/preflight.sh` `--tmpfs /tmp:noexec` repro in Quality
   Preflight catches this.

**Structure conformance corpora for union-not-intersection difficulty (the
"Some tests not passed by any agent run" gate is BLOCKING).** Score per-case
or in graded bands whose top band a best realistic run can actually reach.
Verify CTRF reports each case independently; if parametrization collapses rows,
generate uniquely named `test_case_001`-style functions. Never use ONE
monolithic all-N-cases-must-pass function — a single
universal blind spot then turns that whole test 0/N and the task gets returned.
Before shipping, audit any case every fresh implementation misses: verify the
oracle/authority, explicit interface, evidence support, and CTRF resolution.
Disclose only a non-inferable interface fact; keep a legitimate evidence-based
inference, add authentic evidence if support is weak, or remove an invalid
oracle-only assertion. Apply
[bounded task design](../terminus-regular-task-authoring/references/bounded-task-design.md).
Derive corpus size from retained obligations and discriminating witnesses,
without numerical unit/cluster quotas. Never pad correlated rows. Mix verifier
shapes when appropriate (scenario, property/metamorphic, mutation/anti-shortcut,
final-state, tolerance/differential); every feature cluster keeps ≥1
"soft" case a majority of runs pass; and the trimming direction is always
data-driven from the per-case pass table — NEVER "drop the easy cases, keep
the hard ones" (easy cases are the coverage that keeps the 0/N flag from
firing; a hard-only corpus maximizes 0/N exposure). Full remediation decision
tree when the flag fires anyway:
`.agent/skills/task-revise-flag-remediation/SKILL.md`
(design-time rules: `lever_patterns.md` L1 step 6).

**Fail verifier breadth before Oracle work.** Immediately after the verifier
skeleton is collectable, create `workspace/reports/<slug>/verifier-matrix.json`
with schema version 1, the profile, every platform-visible unit ID, exact unit
to cluster mapping, IDs of actual cross-cluster witnesses, and appropriate
verifier shapes (no minimum count beyond a non-empty inventory). Run:

```bash
python3 .agent/skills/terminus-regular-task-authoring/scripts/verifier_architecture_check.py \
  matrix workspace/reports/<slug>/verifier-matrix.json \
  --task-slug <slug> --allow-missing-ctrf
```

This first pass may omit `ctrf` because no Oracle exists yet. After Oracle runs,
add its raw CTRF path/hash and rerun without `--allow-missing-ctrf`. Never call
a suite “semantic coverage” merely because Oracle passes it; use “smoke suite”
until verifier architecture and mutation-backed semantic coverage both pass.

Portal baseline: before submission, run at least one deliberately wrong,
incomplete, or lazy implementation and confirm the verifier rejects it. Invoke
every documented command/mode on a discriminating hard case, rebuild delivered
binaries from submitted source, and independently spot-check the Oracle against
the visible spec on an edge not used to tune its answer key. The task-batch
per-node mutant campaign is stronger than this baseline and remains required.
For every domain rule explicitly named by the contract, keep an isolating
fixture whose expected result changes when that rule alone is inverted; a
coarse wrong solution or mixed held-out corpus is not enough, and held-out data
must not be the only enforcement of a stated rule.

Before packaging, walk the portal quality panel's five axes:
`coherent_contract`, `correct_reference_solution`, `protected_ground_truth`,
`sound_verifier`, and `deterministic_execution`. `Minor` and `Major` block on `coherent_contract`,
`correct_reference_solution`, `sound_verifier`, and `deterministic_execution`;
only `Major` blocks on `protected_ground_truth`. Findings explicitly marked
`Advisory` do not block, and `Unsure` is not itself a confirmed defect, though
an undecided axis still leaves the panel uncleared. Passing the panel allows
difficulty measurement; it is not task acceptance. Preserve Terminus 3
inference: exact grading conventions need a citable visible authority, while a
domain mechanism may still be reconstructed from distributed visible evidence.

Use real parsers for JSON/XML/CSV. Assert behavior, not source shape.

For Hardware / CAD tasks, follow
`docs/creating-tasks/cad-task-guidelines.md`: measure every stated dimension on
the built solid with a method that can see it; sampling brackets must be finer
than the stated tolerance; verify through/repeated/exact-count features; and
test pose/construction-order freedom. A parametric promise requires changing a
fresh driving value, recomputing, checking for errors, and measuring the changed
geometry. Reading the parameter back is not behavioral coverage.

Verifier matrix for upstream bugfixes must include:

- direct upstream regression
- boundary or ordering edge case
- normal behavior preservation
- anti-shortcut check
- **one discriminating test per independent criterion the instruction lists.**
  If the prompt names N separate reject/accept conditions (e.g. reject modulus
  >8192 AND prime >4096 AND exponent malformed), a verifier covering only one
  lets an agent add a single check and pass — reviewers flag this Critical. Each
  test must DISCRIMINATE: the input must be ACCEPTED by the buggy code and
  REJECTED only by the fix. Watch for a downstream validator (e.g. `rsa.Validate`
  / `pk.Validate()`) that already rejects malformed inputs on the buggy build —
  that makes the test pass on both nop and oracle (a dud). Isolate each criterion
  with an OTHERWISE-VALID input that violates only the target bound (e.g. a real
  RSA key with one prime >4096 but modulus ≤8192; a valid key with a large odd
  exponent). Some criteria a validator already enforces (even exponent, e<3)
  cannot be made discriminating — do not add them as duds.
- no internal crash/traceback when the expected behavior is recoverable
- output format/schema check when relevant

Verifier matrix for domain-profile tasks must include:

- primary target behavior from `instruction.md`
- at least one edge case not identical to the main example
- existing behavior preservation
- semantic output parsing or artifact inspection
- anti-shortcut variation in names, ordering, values, or fixture layout
- category-specific contract checks such as schema, build artifact, service health, security exploit failure, numeric tolerance, metric threshold, or game-state transition
- a tolerance witness using exactly the error band promised by the instruction
  whenever numeric tolerance is part of the contract
- an objective/tie-break witness that distinguishes the specified optimum from
  a merely feasible or differently optimized answer whenever applicable

Every test function needs a docstring. Every asserted behavior must be supported
by `instruction.md`, an agent-visible environment reference, or domain evidence
the instructions explicitly direct the agent to inspect.

Preservation tests are not exempt from prompt coverage. If a verifier checks that non-target modes, aliases, fallback paths, legacy layouts, or normal behavior still work, `instruction.md` must say so naturally.

Example:

```md
Fix the `--import-mode=importlib` collection case. Keep the existing `prepend` and `append` import modes working for the same shadowed-layout projects, and preserve assertion rewriting for nested package tests.
```

Anti-shortcut tactics:

- use temporary directories and generated project names
- vary filenames, ordering, or input values across tests
- keep goldens and held-out fixtures inside the separate verifier image, never
  derive truth from `/app` or another agent-writable tree
- when the verifier rebuilds or executes agent-supplied code, drop privileges
  before that exec, use `--no-new-privs` or equivalent containment, and ensure
  the process cannot read goldens, hidden fixtures, or `/logs/verifier`; never
  colocate an expected answer with an input-tree path passed to that process
- declare exact output paths as top-level artifacts and let the harness transfer
  them; do not manually copy agent-controlled directories where symlinks can
  expose verifier fixtures
- include one unseen variant not present in the upstream PR
- avoid exact source-code assertions
- parse outputs semantically rather than matching full files
- if verifier Python changes interpreter permissions, resolve and deduplicate
  `/bin/bash` and `/usr/bin/bash` targets before saving modes, restore once in a
  `finally` path, and verify full Oracle log/reward collection; the platform-only
  `verifier_interpreter_permissions` preflight blocks the unsafe dual-path pattern
- never require an EXACT error-message string the instruction does not disclose.
  If discrimination needs distinguishing the fix's rejection from the buggy
  build's rejection (both error), prefer a pass/fail behavioral test (an input
  the buggy build accepts and the fix rejects); else match a loose token from
  the instruction's own vocabulary (e.g. instruction says "round count" → match
  case-insensitive `round`), which accepts any reasonable agent phrasing yet
  still differs from the buggy build's unrelated error. Matching the reference
  solution's exact wording fails functionally-correct agents who phrase the
  message differently (`task_specification` / representation overfit). Probe the buggy
  error first to confirm the loose token is absent there, and verify a variant
  wording still passes.

The oracle patch must pass the direct regression and at least one variant, proving it is not verifier-targeted hardcoding.

## Verifier API Sanity

Before packaging, run a focused smoke check for every import and constructor
used by `tests/test_outputs.py`.

For each tested API/class, verify:

- the import works in the pinned starting repo
- the constructor call matches the real signature
- the object under test actually owns the method/property being asserted
- skip guards catch only genuine absence, not broken construction or wrong API
- wrappers and raw containers are not confused

Bad pattern:

```python
try:
    from package.platform.response import RawResponse
except ImportError:
    pytest.skip("not available")

resp = RawResponse(wrapper_like_arg, request_method="GET")
```

The `ImportError` guard does not protect against a wrong constructor. If the
class exists, a `TypeError` is a verifier bug. Use the real wrapper class or
remove the secondary-implementation test.

Recommended smoke command before Harbor:

```bash
cd <task-folder>
<repo-root>/scripts/python3 -m py_compile tests/test_outputs.py
```

Then run oracle and nop. A broken verifier must be fixed before any difficulty
or quality signal is trusted.

## tests/test.sh

Use the Terminus 3 verifier pattern below. The verifier runs in a separate image
built from `tests/Dockerfile`; it sees only the declared artifacts.

```bash
#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier
python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
rc=$?
if [ "$rc" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
```

Do not use `set -e`; a failed pytest must still reach the reward block. The
script must end on the reward block's `fi`, with no trailing `exit`: pytest's
status is captured and never propagated, while a failed reward write must remain
an infrastructure error. If the published skeleton differs, the skeleton wins.

Verifier dependencies must be available before `tests/test.sh` starts. Install
`pytest`, `pytest-json-ctrf`, and verifier-only dependencies in
`tests/Dockerfile` with exact pins. That Dockerfile must be digest-pinned,
`COPY . /tests/`, and create parent directories for every top-level artifact.
`tests/test.sh` should run pytest and write
`/logs/verifier/reward.txt`; it must not install packages or fetch from the
network.

Keep runtime/project dependencies separate from verifier-only dependencies. For
editable installs of the target package, prefer `pip install --no-deps -e .`
after installing pinned deps so project metadata cannot fetch or override
unpinned packages.

## Spec-task gotchas that cost a re-run (2026-06-21, learn these)

When cloning a from-scratch spec-implementation whose oracle is checked against a
real external tool/library (gitignore, chmod, IPv6, quantile, DST, …), four
mistakes each cost a full rebuild this session — avoid them up front:

- **Reference the authoritative external behavior in `instruction.md`; do NOT
  enumerate the rule mechanics.** A prose list of matching rules / a precedence
  table reads to the platform reviewer as a "design specification that prescribes
  implementation" — the `instruction_check` warning and the #1 client reject.
  Instead say "the result must match what `git check-ignore` reports / matches
  `numpy.quantile(method=...)`" and let that named reference be the authority.
  This ALSO satisfies instruction/test symmetry (the named reference defines
  correctness) without listing internals. Keep only YOUR I/O format + the
  observable contract; drop the mechanics. AND write the whole instruction as
  flowing prose (usually 1-3 paragraphs, not a hard cap) — NOT as
  `Input`/`Output`/`Build` sections:
  `instruction_check` flags rigid spec-section structure as a "design document"
  too, even after the rule tables are gone. Weave the stdin/stdout format into
  narrative sentences that say *why* each part matters (confirmed: a
  section-structured but rule-free instruction still drew the warning; the prose
  rewrite cleared it).
- **Generate ground-truth fixtures with the SAME runtime VERSION the verifier
  uses (inside the task image), never the host.** Baking fixtures from a host
  interpreter can disagree with the in-image one on edge cases (e.g. Python 3.9
  vs 3.11 `ipaddress` on a trailing-colon address), so the oracle passes locally
  but fails in CI. Run the reference in the task's base image (or the exact
  pinned version) when dumping expected values.
- **Pin verifier deps with a hash-locked `requirements.lock` + `pip install
  --require-hashes --no-deps`, for EVERY language's task** (not just Python ones).
  Inline `pip install pytest==x pytest-json-ctrf==y` trips the static-check
  lockfile warning even in a Go/C++/Rust task. Put `requirements.lock` in the
  `tests/` build context, copy it from `tests/Dockerfile`, and install it in the
  verifier image. Never put verifier-only dependencies in `environment/`.
  (Reusing an existing task's lock is fine.)
- **Don't make blank/empty input a fixture VALUE if the program skips blank
  lines, and avoid positional-alignment verifiers.** A program that ignores blank
  lines emits no output line for an empty input, which both contradicts an
  "empty -> INVALID" expectation and shifts every later line in an
  index-by-position comparison. Prefer one invocation per case, or assert on a
  parsed mapping, and only test inputs the program actually emits a line for.

## Quality Preflight

Before packaging or platform upload:

- **run `scripts/preflight.sh <task-dir>` (repo root) — zero FAIL rows
  required.** It machine-checks layout, .dockerignore entries, Dockerfile
  hygiene (syntax line, cloud-compatible `COPY --chown`/`COPY --from`,
  canonical digest-pinned base, bind-mounts),
  task.toml fields, leak sweep, zip arcnames/CRLF, rubric format, docker
  oracle=1.0/nop=0.0, and the oracle-under-`--tmpfs /tmp:noexec` repro.
  (New tasks should have been stamped by `scripts/new-task.sh`, which
  pre-wires the hygiene this checks.)
- **run the per-case pass-table pre-audit for corpus-graded verifiers.**
  Re-score stored blind-probe diffs against the full corpus. For a zero-solve
  local Frontier signal, require 100% union coverage, zero common misses, and
  de-correlated failures; otherwise the result may be an oracle defect or one
  shared blind spot. For Core/Base candidates, shared misses are a review risk
  rather than an automatic rejection, but every shared miss still needs an
  authority/oracle and V3 evidence-inferability audit before packaging.
- **close the difficulty-design loop.** Re-read
  `workspace/reports/<slug>/difficulty-design.json` against the frozen task:
  every declared trap has a killed mutant in `semantic-coverage.json`, every
  declared cheat has a block recorded in `adversarial-pass.json`, and the
  coupling edges still hold after repairs. A trap that lost its witness, or a
  coupling edge that a repair severed, is a difficulty regression — re-measure
  rather than packaging on the earlier probe.
- **run the Terminus 3 domain screen.** Apply
  `.agent/skills/task-miner/category_rules.md`, choose exactly one category and
  subcategory, and write `workspace/reports/<slug>/category-screen.json` with a
  domain rationale plus citations to the instruction and verifier evidence.
  Do not use the legacy nine-slug classifier or reshape prose to chase an old
  classifier result.
- run a V3 symmetry audit: exact artifact paths, public interface/schema,
  arbitrary constants/strings, and non-inferable operational constraints must
  be explicit; semantic invariants may instead map to one or more visible
  evidence sources and may be tested on held-out instances/combinations
- create `workspace/reports/<slug>/instruction-sufficiency.json` with
  `schema_version: 3`, map every static test to an explicit-contract row or an
  inference family, complete two fresh task-visible fairness reviews, and run
  `sufficiency_manifest_check.py --require-v3`; any failure blocks the full
  solve probe and packaging
- In `campaign_ready`, create `workspace/reports/<slug>/semantic-coverage.json` following
  `terminus-regular-task-authoring/references/semantic-coverage-gate.md`; map
  every promised public surface, record the natural causal mechanisms and
  interactions without a count quota, and preserve a killed executable mutant
  per mechanism/interaction. Pass `semantic_coverage_check.py --advanced-plus`
  before preparing counted probes
- before counted preparation, run strict Docker preflight to
  `probe-preflight.json`, folder-level client/manual review to
  `pre-freeze-review.json`, and task-visible style audit to
  `task-style-preflight.json`; require `preprobe_check.py` to pass
- treat fixture multiplication as zero added semantic rank: one keyword across
  eight units or one numerical branch across fourteen scales remains one
  mechanism
- state preservation of a public mode/interface when the user must know it is
  in scope; hidden variations of the same inferable invariant do not need to be
  enumerated in the prompt
- run a verifier API sanity audit for every public entry point promised by the
  instruction; each must have a platform-visible discriminating test. Tests may
  not pin undocumented keyword spelling, internal attributes, class identity,
  or exact error wording when the contract permits semantic equivalents
- remove implementation hints, issue URLs, PR IDs, commit hashes, upstream test names, and private helper names from `instruction.md`
- remove hidden walkthroughs, procedural hints, and prompt-bypass instructions
  from environment files, comments, README, configs, scripts, TODOs, `spec.md`,
  and architecture docs
- verify the task root has no `pyproject.toml`
- verify the manifest contains one exact Title Case category/subcategory pair,
  3–6 tags, a current difficulty tier, and all required explanation fields
- verify top-level `artifacts` lists every path the verifier reads, and
  `tests/Dockerfile` creates their parent directories
- verify `[verifier].environment_mode = "separate"` and that the agent image
  never copies tests or solution data
- run `ruff check <task-folder>` over the WHOLE task dir. Platform CI lints
  `environment/repo` too (default E4/E7/E9/F rules), so a non-`ruff`-clean
  upstream dev/codegen `.py` fails the build. Remove non-build-required upstream
  `.py` that has lint errors; fix build-required generators in place
  (output-preserving, e.g. move an `E402` import to the top) and re-run oracle.
  Also clear `F401`/`E741` in `tests/test_outputs.py`.
- verify rubrics do not reference tests, verifier logic, `test.sh`,
  `test_outputs.py`, `/tests/`, hidden tests, CI, reward files, or pytest
  results
- verify `tests/` contains verifier scripts/fixtures only, not dependency
  wheels
- verify `tests/Dockerfile` exists, digest-pins every `FROM`, copies the tests,
  and bakes all verifier dependencies with exact pins
- verify `tests/test.sh` does not run runtime setup, `apt-get`, `pip install`,
  `npm install`, or network downloads
- verify Dockerfile does not `COPY tests/`, `COPY solution/`, or create `/tests`, `/solution`, `/oracle`, `/logs/verifier`
- verify Dockerfile uses a canonical final runtime base (or non-canonical with a
  credible justification), has no
  heredoc-generated source files, no tag-only `FROM` image, no unverified
  downloads, no stale copied archives, and no broad recursive permission rewrites
- verify `environment/ <= 100 MiB` and no file under `environment/` exceeds `50 MiB`
- verify `environment/` contains no `.git`, `.env`, credentials, package caches,
  build outputs, or AI-framework scaffolding files such as `CLAUDE.md` or
  `skills.md`
- remove `.ruff_cache`, `.pytest_cache`, `__pycache__`, `.DS_Store`, `._*`, `__MACOSX`, reports, logs, and local notes from the submission ZIP
- run oracle and nop; nop must fail for the intended behavior, not missing deps or setup errors

## Submission Explanation Workflow

Generate submission explanations only after the prompt, oracle, verifier, and
available solve probes are stable.

1. Write `submission-explanations-source.md` from task evidence:
   - Difficulty: interacting concepts, the tempting partial fix, fair semantic
     failure patterns from solve probes, and why the issue requires reasoning
     across more than one local symptom.
   - Solution: root cause, high-level oracle strategy, and preserved behavior.
   - Verification: requirement-to-test mapping, why cases discriminate, and
     actual oracle/nop results.
   - Relevant Experience: concrete domain, toolchain, or repository background
     that supports the task design, without invented credentials.
2. Produce the complete platform packet at
   `workspace/submissions/SUBMISSION-<slug>.md` (the single canonical name, shared with
   `task-batch`) containing, beyond the four explanation fields:
   - **Metadata**: "Does this task use an approved canonical base image?"
     Yes/No + the exact digest-pinned image from the Dockerfile; "Did you use
     a Task Inspiration from the Task Gallery?" Yes/No + the Inspiration ID
     when yes (`mined-candidates/gallery_tasks_snapshot.md`).
   - **Rubrics**: the full paste-ready block (NOT shipped in the zip) —
     format rules in the Rubric quality section above and AGENTS.md §9: one
     physical line per criterion starting with `Agent`, closed score set
     {+1,+2,+3,+5,-1,-2,-3,-5} with mandatory leading `+`, positive sum
     10–40, block appears once, behavior-not-work-steps, affirmative
     penalties, no test paths, fixture values, oracle outputs, root-cause hints,
     or implementation recipe.
   - **File zip name**: the matching zip in `workspace/submissions/`.
3. Apply the human-writing rules from `terminus-regular-task-authoring` only as
   an editorial pass. Do not add claims, remove thresholds, or change technical
   meaning.
4. Compare the final version with `instruction.md`, `solution/fix.patch`,
   `tests/test_outputs.py`, and validation reports.
5. Keep the source notes and the packet outside the task ZIP.

Use this structure in both files:

```md
# Difficulty Explanation

...

# Solution Explanation

...

# Verification Explanation

...

# Relevant Experience

...
```

The final text must not mention LLMs, AI, models, agents, anti-LLM techniques,
detection avoidance, submission guidelines, or reviewer criteria. Although the
form asks why the task is challenging for humans and agents, answer by
describing the intrinsic technical difficulty rather than speculating about a
solver type.

## Quota Discipline

Avoid monolithic end-to-end exploration. After each phase, compress findings into compact notes and stop carrying raw diffs unless needed.

Exploration limits:

- inspect `<= 10` source/test files unless blocked
- inspect `<= 3` commits around the fix
- do not enumerate full repo trees or unrelated test suites
- reuse upstream regression tests as inspiration, but wrap them in behavioral verifier tests

For large repos such as TypeScript, go-ethereum, PyTorch, pandas, or NumPy, use focused staging/sparse extraction and strict runtime checks before investing in verifier/oracle work.

## Validation

Run what is available (full verified CLI surface + infra-failure triage live in
`task-harbor-runner`):

```bash
stb harbor run -a oracle -p <task-folder>
stb harbor run -a nop -p <task-folder>
stb harbor check <task-folder>
stb harbor run -m @openai/gpt-5.6 -k 4 -p <task-folder>   # difficulty, needs approval
stb harbor run -m @anthropic/claude-opus-5 -k 4 -p <task-folder>
```

Use the current Terminus 3 model commands when credentials and quota are
available. Otherwise record fresh isolated local probes as preliminary evidence;
they do not replace the platform's single eight-run difficulty measurement.

If Docker is not running, still run static checks:

```bash
scripts/python3 -m py_compile <python files>
scripts/python3 - <<'PY'
import tomllib
tomllib.load(open("task.toml", "rb"))
PY
```

Difficulty is measured once, after the quality panel passes and before human
review: four runs per current reference model, eight total. For a new
submission, at least 3 of those 8 runs must fail, so no more than 5 may pass
and the maximum measured accuracy that can proceed is 62.5%. Tasks already on
the platform by the morning of Sep 15, 2026 keep the prior one-failure rule,
including their later revisions.

Difficulty gate (PLATFORM-result interpretation only — these numbers come from
the platform's own agent runs after submission, not from anything runnable
locally):

- `frontier`: <20%; `advanced`: 20–<50%; `core`: 50–<80%; `base`: 80–<100%.
- The tier bands are unchanged, but a new submission needs at least 3 failures
  in 8 runs, so `base` and a 75% `core` result cannot proceed. `base` remains a
  valid tier only for grandfathered tasks and their later revisions.
- If the oracle patch is `<= 10` meaningful LOC in one obvious file, require empirical agent failures before keeping it.
- Timeouts, refusals, unclear instructions, and environment defects do not count
  as legitimate difficulty; resolve the trial-analysis flags and re-measure.
- For `near_miss`, inspect the per-run failure pattern: repeated misses on the
  same one/few tests point first to the check, instruction, or oracle; different
  misses across runs are more credible difficulty. Do not raise the tier merely
  because nearly complete runs count as failures.

## Final Packaging

Zip task contents, not the containing folder:

```bash
cd tbrain-<problem-slug>
find . \( -name '.DS_Store' -o -name '._*' -o -name '__pycache__' -o -name '.ruff_cache' -o -name '.pytest_cache' -o -name '.mypy_cache' \) -print
TASK_NAME="$(basename "$PWD")"
REPO_ROOT="$(git -C "$PWD" rev-parse --show-toplevel)"
ZIP_PATH="${REPO_ROOT}/workspace/submissions/${TASK_NAME}.zip"
mkdir -p "${REPO_ROOT}/workspace/submissions"
zip -rX "$ZIP_PATH" instruction.md task.toml environment solution tests \
    -x '*.DS_Store' -x '__MACOSX/*' -x '*/__pycache__/*' -x '*/.ruff_cache/*' -x '*/.pytest_cache/*' -x '*.pyc'
```

Regular task ZIPs must contain only submission-required files/folders, not root
`pyproject.toml`, `reports/`, `submissions/`, `workspace/`, logs, caches, or
scratch notes.

## Hand-Off

When done, report:

- source issue/PR URL and pinned starting commit
- task folder path
- task slug under `workspace/` and why the name omits repo/domain filler
- tests included and which prompt requirement each covers
- validation commands run and results
- paths to the factual and UI-ready submission explanation files
- any blocked step, especially Docker/Harbor/API key availability
