# Semantic Coverage Gate

Use this gate before any blind solve run whose result may count toward a
difficulty shortlist. An exploratory skeleton run may happen earlier, but it
must be labelled exploratory and can never produce an Advanced/Frontier
verdict.

The gate prevents a large fixture matrix from disguising one semantic branch.
Its unit of design is a mechanism or interaction, not a pytest row.

It also fails the opposite defect: a semantically promising task with too few
platform-visible units to diagnose coverage. Before writing the Oracle, the
verifier skeleton must already pass `verifier_architecture_check.py matrix
--allow-missing-ctrf`. The finalized gate reruns the same validator with raw
Oracle CTRF evidence.

## Required model

Create `workspace/reports/<slug>/semantic-coverage.json` with schema version 1.
Bind it to the complete task tree after the verifier and oracle are frozen.

Record:

- every public entry point, artifact, or observable surface promised by the
  instruction;
- at least three independent semantic mechanisms;
- at least two interactions joining different mechanisms;
- the platform-visible verifier unit IDs that discriminate each surface,
  mechanism, and interaction;
- one executable partial-fix mutant for every mechanism and interaction;
- an independent semantic-review transcript.

The builder drafts the manifest, implements the Oracle/verifier, executes the
mutants, and repairs pre-freeze defects. For `task-batch`, the independent
semantic judgment is one surface of the consolidated auditor session. Its
`review` identity and transcript provenance must exactly match
`pre-freeze-review.json.manual_review` and
`task-style-preflight.json.auditor`. This consolidation does not relax
independence: the auditor cannot be the builder, either fairness reviewer, or a
blind solver.

`verifier-matrix.json` uses schema version 1 and declares:

- `profile`: `cheap_deterministic` or `expensive_stateful`;
- 50–1000 platform-visible units across at least six semantic clusters for the
  cheap profile, or 20–80 scenarios across at least four clusters for the
  stateful profile;
- an exact unit-to-cluster map, at least two cross-cluster unit IDs, and at
  least two verifier shapes (unless an authority corpus with six or more
  clusters is the declared substitute);
- non-behavior IDs separately from semantic units;
- the raw Oracle CTRF path/hash, whose IDs exactly equal the declared behavior
  plus non-behavior IDs.

These are minimum resolution requirements, not a target to pad toward. Multiple
values exercising one branch increase fixture count but not semantic rank.

A mechanism is one implementation decision or domain invariant. Repeating one
decision across values, units, files, scales, or API wrappers does not create
new mechanisms. An interaction must fail only when two or more mechanisms are
combined; it is not another fixture for either mechanism alone.

Every platform-visible behavioral unit must map to at least one mechanism or
interaction. A unit may map to multiple nodes when it genuinely tests their
combination; leaving units unmapped creates probe failures that cannot be
interpreted semantically.

## Mutant evidence

Each mutant represents a plausible incomplete implementation, not an empty
solution or a wholesale breakage. Preserve its non-empty patch, materialized
task-tree hash, verifier command/exit code, raw verifier log, and CTRF under
`workspace/reports/<slug>/semantic-coverage/`. The patch must apply cleanly to
the frozen task snapshot; the validator reconstructs it and checks the hash.

The CTRF must:

- contain unique test IDs;
- contain at least one pass and one fail;
- fail every test ID claimed as the mutant's discriminating witness;
- use only IDs present in `verifier-matrix.json`.

At least one mutant must target each mechanism alone. At least one separate
mutant must target each interaction. Its expected failing witnesses must belong
to every node it claims to target. A single mutant may not satisfy every row.

## Advanced geometry

After this gate passes, freeze the task snapshot and prepare a counted probe.
For a provisional `1/3` Advanced result, both failing runs must cross at least
two semantic nodes, and their failed-node sets must differ. Two runs missing
the same single mechanism, even through dozens of fixtures, are a single-lever
lottery and do not qualify.

For a zero-solve Frontier result, retain the stricter requirements: complete
per-case union, no common miss, and de-correlated semantic-node failures.

Any change to instruction, environment, solution, tests, metadata, semantic
manifest, verifier matrix, or mutation evidence invalidates the counted probe.
Re-run this gate and prepare fresh solve copies.

## Validation

```bash
python3 .agent/skills/terminus-regular-task-authoring/scripts/semantic_coverage_check.py \
  --advanced-plus \
  workspace/tasks/<slug> \
  workspace/reports/<slug>/semantic-coverage.json \
  workspace/reports/<slug>/verifier-matrix.json
```

The validator proves receipt integrity and minimum geometry. It cannot decide
whether a mutant is professionally realistic; the independent review must make
that judgment from the visible contract, patches, and CTRF evidence.
