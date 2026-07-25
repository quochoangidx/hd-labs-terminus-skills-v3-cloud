---
name: task-revise-flag-remediation
description: Use when a Terminus task is returned with the platform flag "Some tests not passed by any agent run" (a 0/N coverage failure), when pre-auditing correlated blind spots before submission, or when the user explicitly opts into pragmatic non-Python MEDIUM salvage. Classifies each 0/N test by root cause and applies the matching fix — delete redundant group test, parametrize per-case, prune the case, disclose the convention, or ship reference data in-env — while guarding that difficulty is retained.
---

# Coverage-Flag Remediation — "Some tests not passed by any agent run"

The platform flag `❌ Some tests not passed by any agent run` is **BLOCKING**:
the task is returned until every verifier test is passed by ≥1 of the ~10
agent runs. This skill is the remediation decision tree, distilled from ~10
platform rounds across 6 tasks (html5-tree-construction, semver-range-satisfies,
maven-version-order, collation-sortkey, css-tokenization, cargo-version-req).

## The one principle behind every fix

0/N happens only for **CORRELATED** failures — every agent misses the SAME
feature. De-correlated (independent) failures get covered by the union across
runs and naturally reach ≥1/N. You cannot *guarantee* every test ≥1/N by
editing — the flag is stochastic: at N=10 runs, keeping expected-0/N below 1
across ~1500 cases requires every case be passed by >~37% of runs, which
contradicts HARD. The achievable goal is: **eliminate every correlated /
deterministic blind spot, then prune the residual low-probability tail for
margin, then re-run to confirm.**

A second principle connects this flag to `instruction_check`: the two fixes
pull against each other (disclosing a convention to fix coverage often reads
as a "spec table" to the instruction checker). The move that satisfies both:
**disclosure lives in the environment as DATA (`/app/examples.json`, a format
doc, a standard's table), not in instruction.md as prose** — see the
disclosure ladder in `terminus-regular-task-authoring` (Prompt Rules).

## Local 3-run pre-audit is not a platform 0/10 verdict

When this skill is called from `task-batch`, treat a test missed by all 3 local
solvers as a coverage-risk observation, not proof that all roughly 10 platform
solvers will miss it. Always build the per-case × per-run matrix first:

- non-Python may remain eligible through 2/3 solved; 2/3 is MEDIUM/AMBER and
  the failing run must contain at least two broad semantic clusters;
- Python still requires 0/3 solved;
- union 100% and clean fairness needs no coverage remediation;
- bounded distributed common misses that satisfy the
  `platform_candidate_coverage_risk` thresholds in `task-batch` are preserved
  unchanged and packaged separately for the wider platform sample only after
  the task's validated `instruction-sufficiency.json` maps every affected
  cluster to visible contract or training evidence;
- common misses caused by infra, oracle, contract, aggregation, or unreachable
  data follow Steps 0–2 below;
- concentrated single-lever misses or candidates outside the bounded lane are
  redesigned/dropped from the qualified pipeline, while their artifacts remain
  retained for audit rather than being silently deleted.

Do not margin-prune a task from local 0/3 evidence alone merely to manufacture
100% local union. Platform per-trial readback is stronger evidence than the
three-run pre-audit.

## Step 0 — rule out infrastructure look-alikes FIRST

Two known non-difficulty causes produce this exact flag; check them before
touching any test:

- **`/app` is not a git repo** (cloned `.git` stripped and no `git init` in the
  Dockerfile). Agents apply edits via `git apply` and self-check with
  `git diff`; patches silently fail to land and otherwise-correct agents score
  0. Fix: `RUN git init -q && git add -A && git commit …` after the final
  source COPY (see `terminus-regular-task-authoring`, Docker Rules).
- **Missing `tmux`/`asciinema` in the image** — all runs die at setup
  (`verifier_did_not_run` N/N) and every test shows 0/N while oracle passes.
  Fix the Dockerfile, not the tests.

## Step 1 — read the PER-TRIAL data, never the job summary

The LLM job summary names the wrong blind spot often enough to burn you
(semver: summary blamed the `-0` suffix, actually at 5/10; the real universal
misses were compound canonicalization conventions). Before writing any fix:

- Pull the per-test / per-trial pass table and b64-decode the actual 0/N case
  vectors.
- Cluster the 0/N cases **by feature**, not by test name — correlated blind
  spots are feature clusters (e.g. 51 of 52 cases = one tokenizer state).
- For each cluster ask: did ANY trial pass these cases *individually* even
  while failing the enclosing group test? (This decides parametrize vs prune
  below.)

## Step 1.5 — ⭐ suspect the ORACLE before you prune

N independent strong agents each reconstruct the authority; when they ALL
disagree with the oracle on the same cluster, the base rate says the oracle is
wrong, not the agents. Before any prune/disclose:

- Re-derive every expectation in the cluster by running the REAL authority (a
  live `node_modules/semver`, the actual jar, the upstream binary) — not the
  oracle, not the corpus.
- Differential-fuzz the oracle against that authority over tens of thousands of
  generated inputs. The corpus is self-consistent with the oracle's bugs *by
  construction*, so `oracle == corpus` proves nothing; the gate is
  `oracle == authority`.
- Pruning first deletes the evidence: the semver-range family's two 0/N
  clusters (numeric-after-wildcard, build-metadata-on-partial) were BOTH oracle
  bugs; the prune cleared the flag and a client reviewer returned the sibling
  task months later.

Only once the oracle is proven conformant is a 0/N cluster evidence of a real
agent blind spot — then, and only then, proceed to Step 2.

## Step 1.75 — single-lever early exit (DROP, don't remediate)

Before walking the decision tree, check the fair⊥hard fingerprint: agent runs
are NEAR-PERFECT and miss only the 0/N cluster — i.e. the task's ENTIRE
difficulty is that one boundary / convention / precedence / output-contract
fact. Then no remediation path exists: hiding it stays unfair 0/N, disclosing
or pruning it flips the near-perfect runs to 100% and the task grades EASY.
**DROP or redesign around an orthogonal implementation/reasoning challenge under
a fully visible contract immediately**
(arrhenius-clip-fit, calibration-threshold-select, hanabi, provenance-release-
gate were all late-drop lessons). This mirrors verdict case 4 in
`task-local-solve-probe` (Submit-readiness); the same fingerprint should
already have been screened at mining time (`task-miner`, Master collapse law
screen). Only tasks with a BROAD residual wall beyond the 0/N cluster continue
to Step 2.

### Explicit pragmatic MEDIUM salvage

The strict exit above is the default for autonomous batches and HARD claims.
When the user explicitly accepts a less conservative gate to avoid discarding
usable work, a non-Python task may take a bounded salvage lane:

- run one final fresh blind solve after the first valid semantic run;
- prove oracle=1 and NOP=0 and rule out setup, verifier, and authority defects;
- require the shared misses to be a small, coherent contract/reference cluster
  that Step 2 can fully disclose, split, prune, or supply as in-environment data;
- require independent graded breadth outside that cluster, established by the
  starter's broad failure, mutation coverage, or de-correlated behavior groups;
- package it as MEDIUM with a recorded amber caveat, never relabel it HARD or
  claim union-complete probe evidence.

This lane is meant for shapes such as a resolver that still grades independent
ordering, archive/group traversal, and symbol-state interactions after one
precedence/output convention is clarified. It does not rescue an all-pass
task, Python, a bad oracle, or a near-perfect single-lever task whose only wall
would disappear after remediation.

## Step 2 — classify each 0/N test and apply the matching fix

| 0/N shape | Fix | Why / proven on |
|---|---|---|
| **Group-aggregate test sitting ON TOP of per-case parametrized tests** (asserts a whole category in one function, every case also has its own test) | **DELETE the group test.** Structurally 0/N forever — no single run passes an entire hard category — and 100% redundant. Difficulty-neutral. | semver: removed 9 group tests |
| **Group test is the ONLY coverage of its cases, and the killer cases are NOT universal-miss** (per-trial data shows ≥1 agent passed them individually) | **Split the corpus per-case** (`test_case_001`, `test_case_002`, one test per vector). Coverage becomes per-case → killers covered by whoever got them right. Difficulty-neutral when `test.sh` reward is already all-or-nothing (pytest rc==0 → 1): you change the unit of *coverage*, not the win condition. Caveat: `pytest-json-ctrf` can collapse `@pytest.mark.parametrize` rows into one test with `retries`; generate unique test functions or verify CTRF reports `summary.tests == case_count`. | cargo-version-req: 3 killer P4 cases inside a 2400-case group; renju: parametrized rows collapsed in CTRF until generated test functions were used |
| **Per-case 0/N on an irreducible obscure feature** (every fresh impl will miss it; no fair way to teach it without gutting difficulty) | **PRUNE those cases from the corpus** (regenerate the `.gz`/json; keep any `corpus_present` minimum-count guard satisfied). | html5: script-data double-escape ×51; css-tokenization: 3 `url(`+ws+quote cases |
| **0/N caused by an undisclosed convention or reference-class divergence — the cases ARE the lever** (agents implement the version they memorized; the corpus is the real implementation's behavior) | **DISCLOSE, do NOT prune**: pin the exact reference release in the instruction + a few oracle-verified contrast examples (embedded at the operation definitions as contract clarification, not a mapping table). The correlated blind spot becomes a de-correlated residual tail. | maven: 894/8015 identical misses; pinned "maven-artifact 3.9.9" + contrast pair |
| **0/N because a large NON-derivable standard table is unreachable offline** (entities, Unicode data) | **SHIP the data in-env** (canonical-format file, `COPY` before the image's `git add -A`, point the instruction at the path). Fair and difficulty-neutral — mechanical data can't beat an algorithmic wall. | html5: `entities.json` (2231 entries), `whatwg-parsing.html` |
| **0/N band in chunked/monotonicity scoring** (corpus replayed in index bands) | Rebuild the oracle, **inject the common agent bug**, run the exact test harness to locate the first breaking line, then **prune just those corpus lines** — re-greens the band without deleting it. A 0/N *subset-isolator* test for an irreducible feature gets DELETED (graded difficulty survives in the general bands). | collation: Tangut-Supplement lines; deleted `test_implicit_weight_subset` |

Cross-cutting rules:

- **NEVER** delete the per-case parametrized suite or collapse the corpus to a
  few boundary cases to clear the flag — boundary cases are memorizable and
  the task flips EASY (fails the difficulty gate).
- Pruning must be **feature-cluster-complete**: a literal predicate can be
  incomplete when cases reach the blind spot transitively (collation: BMP
  compat ideographs *decompose to* astral CJK — the prune predicate had to be
  decomposition-aware). Derive the predicate from the mechanism, not the
  surface pattern.
- Pre-audit any NEWLY added vector family for likely-universal-miss shapes
  before shipping (semver pre-emptively dropped vectors even the oracle
  originally got wrong).
- **Soft-representative rule:** after any prune, every feature cluster must
  still keep ≥1 "soft" case that a majority of runs pass. A hard-cases-only
  corpus is forbidden — it maximizes 0/N exposure on the next re-run and trips
  anti-hardcoding minimum-coverage guards. The trimming direction is always
  pass-table-driven; never "drop the easy cases to keep the hard ones" (easy
  cases ARE the coverage that keeps the flag from firing).

## Step 3 — margin-prune the ≤2/N tail

The flag is stochastic across re-runs: a case at 1/N has ~35% chance of
flipping to 0/N on the next sampled run, 2/N ~11%, 3/N ~2.8%. After fixing the
clusters, prune observed ≤2/N cases from the last report for margin — but do
NOT prune the whole ≤2/N tail on the FIRST fix (pkgconf 2026-07-19, AGENTS.md
§3): that tail can nearly equal the best agent's residual failure budget, and
sweeping it risks flipping HARD to EASY. Prune conservatively, keep softer
representatives of each cluster, and lean on disclosure first.
Don't chase ≤3/N unless forced — over-pruning the hardest cases raises the
best-run ceiling toward 100% and risks the difficulty gate. Per-case counts in
one report are a noisy sample; this is probabilistic de-risking, not a
guarantee.

Exception: do not margin-prune the ≤2/N tail when the best agents are already
near-perfect and those low-pass cases are their only remaining misses. In that
shape, prune only the true 0/N rows and leave the 1/N or 2/N rows as the
residual wall; removing them can turn many failed trials into full passes and
collapse HARD to EASY. Proven on renju-forbidden-move: after per-case CTRF,
three 0/10 rows were pruned while two 1/10 rows were deliberately retained.

Index bookkeeping when pruning repeatedly: report indices map to the current
corpus via `cur = old if old < deleted_idx else old - 1` per prior deletion.

## Step 4 — difficulty-retention guards (run after EVERY edit)

- Oracle must still pass **100%** (pruning a subset of a passing set is safe;
  anything else is a bug).
- Nop/stub must still fail.
- Best agent's residual failure count must remain ≫ what you removed (html5:
  pruned 11, best run still failed ~76 others) — verify no run can flip to
  100%.
- Difficulty is *guaranteed* retained without re-probing when the binding
  constraint is an untouched graded band or an untouched universal algorithmic
  wall (edits only raise pass rates; if ≤1 run passes that band, the task
  stays ≤1/N overall).
- Re-zip after edits; re-run the platform check — it is the only source of
  truth for the real pass fraction.

## Step 5 — validate offline before spending a platform run

Build a **best-agent emulation**: the oracle with the common agent bug
injected (corrupt exactly the feature the report says everyone misses). After
your fix, the emulation must pass the previously-0/N tests (proves the flag
will clear) while other known-buggy variants still fail (proves the surviving
traps hold). This replaces a blind platform re-run for the *flag* question;
the *difficulty fraction* still needs the platform.

For disclosure fixes, the cheap reachability proof: resume the best stored
probe solver with just the newly disclosed delta facts and confirm it can now
reach full-pass.

## Design-time prevention (cheaper than any of the above)

- Structure verifiers **per-case parametrized or graded bands** from day one;
  no monolithic all-N-cases functions, no group-aggregate tests on top of
  per-case ones (`lever_patterns.md` L1 step 6).
- Target each quirk family at ~40–80% expected per-run pass rate; a case you
  predict <~35% of runs will pass is a 0/N candidate — disclose or drop it at
  design time.
- Run the **coverage pre-audit** in `task-local-solve-probe`: score the blind
  probe solvers' diffs per-case against the corpus; any case passed by NO
  probe run is a correlated-blind-spot candidate before the platform ever
  sees it.
