---
name: task-batch
description: "Use when the user wants an autonomous end-to-end batch of brand-new Terminus Regular tasks delivered to submissions/, including /task-batch, /task-batch 3, tạo batch task, or chạy batch. Run fresh-only mining, category and collapse screening, adaptive Difficulty × Fairness probes, build, validation, packaging, and SUBMISSION.md without further prompting. Accept an optional delivery quota, default 4; treat quotas above 6 as cumulative sequential rounds. Do not use for single-task work, ports, or remediation of returned tasks."
---

# Task Batch — autonomous end-to-end delivery

Mission: deliver `<quota>` (default 4) brand-new Terminus Regular tasks at
≥ MEDIUM, fully autonomously. Do not ask the user questions mid-run; every
drop/redesign/lane decision is yours, governed by AGENTS.md and the skills
below. The quota is the commitment; every candidate is raw material — drop
without regret, and NEVER lower the handover bar to hit the number.

## Frontier-training calibration — read FIRST (this is training data)

The tasks train/eval a frontier model, so the value of a task = it makes the
STRONGEST model FAIL, FAIRLY, in an under-covered category. Four consequences
override intuition:

- **Probe in MEDIUM thinking mode, model-agnostic.** Run every skeleton and
  difficulty probe subagent in **medium thinking mode** on whatever
  frontier-tier backend is running this skill — do NOT hardcode a model name;
  this prompt is ported across agents (GPT / Claude / DeepSeek). Aim the probe
  at the strongest tier the backend offers: a PASS = EASY, drop it; only a
  **fail-broad** task qualifies. For training data you want anything the
  frontier solves gone — this raises the bar and lowers yield, which is correct.
  Record `probe_model` (the actual backend used) in the verdict.
- **Test-count ≠ difficulty, but verifier breadth is still a HARD gate.** For
  cheap deterministic tasks, require 50–1000 **platform-visible, meaningful
  evaluation units**; for genuinely expensive stateful/interaction tasks,
  require 20–80 scenarios. A corpus row hidden inside one aggregate pytest
  function is not platform-visible. Generate uniquely named test functions
  (or prove from CTRF that `summary.tests == intended_case_count`) so the
  per-case pass table can expose 0/N cases. Corpus size is a GRADING property
  (coverage / anti-hardcode / no 0-N flag), never evidence of difficulty.
  browscap has 171k patterns and is EASY. Difficulty is certified ONLY by the
  blind probe landing 0–2/3 broad — never by corpus size. Do not pad micro-cases
  to look hard. Conversely, 4–8 aggregate tests over one mechanism never
  satisfy the breadth gate merely because each function loops over many rows.
- **Category is GATE-ZERO, checked BEFORE any heavy build.** The dominant
  failure this arsenal hits is spending a full oracle/corpus build on a shape
  that then predicts software-engineering (the p0f build). Run the rules-first
  category screen (`task-miner/category_rules.md`) on the skeleton instruction
  at the SKELETON stage; a fired BLOCK rule kills the candidate before build.
- **Diversity of FAILURE-MODE is the product.** A task that fails the model in a
  NEW way beats three that fail it the old way (a monoculture of one lever =
  low-rank gradient). The durable difficulty axis is EXECUTION / INTERACTION /
  DISCOVERY (horizon, hidden state, no iterative feedback), which ages with
  scale; information-asymmetry conformance/matcher shapes are mostly spent
  (documented→EASY, undocumented→category-SWE) — keep them a minority lane, and
  log a `failure_mode` field for every delivered task to track coverage.

**Quota semantics — the quota is the target, honesty is the contract.** The
run ends in one of exactly two ways: (a) `<quota>` tasks in `submissions/`,
each passing all six handover conditions; or (b) the **honest-exhaustion
exit** — the full pivot ladder (Dry-round handling below) has been walked AND
two consecutive fully-pivoted rounds delivered nothing new, in which case the
run ends below quota with the complete exploration map and a per-seam verdict
report. Recent clean-slate evidence puts fresh HARD+category-safe yield at
roughly 0–1 per large batch (AGENTS.md §6); treat 10-fresh as infeasible and
report honestly rather than pad. An
under-quota exit backed by a full exploration map is a CORRECT outcome, not a
failure; padding with lowered-bar tasks or ports is the failure. Never ask the
user anything mid-run, and never lower the handover bar to hit the number. A
quota >6 (e.g.
`/task-batch 10`) runs sequential internal rounds of 3–4; BETWEEN rounds fold
only durable, evidence-backed design laws and live/dead verdicts into
`AGENTS.md`, the sole durable knowledge store. Local logs may support resume
and audit but are not parallel knowledge stores. Report progress after each round
(delivered so far / quota, plus that round's exploration map) — a status
report, not a question. If the session is interrupted, re-invoking
`/task-batch <quota>` resumes: count already-delivered zips in
`submissions/`, reload state from `index.jsonl`, and continue toward the same
cumulative quota.

Environment notes: harbor + Docker work locally (~3 min/oracle run) and need
no LLM; harbor LLM / stb are geoblocked from VN — run every difficulty and
category probe yourself with fresh subagents (Agent tool), never harbor LLM.

## Handover conditions — a task counts ONLY when ALL six hold

1. harbor oracle = 1.0 and nop = 0.0.
2. **Difficulty** — fair blind probe (inside the task image, `--network none`,
   terse prompt, no hints, scored by differential per
   `task-local-solve-probe`; because this skill creates frontier-training data,
   pin the strongest frontier-tier backend available in the active runtime at
   medium thinking and record `probe_model`): start with 2
   runs and use at most 3. **Two de-correlated semantic failures suffice and
   STOP probing**,
   under two hard riders: (a) failures are SEMANTIC —
   setup/instruction/compile/infra failures count for nothing, fix the task
   and re-probe; (b) the 2 failures land in DIFFERENT places — both runs dying
   on the same single case/convention is the single-lever fair⊥hard
   fingerprint, but at n=2 it can be coincidence on a multi-cluster task:
   spend ONE disambiguation run — same place again → DROP, a different place
   or a pass → normal scoring. The target band is 0–1/3 solved. A 2/3 result is
   AMBER, never automatic handover: keep it only for non-Python when the sole
   failing run contains ≥2 broad semantic clusters and no setup/reference
   advantage explains the two passes. Python tasks must be Hard (0/3 semantic).
3. **Verifier architecture + Difficulty × Fairness pass-table clean**
   (re-score stored probe diffs, no new runs): union coverage across runs =
   100%; common-miss count = 0; every
   feature cluster keeps a soft representative; and, when ≥2 runs fail, their
   failure sets are de-correlated rather than one shared lever. `Every case has
   a passer` means the UNION is 100%; do not confuse it with the best individual
   run. Any 0-probe cluster must be oracle-authority-checked BEFORE any
   prune/disclose (`task-revise-flag-remediation` Step 1.5). Attach a compact
   verifier matrix to the local verdict with: platform-visible unit count,
   feature-cluster counts, cross-cluster cases, verifier shapes, per-run
   cluster pass rates, union, and common misses. Cheap deterministic tasks need
   50–1000 visible units across ≥6 real behavior clusters; expensive
   stateful/interaction tasks need 20–80 scenarios across ≥4 clusters. At least
   two clusters must exercise interactions between rules/state, not isolated
   happy-path variants. Structural/protocol smoke tests do not count as behavior
   units. If one cluster contains >35% of the units, justify why it is internally
   heterogeneous; otherwise rebalance it. Reject semantic duplicates and
   boundary-value padding. Before accepting any model failure, prove the missed
   behavior is stated, derivable, or reachable from an in-image reference; an
   underdocumented cluster is a fairness FAIL, not difficulty evidence.
4. **Category check — rules first** (`task-miner/category_rules.md`): run the
   real-CI-calibrated rules against the task shape. A fired BLOCK rule ⇒
   reshape or drop, no probe run can override it; a fired ALLOW rule matching
   the declared category ⇒ at most one confirmatory probe run. Only when NO
   rule fires, fall back to the blind category probe — 2 runs, a 3rd only on
   a 1–1 split (fresh subagent;
   de-contaminated packet — only instruction.md + environment file tree +
   README + rubric, copied outside the repo; the subagent must NOT read
   AGENTS.md/CLAUDE.md/memory): no run predicts a blocked slug; majority
   matches the declared category.
5. No rust_cli/sibling template shape; passes `task-zip-validator` +
   `task-llm-style-audit`; zip lands in `submissions/`.
6. `submissions/SUBMISSION-<slug>.md` complete (section below).

## Strategy — 100% new tasks

Follow `task-miner` → **Fresh-only exploration doctrine** exactly: no
ports/reskins/twists (`gallery_novelty` must be `novel`); history is only the
forbidden-zone map (§6 + collapse verdicts), the design laws (master collapse
law), and dedupe/novelty/Task-Inspiration lookup. 20–30 fresh ideas per
mining round across ≥4 allowed categories and ≥4 source classes; screen ALL
with the collapse-law screen and log every verdict (rejects included) into
`mined-candidates/index.jsonl` — that log is the batch's exploration map.
Use a progressive beam: shortlist only the 4–6 highest-value, most diverse
survivors for skeleton work (never two from one family), then full-build at
most the 1–2 candidates whose probe geometry survives. Rank by expected value:
`P(category-safe) × P(fair) × P(MEDIUM+) × P(novel) / expected model calls`.

Structural diversity is mandatory, not cosmetic domain/language rotation.
Give each shortlisted candidate a six-axis design signature — `work_surface`,
`interaction`, `input_surface`, `oracle_type`, `verifier_type`, and
`failure_mode`. Do not shortlist two tasks that match on more than 4/6 axes.

**Screen control group (mandatory per round):** the screen is a one-sentence
prediction and screen-rejects are never probed, so its false-negative rate is
invisible by construction. Advance 1 screen-FAILED candidate (not
from a §6 CONFIRMED-dead family) into the skeleton probe anyway, marked
`screen_control: true` in index.jsonl. A control that holds (0/2 semantic) is
a measured screen false-negative: keep it in the normal pipeline, log the
finding as durable, and loosen the screen criterion that killed it. Controls
that collapse confirm the screen at skeleton cost, not build cost.

## Loop (repeat until quota or a stop condition)

1. **MINE** fresh per the doctrine, starting with **Repo Prospecting**
   (`task-miner`, Repo Prospecting): discover mature-but-obscure repos via
   `gh search` by lever/archetype signal — never rely on the static Source
   Queue (famous repos are memorization-poison) or on repos the model happens
   to remember. Claim slugs (`tbrain-<problem-slug>`).
2. **CATEGORY GATE-ZERO then SKELETON PROBE** (both BEFORE any heavy build):
   FIRST run the rules-first category screen (`task-miner/category_rules.md`)
   on the skeleton instruction + env tree — a fired BLOCK rule (SWE / debugging
   / data-processing) kills the candidate NOW, before you sink an oracle/corpus
   build into it (the p0f lesson: never build then discover category). THEN the
   skeleton probe: env + instruction.md + stub + a rough grader of about 30–60
   platform-visible evaluation units spanning 6–8 independent behavior
   clusters. Before probing, write the proposed verifier matrix and kill any
   candidate whose contract cannot naturally supply ≥6 clusters and ≥2
   cross-cluster interactions without padding; this catches shallow single-fix
   tasks before model quota is spent. Start with 2
   fresh blind solvers in isolated dirs outside the repo (`/var/tmp/probe-*`), net
   forbidden, every known reference lib NAMED as forbidden, every solver in
   **medium thinking mode** on the running frontier-tier backend (model-agnostic
   but mechanically pinned for that runtime; do not silently inherit or swap
   tiers). Run a 3rd solver only on a 1–1 split, a shared failure cluster, or
   incomplete union coverage. Decision table: 2/2 pass → DROP; 0/2 with
   de-correlated semantic failures and 100% union → BUILD; otherwise use the
   3rd run; 0/3 on the same case/cluster → oracle-audit then DROP/redesign.
   Running harbor oracle on a
   candidate with no skeleton-probe log is a violation — log it as a wasted
   build.
3. **BUILD** (`task-clone`): start from `scripts/new-task.sh <slug> <lang>
   <category>` (skeleton with the verifier/packaging hygiene pre-wired).
   Expand cheap deterministic tasks to 50–1000 platform-visible meaningful
   units; an honest execution/stateful task may use 20–80 expensive scenarios.
   Prefer individually named case tests over family aggregates; aggregate tests
   are allowed only as extra smoke checks. Verify the actual CTRF/readback unit
   count before handover. Measure semantic breadth separately from test count:
   a thousand variants of one rule remain one correlated cluster. Choose verifier
   shapes to fit the problem instead of copying one template; combine at least
   two appropriate shapes from scenario, property/metamorphic,
   mutation/anti-shortcut, preservation/final-state, tolerance/differential,
   and runtime-reference checks. A single broad authority corpus may substitute
   for a second shape only when its ≥6 semantic families and cross-family cases
   are explicit in the verifier matrix. Keep independent feature
   families around 40–80% per-run pass, preserve a soft representative per
   cluster, and disclose or drop any case predicted below ~35% pass. Re-score
   the stored skeleton diffs against the expanded corpus before buying another
   model call. Verifier hygiene: build from /app + check build
   exit status, hide expected-value corpora before running the candidate,
   run the candidate unprivileged, no exec from bare /tmp, instruction/test
   symmetry both directions. Before condition-5 validation, run
   `scripts/preflight.sh <task-dir>` — zero FAIL rows required.
4. **VALIDATE** against all six conditions. On a miss, fix per playbook (0/N →
   `task-revise-flag-remediation`, suspect the ORACLE first; single-lever
   fingerprint → DROP, never rescue; category drift → reshape the SHAPE and
   re-probe). Two fix rounds without passing → drop the task, refill the pool.
5. Keep the local `index.jsonl` statuses current as an execution log; one-line log per drop
   (slug | killing gate | reason). Every DELIVERED task also logs
   `failure_mode` (the KIND of mistake the frontier model made on the probe —
   missed-invariant / lost-state-over-horizon / premature-success /
   wrong-tool-sequence / undocumented-quirk / accumulation-drift …) and
   `pattern_axis` (execution / discovery / recovery / conformance), so the
   round report can show failure-mode coverage and steer the next round away
   from a monoculture. Fold only durable, evidence-backed conclusions into
   `AGENTS.md`; do not create additional knowledge stores, dashboards, claim
   systems, or memory mirrors.

## SUBMISSION.md (per delivered task → `submissions/SUBMISSION-<slug>.md`, NOT in the zip)

- **Difficulty Explanation** — your own words on why the task is hard for
  humans and agents, grounded in the REAL semantic-failure patterns from the
  probe (missed invariant/boundary/layer). Never name models/solvers, hidden
  fixtures, the verifier/tests, or use runtime/test-count as difficulty
  evidence.
- **Solution Explanation** — high-level approach + key insights; MUST match
  the submitted solve.sh/fix.patch exactly (never describe a different
  solution than the shipped code).
- **Verification Explanation** — how the tests verify correctness:
  behavioral execution, per-case corpus, preservation, anti-shortcut/
  anti-cheat. Describe the shape, never enumerate hidden cases.
- **Metadata** — "Does this task use an approved canonical base image?"
  Yes/No + the exact digest-pinned image; "Did you use a Task Inspiration
  from the Task Gallery?" Yes/No + Inspiration ID if yes (from
  `mined-candidates/gallery_tasks_snapshot.md`).
- **Rubrics** — the complete paste-ready block (rubric is NOT in the zip):
  each criterion exactly one physical line starting with the literal word
  `Agent`; scores from the closed set {+1,+2,+3,+5,-1,-2,-3,-5} with the
  leading `+` mandatory; positive sum 10–40; block appears exactly once;
  grade final BEHAVIOR, never work-steps; penalties phrased affirmatively
  ("Agent hardcodes expected outputs, -5"); no test paths, no line leaking
  the hidden lever.
- **File zip name** — the matching zip in `submissions/`.
- Run `task-llm-style-audit` over all three explanations (human-writing pass).

## Dry-round handling — PIVOT before stopping, honest exit after the ladder

Dry rounds trigger PIVOTS, not an immediate stop — when ≥15 screened
candidates are exhausted without a delivery, or 2 consecutive rounds put
nothing through the skeleton gate, do not keep drilling the same seam.
Escalate the exploration, in order:

1. **Rotate source classes and categories** you haven't used yet this run
   (the ≤40%-per-class rule exists for this); switch prospecting queries to
   new archetype signals and new registries.
2. **Change task SHAPE, not just domain**: rotate the six-axis design signature
   (`work_surface`, `interaction`, `input_surface`, `oracle_type`,
   `verifier_type`, `failure_mode`) and prospect for a genuinely new shape.
   Do NOT fall back to the three old interaction/scale archetypes as a live
   lane: ops restoration and DB migration fell 3/3, and long-context
   cross-referencing is closed by AGENTS.md. They are eligible only through the
   single SUSPECT-dead retest slot with a materially stronger/new instance.
3. **Last resort — held §5/§4 archetype RECIPES, heavily constrained** (prefer
   staying in the bd-mgmt / interaction-scale lanes and genuinely novel shapes
   from rungs 1–2 first). §5 sim-in-verifier is allowed ONLY in the
   sim-stays-hidden-in-verifier form: the solver emits an estimate/plan and the
   simulation lives solely inside the verifier — a fresh stub-fill where the
   solver reimplements disclosed dynamics is the disclosure trap and collapses
   EASY (AGENTS.md §6). §4's terse-spec ledger recipe is closed by the
   fresh-only doctrine and pools MEDIUM at best — never promise HARD from it.
   A fresh engine in a held archetype can still satisfy
   `gallery_novelty: novel`; a reskin of an existing engine does not.

**Suspect-dead retest slot (max ONE per run):** §6 dead verdicts have tiers
(AGENTS.md §6 header) — a verdict backed only by local n≤3 probes on a single
instance is SUSPECT-dead, not CONFIRMED. Once per run, preferably during a dry
round, you may retest ONE suspect-dead seam by building a materially STRONGER
instance than the one that produced the verdict (bigger discovery surface,
deeper coupling, richer state — never a reskin of the probed instance) and
skeleton-probing it. Hold → the seam returns to live and re-enters the pool;
collapse again → upgrade the seam to CONFIRMED-dead in AGENTS.md §6. Platform
returns and pooled-N≥5 verdicts are CONFIRMED and never retested.

Log each pivot in the round report. Never lower the handover bar; never
backfill with ports. Only after ALL THREE pivots have been attempted in this
run AND two consecutive fully-pivoted rounds delivered nothing new does the
honest-exhaustion exit apply (Quota semantics above): end below quota with the
full exploration map, per-seam verdicts folded into AGENTS.md §6, and
an explicit "delivered X of <quota>; remaining yield requires either the port
lane (user request) or a genuinely new category-safe build recipe" line.

## Final handover (full quota reached, or honest-exhaustion exit)

Report in the user's language. Table: slug | category | hidden lever (one
sentence) | skeleton probe | fair probe (where each run failed) | pass-table
(solve count, union coverage, common misses, failure clusters) | category probe
| zip path | SUBMISSION.md path. Then: the exploration map
(every screened idea: assumed lever | killing gate | one-line verdict), every
pivot taken and why, and fold every durable verdict (new dead/live family)
into AGENTS.md §6/§3 per the self-update rule.
