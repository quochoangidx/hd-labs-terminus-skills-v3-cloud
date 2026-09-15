# Interaction/Scale Shape Recipe — building tasks OUTSIDE the spec-engine mold

> **Current routing:** use `frontier_task_design_patterns.md` as the
> authoritative catalog and adaptive candidate-portfolio policy. This file keeps
> detailed historical calibration for three interaction shapes; it does not
> define a separate batch allocation or override the current catalog.

> **Historical calibration, not a Terminus 3 closure.** The exact canonical
> examples for Archetypes 1 & 2 landed in the old EASY band:
> The coupling doctrine below (≥3 causally-coupled causes ⇒ HARD) did NOT hold
> against fresh blind frontier solvers. **Archetype 1 (multi-service ops
> restoration)** — a stack with 3 GENUINELY causal-unmasking misconfigs
> (all partial-fix subsets verified failing) — was fully restored by **3/3**
> solvers in ~130s via routine `supervisorctl status`→logs→perms→socket→schema
> iteration. **Archetype 2 (order-dependent live DB migration)** — with a real
> silent double-count/ordering trap — was full-solved by **3/3** solvers who all
> applied the canonical SQLite table-rebuild recipe, which defuses the trap by
> construction. Those results are negative priors for routine supervisor
> restoration and canonical SQLite table rebuilds, not for the broader
> evidence/state/native-artifact shapes Terminus 3 now requests. Require domain
> inference and interacting semantic axes beyond the canonical recipe. An
> exploratory skeleton run may reject a weak idea, but only the frozen
> mutation-backed verifier may produce a tier signal.


The historical collapse law applies to minimal spec-engine tasks, not all
evidence-driven Terminus 3 work. This recipe covers tasks
tasks whose difficulty is **breadth of discovery and interaction inside a
realistic environment**, not a hidden rule. A solver can't transcribe its way
through — it must explore, correlate state across components, and sequence
changes correctly. The category still follows the domain evidence: a service
implementation is normally `Software / Systems`, while a logistics restoration
workflow may be `Operations / Logistics`.

Cost warning: these builds are 2–5× a spec-engine build. An exploratory
skeleton probe is optional cost control. It cannot qualify difficulty; finish
the public-surface audit, semantic mechanism map, executable mutants, Oracle,
and verifier before a counted probe.

## Difficulty doctrine (replaces the hidden-lever screen for these shapes)

A candidate holds only when ALL of:

1. **A compact causal chain.** The broken/target state has interacting
   misconfigurations or constraints where a plausible partial repair still
   leaves the end-to-end behavior failing. The coupling must be causal (fix A
   unmasks B), not independent bugs collected to increase breadth.
2. **Symptom ≠ site.** The observable failure surfaces in a different
   component from the causal repair surface (for example an app 502 caused by
   a permissions or dependency-state interaction).
3. **No runbook in-image.** Comments, logs, and docs must not narrate the
   causal chain (leak-audit like any task); logs may show honest symptoms.
4. **Mutation-backed counted-probe evidence**: in `campaign_ready`, dedicated
   subset-fix mutants prove every retained cause and interaction is
   discriminating. Then fresh counted solvers run against the frozen verifier.
   Repeated misses on one cause are a diagnostic fingerprint, not a reason to
   add unrelated causes. `panel_ready` stops before this difficulty evidence.

## Archetype 1 — multi-service restoration

- **Environment**: a realistic small stack in one container — e.g. nginx (or
  haproxy) fronting an app process managed by a supervisor (runit/supervisord
  — not systemd; containers), a database (sqlite/postgres), cron-style timed
  jobs, log rotation. Everything pinned and offline.
- **Broken state**: a compact chain of coupled misconfigurations across the
  layers naturally required by the incident (for example unit/file perms,
  socket routing, proxy behavior, or migration state). Do not add a layer to
  reach a count. Verify the claimed coupling: a natural partial repair must
  still fail the end-to-end outcome while the complete causal repair passes.
- **Instruction framing:** state the operational outcome and its evidence.
  Choose `Software / Systems` when the system itself is the domain; choose an
  `Operations` subcategory only when correctness depends on business or
  operational constraints beyond restoring software.
- **Verifier**: end-to-end behavioral checks only — HTTP responses through
  the front proxy (status/body/headers), service supervision state after a
  kill (restart policy actually works), timed-job artifacts, log invariants.
  Never assert config-file CONTENTS (that pins one solution and grades
  source shape, not behavior); assert observable behavior so any correct
  operational fix passes.
- **Oracle**: `solve.sh` as a realistic ops runbook (edit configs, restart
  services, run migration), not a patch dump.

## Archetype 2 — stateful data-store operations (db_interaction)

- **Environment**: a seeded database (prefer sqlite/postgres in-image) with
  realistic schema, constraints, triggers/views, plus an application config
  that depends on the schema.
- **Task**: a multi-step schema/data migration under stated invariants —
  e.g. split a table while preserving FK integrity and view behavior, with
  live constraints that make step ORDER matter (constraint X blocks step B
  until step A backfills; a naive order corrupts rows that the verifier
  checks).
- **Verifier**: queries against the FINAL state only — row counts,
  invariant queries, view outputs, constraint enforcement probes (INSERT
  attempts that must fail), plus preservation checks on untouched data.
  Order-dependence is graded through corrupted-state detection, never by
  watching the steps.
- **Category shape:** database internals, migrations, constraints, and recovery
  normally belong to `Software / Databases`. ETL and record-linkage pipelines
  normally belong to `Software / Data engineering`.

## Archetype 3 — long-context cross-referencing discovery

- **Environment**: a large realistic config/document tree (hundreds of
  files: service configs + docs + tickets + logs) where the answer/change
  requires CORRELATING many files — satisfying the `long_context` subtype's
  `why_not_greppable`: no single grep hits the answer; identifiers are
  aliased/indirected across files (name maps, includes, env overlays).
- **Task**: produce a change or decision that is only correct if the
  cross-references were resolved (e.g. rotate a credential everywhere it is
  REALLY used — including via 2 levels of include/alias — without touching
  look-alike unused entries; the verifier checks both the rotations AND the
  non-touches).
- **Verifier**: final-state checks over the tree + behavioral probes; the
  distractor entries that must NOT change are as load-bearing as the ones
  that must.

## Determinism rules (flakiness kills these tasks in review)

- Bake every dependency into the images. Keep `[environment].network_mode =
  "public"`; explicitly choose `[agent]` and `[verifier]` network modes, normally
  `"no-network"` unless that phase genuinely needs internet access.
- No wall-clock dependence: pin timestamps/timezones; timed-job checks run
  the job binary directly or advance a fake clock — never sleep-and-hope.
- No race-prone asserts: poll-with-timeout helpers for service readiness
  (bounded retries), never fixed sleeps; single-CPU-safe.
- Verifier must pass oracle 20/20 consecutive local runs before shipping
  (interaction tasks flake in ways spec tasks don't — prove stability).
- Keep the verifier's own service interactions read-only where possible;
  when it must mutate (kill-restart probe), do it last and idempotently.

## Category + template hygiene

- Use verbs that accurately describe the requested outcome. Do not rewrite
  verbs merely to influence category selection.
- Rubric grades final BEHAVIOR (endpoints serve, invariants hold, jobs
  fire), never investigation steps.
- The multi-service repo furniture (configs, docs, logs) is naturally
  template-distant; keep it VARIED across tasks anyway — two tasks sharing
  the same stack layout invite a template match.
- Run `category_rules.md` before building and record the exact domain pair in
  `category-screen.json`.

## Exploratory skeleton adaptation

The exploratory skeleton = the broken environment + instruction + a rough
end-to-end check script (curl the endpoint, query the db — a subset of the
final verifier is fine). No oracle is needed yet. Score only whether the solver
reaches the operational outcome. Use isolated directories, a terse prompt, and
semantic-failure classification; the active execution profile determines the
solver count. Mark it `--exploratory`; it may inform build investment but never
a tier or quota.
