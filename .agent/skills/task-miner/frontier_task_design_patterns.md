# Frontier Task Design Pattern Catalog

Use this catalog for every new Terminus 3 mining round. It describes current
task-design shapes that are plausible against frontier agents; it does not
assign a tier. Only frozen, mutation-backed probes and platform trials provide
difficulty evidence.

## Portfolio allocation

Classify every candidate that passes the mining plan gate into exactly one
track:

- `established`: apply one or more `P*` patterns below without changing the
  pattern's causal topology.
- `derived`: create an experimental pattern by transforming or composing the
  established patterns. A different domain, language, narrative, repository,
  or file format alone is a reskin and does not qualify.

For a requested batch of `N`, use the nearest whole-task 80/20 allocation:

```text
derived_target = floor(0.20 * N + 0.5)
established_target = N - derived_target
```

This gives 2 established + 1 derived for a three-task batch and 4 + 1 for a
five-task batch. A rejected slot must be replaced by a candidate from the same
track. Enforce the allocation both on the initial post-mining build pool and on
the final accepted batch.

## Established-pattern rules

An established candidate must record:

- `track: established`;
- one or more pattern IDs from this catalog;
- a candidate-specific causal graph;
- at least three semantic mechanisms and two genuine interactions for an
  Advanced+ target;
- a dedicated plausible partial-fix mutant for every mechanism and interaction;
- why the candidate is not a previously shipped instance of the same pattern.

Pattern IDs are design priors, not difficulty labels. Do not copy an example's
domain, repository, artifact, or verifier corpus merely because it appears
below.

## Derived-pattern rules

A derived candidate must record:

- `track: derived` and a candidate-local ID such as `X-delayed-dual-control`;
- one or more parent `P*` IDs;
- the transformation operator, such as composition, inversion, delayed
  feedback, partial observability, cross-representation, exogenous
  perturbation, or adversarial role reversal;
- concrete deltas in at least two of: causal topology, work surface, verifier
  architecture, and expected failure geometry;
- a falsifiable explanation of why the shape is not equivalent to a parent;
- the same evidence-inferability, verifier-breadth, mutation, and frozen-probe
  gates as established candidates.

A derived candidate may instantiate one of the registered experimental
prototypes below or define a candidate-local `X-*` ID. A registered prototype
is a reusable research hypothesis, not an established pattern: the candidate
must still record its own transformation, material deltas, causal graph, and
non-equivalence rationale. It counts toward the derived 20% allocation.

Keep a derived pattern experimental after one candidate. Promote it into the
established `P*` catalog only after either (a) two structurally different
applications in different domains produce valid Advanced/Frontier evidence, or
(b) one task is platform-confirmed Frontier and a fresh independent review
finds the pattern generalizable. Never promote on an exploratory probe.

## Frontier-stability mining gates

Apply these gates before scaffolding every new Advanced+ candidate. Pattern
membership alone never clears them.

1. **Typed topology:** record exactly one dominant topology, optionally one
   orthogonal secondary topology, and at most one amplifier or delivery
   envelope. The dominant ID must be an applied `P*` ID for an established
   candidate or its `X-*` ID for a derived candidate. Use only `P4` or `P6` in
   the amplifier/envelope slot.
2. **Anti-retrieval:** search the issue wording, distinctive failures, public
   symbols, release history, and version diffs. Record the queries and public
   artifacts checked. Reject when one public artifact already implements two
   or more planned mechanisms or any genuine interaction. An upstream fix may
   remain a substrate only when the new task's core topology is not that patch.
3. **Orthogonal natural-fix traps:** name at least two reasonable
   implementations that are wrong for different semantic reasons. Their
   semantic nodes, repair surfaces, and planned witness IDs must be distinct;
   their witness sets must not overlap. Explain why one central helper or
   recovered mapping cannot repair both.
4. **Fast semantic loop:** retain a deterministic local edit/measurement loop.
   Search friction, cold builds, timeout pressure, and inaccessible evidence
   cannot substitute for the gates above.

The schema-v2 pattern-mix manifest stores these facts under
`frontier_stability`, including the planned mechanism and interaction IDs that
retrieval overlap and trap nodes reference. Schema v1 remains readable only for
historical evidence; never create a new v1 manifest.

## P1 — `coupled-invariant-reconstruction`

- **Intent:** make the solver reconstruct a non-obvious domain invariant that
  spans several components, rather than patch the visible symptom locally.
- **Required shape:** the symptom occurs away from at least one cause; three or
  more mechanisms constrain one another; at least two plausible local fixes
  pass some tests and fail different interaction tests.
- **Strong surfaces:** optimizers, type systems, schedulers with policy state,
  cache eviction/rebalancing, storage engines, compilers, and numerical engines.
- **Verifier:** primary behavior, preservation, and secondary state/plan/metric
  checks; hidden cases vary interactions under the same visible model.
- **Reject when:** the fix becomes an obvious guard after locating one function,
  or the mechanisms are independent checklist items.

## P2 — `crash-recovery-state-machine`

- **Intent:** require correctness across partial progress, interruption,
  restart, replay, retry, rollback, and finalization.
- **Required shape:** at least one durable state transition; multiple fault
  points; idempotent replay; an ordering interaction; preserved normal flow.
- **Strong surfaces:** journals, migrations, checkpoint/resume, deployment
  rollout, queues, workflow engines, package transactions, and replicated state.
- **Verifier:** deterministic fault injection and final-state validation across
  20–80 stateful scenarios; no sleeps or flaky races.
- **Reject when:** a canonical recipe such as a routine SQLite table rebuild
  neutralizes every trap by construction.

## P3 — `distributed-evidence-diagnosis`

- **Intent:** make the graded model inferable only by correlating several
  authentic evidence sources.
- **Required shape:** evidence is distributed across traces, config, schema,
  current state, design files, or domain records; no single grep or document
  states the answer; distractors remain realistic.
- **Strong surfaces:** root-cause analysis, scientific interpretation,
  forensics, data lineage, operational reconciliation, and multi-service bugs.
- **Verifier:** test the repaired behavior or reconstructed artifact on fresh
  evidence instances, never an exact prose diagnosis.
- **Reject when:** identifiers merely form a long lookup chain or environment
  docs narrate the causal chain.

## P4 — `secondary-observable-correctness`

- **Intent:** keep the primary output plausible or correct while grading a
  consequential secondary observable.
- **Required shape:** correctness depends on a plan, cost, cardinality, memory,
  provenance, determinism, durability, timing policy, or resource decision that
  cannot be faked by printing a claimed value.
- **Strong surfaces:** query plans, compiler metadata, cache policy, build
  provenance, scheduling, numerical stability, and resource accounting.
- **Verifier:** independently derive the secondary observable from real runtime
  behavior or a native artifact and retain primary-output preservation checks.
- **Reject when:** the observable is a self-reported metric or one arbitrary
  exact constant.

## P5 — `native-semantic-artifact`

- **Intent:** require a real domain-native deliverable whose semantics matter,
  not a cosmetic JSON description or screenshot.
- **Required shape:** at least two meaningful semantic layers or consumers;
  artifact validity, behavior, and preservation constraints interact.
- **Strong surfaces:** ELF/WASM/package archives, database snapshots, ML
  checkpoints, CAD/RTL outputs, media timelines, signed manifests, and compiled
  plans.
- **Verifier:** parse or execute the artifact through independent consumers and
  compare each to external source evidence; do not accept self-consistency
  between two solver-produced representations as ground truth.
- **Reject when:** the task is a format conversion with a reachable one-command
  authority or the artifact is only superficially validated.

## P6 — `holistic-all-pass-deliverable`

- **Intent:** require the complete engineering outcome rather than only the
  central function.
- **Required shape:** functional correctness interacts with at least two of
  compatibility, recovery, provenance, determinism, safety, performance, or
  migration behavior. Every axis must be objectively gradeable.
- **Strong surfaces:** production-ready feature changes, cross-version
  migrations, packaging, data pipelines, and safety/performance work.
- **Verifier:** all-pass across independent behavioral axes with semantic
  equivalence allowed; use deterministic checks, not taste-based style grading.
- **Reject when:** extra axes are lint/docs busywork or hidden implementation
  preferences. Holistic does not mean vague.

## P7 — `adversarial-strategy-search`

- **Intent:** require a strategy robust to opponents, exploit attempts, or
  adaptive perturbations rather than a single procedural implementation.
- **Required shape:** several independent attack/opponent families; legitimate
  behavior to preserve; no one guard blocks the whole space.
- **Strong surfaces:** sandbox hardening, protocol abuse, game strategy,
  scheduling under adversarial load, and resilient parsers only when the fix is
  multi-vector and architectural.
- **Verifier:** held-out opponents or perturbations from the same visible rules,
  plus preservation and anti-hardcoding tests.
- **Reject when:** the task is vague "harden this", a single CVE guard, or needs
  a live target/network.

## P8 — `exogenous-state-reconciliation`

- **Intent:** require the solver to reconcile state changes not caused by its
  own actions.
- **Required shape:** deterministic external events interleave with agent-owned
  transitions; stale observations, retries, and convergence interact; final
  correctness cannot assume a static world.
- **Strong surfaces:** replicated services, inventory/logistics, market or
  claims reconciliation, device/robot state, event-sourced systems, and
  incremental data processing.
- **Verifier:** replay a fixed event schedule with varied seeds/orderings and
  validate convergence, preservation, and provenance.
- **Reject when:** wall-clock timing, real external services, or random races
  create the apparent difficulty.

## Registered experimental prototypes

These `X-*` prototypes make underrepresented frontier-hard topologies available
for deliberate trials. They remain `track: derived`; appearing here does not
make them established or provide difficulty evidence.

## X-cross-layer-feature-completion — `cross-layer-feature-completion`

- **Parents:** `P1` coupled invariants and `P6` holistic delivery.
- **Transformation:** lift a local invariant repair into a short product outcome
  whose implementation crosses a real repository dependency graph.
- **Required shape:** the outcome needs coordinated changes across at least
  three meaningful layers, such as public API, domain implementation,
  persistence/configuration, compatibility, or downstream consumption. At
  least two natural partial implementations must complete different layer
  subsets and fail on disjoint end-to-end witnesses.
- **Strong surfaces:** multi-service or multi-package features, protocol or
  storage evolution, compatibility-sensitive product changes, and compiler or
  build features with several consumers.
- **Verifier:** exercise the feature end to end and independently preserve each
  affected layer's existing contract. Accept alternative dependency-graph
  implementations that produce equivalent behavior.
- **Reject when:** the apparent breadth is file count, generated scaffolding,
  lint/docs work, or one central helper change that mechanically fixes every
  layer.

## X-dynamic-authority-reconciliation — `dynamic-authority-reconciliation`

- **Parents:** `P3` distributed evidence and `P8` exogenous reconciliation.
- **Transformation:** make later evidence change which visible source is
  authoritative, forcing invalidation and reconstruction of previously derived
  state rather than mere convergence after external events.
- **Required shape:** at least two visible evidence sources have inferable
  precedence or provenance; a deterministic later observation supersedes or
  conflicts with an earlier conclusion; stale downstream decisions must be
  revoked; and completeness must be rechecked across multiple affected items.
- **Strong surfaces:** incident response, data lineage, configuration control
  planes, reconciliation pipelines, scientific evidence revision, and
  inventory or claims adjudication.
- **Verifier:** replay a fixed evidence/event schedule, then validate the final
  authority choice, provenance, absence of stale derived decisions, and
  completeness. Vary schedules and values under the same visible authority
  model.
- **Reject when:** it is only an event handler or retry loop (use `P8`), or when
  priority between sources is an arbitrary hidden policy.

## X-closed-loop-empirical-convergence — `closed-loop-empirical-convergence`

- **Parents:** `P3` distributed evidence, `P4` secondary observables, and `P5`
  native semantic artifacts.
- **Transformation:** turn static inference into a bounded loop in which the
  solver forms competing hypotheses, chooses informative measurements, updates
  its model, and converges on a validated artifact.
- **Required shape:** several plausible hypotheses fit the initial evidence;
  available experiments have different information value; later choices must
  depend on observed results; and the budget prevents exhaustive enumeration
  while still permitting a reliable strategy.
- **Strong surfaces:** scientific reproduction, ML engineering, performance
  diagnosis, calibration, numerical modeling, and hardware characterization.
- **Verifier:** use a deterministic simulator, fixed dataset, or replayable
  measurement harness; enforce the experiment budget; and grade held-out
  artifact behavior plus independently observable decisions, never a claimed
  narrative of the process.
- **Reject when:** brute force fits inside the budget, one command exposes the
  optimum, stochastic infrastructure determines success, or a hidden metric
  supplies the difficulty.

## Cross-pattern construction rules

Regardless of pattern:

1. Assign one dominant causal topology, optionally one orthogonal secondary
   topology, and at most one amplifier or delivery envelope. Pattern count is
   not semantic rank; `P4` is usually an amplifier and `P6` an envelope.
2. Keep the goal, public interfaces, artifact paths, safety constraints, and
   arbitrary exact conventions explicit.
3. Let domain semantics and causal relations be inferred only from reachable,
   agent-visible evidence.
4. Hidden tests may vary values, sequences, layouts, combinations, and
   metamorphic relations under the same model; they may not add policy.
5. Prefer delayed or cross-layer feedback, but keep a fast deterministic edit
   and verification loop. Slow infrastructure is not difficulty.
6. Isolate verifier assets and expected outputs. Treat reward-hacking probes as
   evaluator QA, not as task difficulty evidence.
7. Reject a provisional high-tier result when all failures reduce to one shared
   semantic node, even if that node appears in many fixtures.
8. Treat an exact public patch that clears at least two mechanisms or any
   genuine interaction as retrieval, not reasoning evidence. Transform the
   task before building or reject it.

## Anti-patterns

- repo size, prompt length, file count, or human time as the main lever;
- clean standard/library transcription, parser/codec work, or a reachable
  authority without a separate interaction challenge;
- hidden constants, exact strings, tiebreaks, or policies that cannot be
  inferred;
- infrastructure failure, OOM, timeout, missing dependencies, or flaky races;
- tests that pin a private implementation instead of observable semantics;
- self-referential artifact validation;
- famous public issues or benchmark resources likely present in training data;
- fixture multiplication standing in for mechanism rank;
- a single correlated boundary family presented as broad hardness.
