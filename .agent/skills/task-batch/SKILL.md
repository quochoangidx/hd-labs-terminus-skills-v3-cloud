---
name: task-batch
description: Use when the user wants an autonomous end-to-end batch of brand-new Terminus Regular tasks delivered to submissions/ — e.g. "/task-batch", "/task-batch 3", "/task-batch 10", "tạo batch task", "chạy batch". Runs the full gate pipeline (fresh-only mining with repo prospecting → collapse-law screen → skeleton probe → build → validate → package → SUBMISSION.md) without further prompting. Args: optional delivery quota (default 4); a quota >6 is treated as a cumulative target run in sequential rounds of 3-4. Do not use for single-task work, ports (needs an explicit port request via task-language-port), or remediation of returned tasks.
---

# Task Batch — autonomous end-to-end delivery

Mission: deliver `<quota>` (default 4) brand-new Terminus Regular tasks at
≥ MEDIUM, fully autonomously. Do not ask the user questions mid-run; every
drop/redesign/lane decision is yours, governed by AGENTS.md and the skills
below. The quota is the commitment; every candidate is raw material — drop
without regret, and NEVER lower the handover bar to hit the number.

**Quota semantics — the quota is the target, honesty is the contract.** The
run ends in one of exactly two ways: (a) `<quota>` tasks in `submissions/`,
each passing all six handover conditions; or (b) the **honest-exhaustion
exit** — the full pivot ladder (Dry-round handling below) has been walked AND
two consecutive fully-pivoted rounds delivered nothing new, in which case the
run ends below quota with the complete exploration map and a per-seam verdict
report. Measured fresh HARD+category-safe yield is ~1–4 per batch (AGENTS.md
§6: "treat 10-fresh as infeasible and report honestly rather than pad") — an
under-quota exit backed by a full exploration map is a CORRECT outcome, not a
failure; padding with lowered-bar tasks or ports is the failure. Never ask the
user anything mid-run, and never lower the handover bar to hit the number. A
single round realistically yields 2–4 fresh tasks, so a quota >6 (e.g.
`/task-batch 10`) runs sequential internal rounds of 3–4; BETWEEN rounds fold
the exploration map + durable verdicts into AGENTS.md/memory/index.jsonl so
the next round mines with an expanded forbidden-zone map (this is what makes
later rounds cheaper and more accurate). Report progress after each round
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
   `task-local-solve-probe`; every probe subagent pinned `model: opus` — never
   session-inherited, `probe_model` recorded in the verdict; a PASS from a
   stronger-than-pool model is invalid EASY evidence and must be re-run on
   opus): **2 failing runs suffice and STOP probing** (early-stop, max N=3),
   under two hard riders: (a) failures are SEMANTIC —
   setup/instruction/compile/infra failures count for nothing, fix the task
   and re-probe; (b) the 2 failures land in DIFFERENT places — both runs dying
   on the same single case/convention is the single-lever fair⊥hard
   fingerprint, but at n=2 it can be coincidence on a multi-cluster task:
   spend ONE disambiguation run — same place again → DROP, a different place
   or a pass → normal scoring. Python tasks must be Hard (0/3 semantic).
3. **Pass-table pre-audit clean** (re-score stored probe diffs, no new runs):
   every case ≥1 probe passer; best union <100%; every feature cluster keeps a
   soft representative; any 0-probe cluster was oracle-authority-checked
   BEFORE any prune/disclose (`task-revise-flag-remediation` Step 1.5).
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
Shortlist the 8–12 most diverse survivors (never two from one family).

**Screen control group (mandatory per round):** the screen is a one-sentence
prediction and screen-rejects are never probed, so its false-negative rate is
invisible by construction. Advance 2 screen-FAILED candidates (diverse, not
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
2. **SKELETON PROBE GATE** (mandatory): env + instruction.md + stub + rough
   grader, N≥3 fresh blind solvers in isolated dirs outside the repo
   (`/var/tmp/probe-*`), net forbidden, every known reference lib NAMED as
   forbidden, every solver pinned `model: opus` (session-inherited stronger
   tiers invalidate EASY verdicts — `task-local-solve-probe` Core Rules).
   Running harbor oracle on a candidate with no skeleton-probe log
   is a violation — log it as a wasted build. 3/3 pass → drop, next candidate.
3. **BUILD** (`task-clone`): start from `scripts/new-task.sh <slug> <lang>
   <category>` (skeleton with the verifier/packaging hygiene pre-wired).
   Corpus soft cap ~100 curated cases, independent quirk families at ~40–80%
   per-run pass, per-case parametrized, binary 0/1 reward, soft
   representative per cluster, any case predicted <35% pass → disclose in
   one sentence or drop. Verifier hygiene: build from /app + check build
   exit status, hide expected-value corpora before running the candidate,
   run the candidate unprivileged, no exec from bare /tmp, instruction/test
   symmetry both directions. Before condition-5 validation, run
   `scripts/preflight.sh <task-dir>` — zero FAIL rows required.
4. **VALIDATE** against all six conditions. On a miss, fix per playbook (0/N →
   `task-revise-flag-remediation`, suspect the ORACLE first; single-lever
   fingerprint → DROP, never rescue; category drift → reshape the SHAPE and
   re-probe). Two fix rounds without passing → drop the task, refill the pool.
5. Keep `index.jsonl` statuses current; one-line log per drop
   (slug | killing gate | reason).

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
2. **Change task SHAPE, not just domain**: the collapse law was validated on
   minimal spec-engine tasks — move to interaction/scale-based shapes where
   difficulty comes from multi-step environment work and discovery. The
   build recipe is `task-miner/interaction_shape_recipe.md` (3 archetypes:
   multi-service ops restoration, stateful data-store operations,
   long-context cross-referencing; ≥3-coupled-causes doctrine, determinism
   rules, category framing). These are more expensive to build, so
   skeleton-probe them extra strictly before investing.
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
full exploration map, per-seam verdicts folded into AGENTS.md §6/memory, and
an explicit "delivered X of <quota>; remaining yield requires either the port
lane (user request) or a new build recipe for interaction/scale shapes" line.

## Final handover (full quota reached, or honest-exhaustion exit)

Report in the user's language. Table: slug | category | hidden lever (one
sentence) | skeleton probe | fair probe (where each run failed) | pass-table |
category probe | zip path | SUBMISSION.md path. Then: the exploration map
(every screened idea: assumed lever | killing gate | one-line verdict), every
pivot taken and why, and fold every durable verdict (new dead/live family)
into AGENTS.md §6/§3 + memory per the self-update rule.
