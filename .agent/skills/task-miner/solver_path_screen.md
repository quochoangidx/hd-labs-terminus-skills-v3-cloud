# Solver-path screen

Most rejected Terminus 3 candidates collapse the same way: the solver reads the
authority, writes its own reference, differential-tests until it converges, and
both solvers pass. The existing candidate scores measure complexity and
hardcode resistance, not this path. This screen asks directly whether that path
exists, before anything is built.

It runs twice, at no extra session cost:

1. **Mining** (`task-miner`): the miner scores the candidate design and records
   `solver_path_screen` in the mined artifact. Here it ranks candidates; only a
   score of 1 rejects (see thresholds).
2. **Contract review** (`builder_certified` step 3): the reviewer's
   `contract_review` turn scores the written instruction and `environment/`,
   which is exactly the visibility the calibration below used. Here a low score
   stops the build before any verifier exists.

## Step A: pre-mortem (write it first)

In 5–10 lines: how would a strong solver (GPT-5.6 / Opus 5 class, warm
container, able to run code and write its own tests) solve this, and how would
it convince itself it was right? Name the forward model or reference it would
write, the self-check it would run, and where it would go wrong, if anywhere.

## Step B: five questions, each 1–5 (5 = strongly resists solving)

1. `reference_unreachable`: 1 = a stdlib, image tool, well-known library or a
   standard the model knows by heart computes the graded answer; 5 = no
   reachable reference.
2. `authority_incomplete_for_grading`: 1 = the visible authority determines
   every graded behaviour, so a complete reference can be written from it and
   differential-tested; 5 = graded behaviour rests on inference self-testing
   cannot confirm (silent regions, preserved shipped behaviour, native-artifact
   semantics, domain judgement). **Fairness still applies:** what the solver
   must infer has to be inferable from visible evidence. Unfairness is not
   difficulty; an ambiguity found here is a contract defect to repair, not a
   point in this score.
3. `hidden_state_not_closed_form`: 1 = the hidden quantity is linear or affine,
   or a few parameters solvable in closed form; 5 = coupled, stateful and not
   closed-form.
4. `restraint_traps`: independent sites where the natural fix must stop (a
   spec-silent sub-domain in the same function as a defect, a qualifier on a
   different parameter, shipped behaviour that must be preserved though it looks
   wrong). 1 = none; 3 = one; 5 = three or more, not all disarmed by one
   instruction sentence. See contract-closure §15. Count a trap only when it has
   the shape that held on the platform (blueprint §4.1): inside an aggregate a
   departure forces the solver to rebuild; a bare unlabelled subtype excluded only
   by a domain-word definition (two hops); one routing decision kept; derivable from
   a chain of definitions. Score a trap that fails the 0/8 screen (blueprint §4.3:
   competing positive enumeration, no definitional chain, contrary expert instinct)
   as a contract defect, not a point. Garbage-input guards, labelled type codes,
   conditions written into the rule sentence and shared-helper coupling count as
   zero.
5. `fuzz_blind_spot`: 1 = self-generated tests naturally cover the graded
   boundaries; 5 = graded cases sit in input shapes self-fuzzing under-generates.

## Step C: verdict

`self_verification_resistance` (1–5, a judgement, not an average),
`prediction` (`collapses` = both of two solvers fully solve, or `resists`),
`confidence`, `decisive_reason` (one sentence).

## Thresholds

| `self_verification_resistance` | At mining | At contract review |
|---|---|---|
| 1 | reject | stop; redesign the causal core or replace the candidate |
| 2 | deprioritize; build only if nothing ranked higher is viable | stop and redesign the core before writing the verifier, unless the reviewer names a concrete restraint trap or blind spot that it scored too low |
| 3 | build | build |
| 4–5 | prefer | build |

A redesign after contract review is a scope change made before any verifier
exists, so it costs a contract rewrite, not a receipt matrix. It is not a panel
round and it does not count toward the probe's single strengthening cycle.
One redesign is allowed; a second score of 2 or lower replaces the candidate.

## Calibration (2026-09-25, blind retro-scoring)

Four fresh Opus reviewers each scored six of 24 probed tasks, anonymised as
T01–T24. Each saw only the probed snapshot's `instruction.md` and
`environment/`, with no `task.toml`, tests, solution or outcome.

- **Labels:** "easy" means the first valid probe was 2/2 solved (14 tasks);
  "hard" means at least one semantic solver failure (10 tasks: seven at 0/2 or
  0/3, three at 1/2 or 1/3).
- **Excluded:** mixed 2/3 results and tasks rescoped between probes.
- **Separation:** AUC 0.74. The `prediction` field was right on 18 of 24
  (8 of 10 hard tasks predicted `resists`; 10 of 14 easy tasks predicted
  `collapses`).

| `svr` | easy | hard | Tasks |
|---|---|---|---|
| 5 | 0 | 1 | script-feature-extraction |
| 4 | 4 | 4 | hard: hmac-operation-isolation, make-expression-state, brep-transform-integrity, sabr-atm-cube-calibration; easy: ecc-scrub-writeback-coherence, catastrophe-layer-settlement, riscv-two-stage-page-table-walker, crispr-lineage-reconstruction |
| 3 | 2 | 4 | hard: acquisition-window-coordinates, quic-key-phase-receive-state, empty-route-delta, performance-note-lineage; easy: multiaxis-ellipsometry-stack-inversion, faulted-stratigraphic-cross-section |
| 2 | 5 | 1 | hard: head-motion-segment-alignment; easy: shifting-control-rating-reconstruction, fragmented-mp4-audio-timeline-reassembly, pcie-ats-invalidation-retirement, preisach-forc-memory-reconstruction, sqlite-wal-sector-recovery |
| 1 | 3 | 0 | easy: low-s-affine-nonce-recovery, variable-font-diacritic-interpolation, fixed-income-settlement-quote-repair |

Rejecting at `svr ≤ 2` would have dropped 8 of 14 easy tasks and 1 of 10 hard
ones, raising the share of built tasks that resist from 42% to 60%. Mean
per-question scores were higher for hard tasks on every question, most for
`reference_unreachable` (3.0 vs 2.1) and `restraint_traps` (3.3 vs 2.6).

**Limits:**
- 24 tasks, one scorer per task, and four scorers with possibly different
  calibration.
- A score of 4 does not separate the two groups (4 easy, 4 hard). Use the
  screen to cut the bottom, not to certify the top.
- Some "hard" labels may reflect contract gaps rather than genuine difficulty:
  one scorer found the script-feature contract ambiguous. That is why question 2
  carries the fairness caveat.
- The labels are local two- or three-solver probes, not platform tiers.

Recalibrate when 10 or more new probe outcomes exist: rerun this blind protocol,
update the table, and adjust the thresholds only when the evidence moves.

## Platform calibration (2026-09-26, six accepted tasks)

The first platform measurements of tasks screened this way (see
`../terminus-regular-task-authoring/references/accepted-task-blueprint.md`):

- In every recorded 8-run check, every run repaired every departure, including
  departures against remembered textbook practice. Departure count and domain
  niche add nothing to `self_verification_resistance`; only `restraint_traps` and
  its interaction with a rebuilt aggregate moved a platform result.
- Measured outcomes: crop-water ADVANCED 3/8 (two independent traps, split
  misses); royalty CORE 4/8 (one trap, a clean GPT-pass / Opus-fail split); three
  0/8 "unsolvable" returns, each from one trap every run missed. A high
  `restraint_traps` score is therefore not enough: count only traps that pass the
  0/8 screen, and prefer two independent traps of different kinds.
- Local Opus 5.5 probes are stronger than the platform's Opus 5 and read the
  silence clause differently: royalty's local pair kept a trap that platform Opus
  failed 8/8, and a local 1/2 one-trap shape went BASE 7/8 (midi). Use local
  probes to find unanimous misses (contract gaps) and collapses, not to forecast
  the tier.
- Across 12 non-trap designs (stateful coupling, evidence reverse-engineering,
  provable optimum, scale, preservation, symptom-to-root), Opus 5.5 solvers passed
  30 of 30 runs. Score such designs `svr ≤ 2` unless a concrete trap or blind spot
  is named.
