---
name: task-revise-flag-remediation
description: Use when a Terminus task is returned with the platform flag "Some tests not passed by any agent run" (a 0/N coverage failure), or when pre-auditing a conformance-style task for correlated blind spots before submission. Classifies each 0/N test by root cause and applies the matching fix — delete redundant group test, parametrize per-case, prune the case, disclose the convention, or ship reference data in-env — while guarding that difficulty is retained.
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
**DROP or redesign around an orthogonal undisclosed second lever immediately**
(arrhenius-clip-fit, calibration-threshold-select, hanabi, provenance-release-
gate were all late-drop lessons). This mirrors verdict case 4 in
`task-local-solve-probe` (Submit-readiness); the same fingerprint should
already have been screened at mining time (`task-miner`, Master collapse law
screen). Only tasks with a BROAD residual wall beyond the 0/N cluster continue
to Step 2.

## Step 2 — classify each 0/N test and apply the matching fix

| 0/N shape | Fix | Why / proven on |
|---|---|---|
| **Group-aggregate test sitting ON TOP of per-case parametrized tests** (asserts a whole category in one function, every case also has its own test) | **DELETE the group test.** Structurally 0/N forever — no single run passes an entire hard category — and 100% redundant. Difficulty-neutral. | semver: removed 9 group tests |
| **Group test is the ONLY coverage of its cases, and the killer cases are NOT universal-miss** (per-trial data shows ≥1 agent passed them individually) | **PARAMETRIZE the corpus per-case** (`test_case[group:name]`, one test per vector). Coverage becomes per-case → killers covered by whoever got them right. Difficulty-neutral when `test.sh` reward is already all-or-nothing (pytest rc==0 → 1): you change the unit of *coverage*, not the win condition. | cargo-version-req: 3 killer P4 cases inside a 2400-case group |
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
clusters, prune the observed ≤2/N cases from the last report for margin.
Don't chase ≤3/N unless forced — over-pruning the hardest cases raises the
best-run ceiling toward 100% and risks the difficulty gate. Per-case counts in
one report are a noisy sample; this is probabilistic de-risking, not a
guarantee.

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
