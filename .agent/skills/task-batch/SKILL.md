---
name: task-batch
description: Use when the user wants an autonomous end-to-end batch of brand-new Terminus Regular tasks delivered to submissions/ — e.g. "/task-batch", "/task-batch 3", "tạo batch task", "chạy batch". Runs the full gate pipeline (fresh-only mining → collapse-law screen → skeleton probe → build → validate → package → SUBMISSION.md) without further prompting. Args: optional delivery quota (default 4). Do not use for single-task work, ports (needs an explicit port request via task-language-port), or remediation of returned tasks.
---

# Task Batch — autonomous end-to-end delivery

Mission: deliver `<quota>` (default 4, hard range 2–6) brand-new Terminus
Regular tasks at ≥ MEDIUM, fully autonomously. Do not ask the user questions
mid-run; every drop/redesign/lane decision is yours, governed by AGENTS.md and
the skills below. The quota is the commitment; every candidate is raw material
— drop without regret, and NEVER lower the handover bar to hit the number.

Environment notes: harbor + Docker work locally (~3 min/oracle run) and need
no LLM; harbor LLM / stb are geoblocked from VN — run every difficulty and
category probe yourself with fresh subagents (Agent tool), never harbor LLM.

## Handover conditions — a task counts ONLY when ALL six hold

1. harbor oracle = 1.0 and nop = 0.0.
2. **Difficulty** — fair blind probe (inside the task image, `--network none`,
   terse prompt, no hints, scored by differential per
   `task-local-solve-probe`): **2 failing runs suffice and STOP probing**
   (early-stop, max N=3), under two hard riders: (a) failures are SEMANTIC —
   setup/instruction/compile/infra failures count for nothing, fix the task
   and re-probe; (b) the 2 failures land in DIFFERENT places — both runs dying
   on the same single case/convention is the single-lever fair⊥hard
   fingerprint → DROP, not deliver. Python tasks must be Hard (0/3 semantic).
3. **Pass-table pre-audit clean** (re-score stored probe diffs, no new runs):
   every case ≥1 probe passer; best union <100%; every feature cluster keeps a
   soft representative; any 0-probe cluster was oracle-authority-checked
   BEFORE any prune/disclose (`task-revise-flag-remediation` Step 1.5).
4. **Blind category probe** 2–3 runs (fresh subagent; de-contaminated packet —
   only instruction.md + environment file tree + README + rubric, copied
   outside the repo; the subagent must NOT read AGENTS.md/CLAUDE.md/memory):
   no run predicts a blocked slug; majority matches the declared category.
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

## Loop (repeat until quota or a stop condition)

1. **MINE** fresh per the doctrine; claim slugs (`tbrain-<problem-slug>`).
2. **SKELETON PROBE GATE** (mandatory): env + instruction.md + stub + rough
   grader, N≥3 fresh blind solvers in isolated dirs outside the repo
   (`/var/tmp/probe-*`), net forbidden, every known reference lib NAMED as
   forbidden. Running harbor oracle on a candidate with no skeleton-probe log
   is a violation — log it as a wasted build. 3/3 pass → drop, next candidate.
3. **BUILD** (`task-clone`): corpus soft cap ~100 curated cases, independent
   quirk families at ~40–80% per-run pass, per-case parametrized, binary 0/1
   reward, soft representative per cluster, any case predicted <35% pass →
   disclose in one sentence or drop. Verifier hygiene: build from /app +
   check build exit status, hide expected-value corpora before running the
   candidate, run the candidate unprivileged, no exec from bare /tmp,
   instruction/test symmetry both directions.
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

## Budget & stop conditions

Stop short of quota only when ≥15 screened candidates are exhausted OR 3
consecutive mining rounds put nothing through the skeleton gate. Then hand
over what passed plus an analysis of why the quota was infeasible and which
territory to try next. Never lower the bar; never backfill with ports.

## Final handover

Report in the user's language. Table: slug | category | hidden lever (one
sentence) | skeleton probe | fair probe (where each run failed) | pass-table |
category probe | zip path | SUBMISSION.md path. Then: the exploration map
(every screened idea: assumed lever | killing gate | one-line verdict), and
fold every durable verdict (new dead/live family) into AGENTS.md §6/§3 +
memory per the self-update rule.
