# Bounded task design and repair

Apply during candidate selection, before scaffolding, and when choosing a
panel remediation batch. Record this in existing campaign artifacts. For
`panel_ready`, materialize the same ledger in the deterministic panel-precheck
manifest; this adds no agent or semantic review cycle.

- Start with one primary domain outcome and a coherent deliverable. Identify
  the core inference/interaction, required public surfaces, visible authorities,
  and natural non-goals. Multiple functions or files are fine when they serve
  that outcome; unrelated modes, compatibility promises and side products are
  not free difficulty.
- Before scaffolding, record a compact scope ledger in the existing candidate
  artifact (do not create another review role or receipt):

  ```yaml
  primary_outcome: one observable domain result
  causal_core: the inference chain that should remain difficult
  core_obligations: [{id, contribution, authority, witness, plausible_wrong}]
  support_obligations: [{id, supplied_boundary, why_not_core}]
  non_goals: [explicitly ungraded domains or variants]
  ```

  An obligation belongs in the core only when removing it materially weakens
  the causal challenge. Domain adjacency is insufficient. Supply ordinary
  parsing, schema, serialization and defensive plumbing when they are not the
  subject of the task; otherwise narrow their accepted domain explicitly.
- Prove connectedness before scaffolding. Every core obligation must have a
  causal path to the same primary outcome and participate in a genuine
  interaction that changes the domain result before serialization. If removing
  an obligation leaves a standalone deliverable, or two subsystems meet only in
  a report/serializer, move the separable surface to supplied support/non-goal
  or reject/rescope the composite design. Use the quality-panel
  `panel_precheck.py --design-only` gate; its structural pass still needs
  semantic judgment.
- Keep a short scope ledger: retained obligation, why it matters, authoritative
  evidence, discriminating witness, and plausible wrong implementation. A
  witness may exercise multiple obligations only if its assertions actually
  distinguish each. Inventory counts do not establish this relationship.
- Choose enough cases to distinguish retained rules, boundaries, interactions
  and lifecycle promises. Test/cluster/shape counts and distribution are
  diagnostics, not minimums, ceilings or a reason to invent behavior. Do not
  pad a corpus, relabel clusters or add wrappers to satisfy old quotas.
- Prefer depth from reconstructing evidence and interacting domain constraints
  over breadth from unrelated features or exhaustive malformed-input policies.
  State arbitrary interface conventions, but do not disclose the solution.
  Preserve applicable semantic-rank and executable-mutant gates; if a candidate
  lacks natural depth, select/redesign it within authority instead of bolting on
  mechanisms. Only fresh empirical probes support the changed task's difficulty.
- Evaluate causal density, not component count: one genuine interaction and a
  natural-but-wrong path can be stronger than many independent functions. No
  minimum number of components, mechanisms, interactions or traps proves a
  tier. If the chosen campaign records those counts, treat them as diagnostics
  and reject/redesign a naturally thin candidate rather than adding scope.
- Keep expected results independently defensible. Avoid a second full solver
  in the verifier; use independent calculations, domain properties and concrete
  witnesses appropriate to the artifact. Test semantic equivalence rather than
  the Oracle's incidental representation.
- Grade exact representation only when an interoperability or domain authority
  makes it part of the outcome. Otherwise supply canonical parsing/serialization
  and compare semantics. Support plumbing must be complete, smoke-tested and
  outside the intended repair surface; a hidden CLI mode, staging rule or
  serializer prerequisite is not supplied support.

Before repair, compare shared repair, narrowing, removal, necessary expansion
and retirement using the existing root-cause procedure. Default to **no new
promises**, not no added lines: a coherent shared repair may need more code.
For every addition, identify the existing obligation it closes or the explicit
authority for expanding scope. Prefer replacing redundant evidence over
appending another exception. Remove a non-core promise only together with its
dependent implementation, grading and documentation; never delete a failing
witness for a promise that remains.

Report before/after obligations, authorities, interactions and witness coverage
alongside size changes. Growing text alone is not failure; growing independent
promises, exceptions or verifier dependencies without closing the original
invariant is a signal to switch strategy. No universal function, file, test or
800-line hard cap applies. Do not promise platform acceptance from compactness.

Keep discovery → one consolidated remediation batch → one fresh clearance.
A blocking or incomplete clearance ends that authorized cycle with a disposition,
not another renamed “final” panel. Never reuse discovery reviewers or replace a
missing independent reviewer with the orchestrator's own clearance verdict.
The required disposition is `rescope_required` when another attempt would keep
the same broad contract. Continuing requires an explicit rescope decision that
moves obligations between core, support and non-goals; adding another witness
batch to the unchanged obligation set is not a rescope.
