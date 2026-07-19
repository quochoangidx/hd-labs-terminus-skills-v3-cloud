# Interaction/Scale Shape Recipe — building tasks OUTSIDE the spec-engine mold

The master collapse law was validated on minimal spec-engine tasks: anything
disclosed-and-derivable is EASY, and the fresh hidden-lever space there is
near-exhausted. This recipe covers the one seam that escapes the law's reach:
tasks whose difficulty is **breadth of discovery and interaction inside a
realistic environment**, not a hidden rule. A solver can't transcribe its way
through — it must explore, correlate state across components, and sequence
changes correctly. These shapes are also naturally category-safe
(system-administration, bd-mgmt, games are allowed slugs) and don't match the
`rust_cli`-family templates.

Cost warning: these builds are 2–5× a spec-engine build. The skeleton probe
(task-local-solve-probe, Skeleton mode) is MANDATORY before full investment,
and probe it extra strictly — an interaction task that 3/3 solvers restore is
dead exactly like a spec task.

## Difficulty doctrine (replaces the hidden-lever screen for these shapes)

A candidate holds only when ALL of:

1. **≥3 coupled causes.** The broken/target state has at least three
   interacting misconfigurations or constraints, where fixing any subset <3
   leaves the end-to-end behavior still failing — and the coupling is
   CAUSAL (fix A unmasks B; B's symptom points away from C), not three
   independent bugs side by side. Independent bugs = a checklist = EASY.
2. **Symptom ≠ site.** The observable failure surfaces in a different
   component than at least two of the causes (app 502s, but the causes are a
   permissions bit + a wrong socket path + a misordered dependency).
3. **No runbook in-image.** Comments, logs, and docs must not narrate the
   causal chain (leak-audit like any task); logs may show honest symptoms.
4. **Skeleton probe evidence**: N≥3 fresh blind solvers in the real image;
   ≥2 fail SEMANTICALLY (wrong final state), failing in DIFFERENT places.
   Both failing on the same single cause = single-lever fingerprint → the
   coupling isn't real → redesign or drop.

## Archetype 1 — multi-service ops restoration (system-administration)

- **Environment**: a realistic small stack in one container — e.g. nginx (or
  haproxy) fronting an app process managed by a supervisor (runit/supervisord
  — not systemd; containers), a database (sqlite/postgres), cron-style timed
  jobs, log rotation. Everything pinned and offline.
- **Broken state**: ≥3 coupled misconfigs across DIFFERENT layers (unit/file
  perms + socket path mismatch + proxy header/timeout + db migration
  half-applied). Verify the coupling: scripted single-fix and pair-fix
  emulations must still fail the verifier; only the full set passes.
- **Instruction framing (category-critical)**: "bring service X back to
  serving Y at Z with properties P" — an OPERATIONAL OUTCOME. Never "find
  the bug"/"debug why it fails" (→ debugging, blocked, `category_rules.md`
  R3) and never "implement/fix the handler" (→ SWE, R4). The agent OPERATES
  a system.
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
- **Category shape**: frame as operating/migrating a live store
  (system-administration) or as schema/build migration (bd-mgmt). Avoid
  "write a query that returns…" phrasing — records-in→report-out is the
  blocked data-processing shape (R2).

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

- `allow_internet = false`; every package baked into the image.
- No wall-clock dependence: pin timestamps/timezones; timed-job checks run
  the job binary directly or advance a fake clock — never sleep-and-hope.
- No race-prone asserts: poll-with-timeout helpers for service readiness
  (bounded retries), never fixed sleeps; single-CPU-safe.
- Verifier must pass oracle 20/20 consecutive local runs before shipping
  (interaction tasks flake in ways spec tasks don't — prove stability).
- Keep the verifier's own service interactions read-only where possible;
  when it must mutate (kill-restart probe), do it last and idempotently.

## Category + template hygiene

- Verbs in instruction/rubric: operate, restore, configure, migrate,
  provision, rotate — never implement/parse/debug/find.
- Rubric grades final BEHAVIOR (endpoints serve, invariants hold, jobs
  fire), never investigation steps.
- The multi-service repo furniture (configs, docs, logs) is naturally
  template-distant; keep it VARIED across tasks anyway — two tasks sharing
  the same stack layout invite a template match.
- Run `category_rules.md` on the shape before building; expected
  predictions: archetype 1/3 → system-administration, archetype 2 →
  system-administration or bd-mgmt.

## Skeleton probe adaptation

The probeable skeleton = the broken environment + instruction + a rough
end-to-end check script (curl the endpoint, query the db — a subset of the
final verifier is fine). No oracle needed yet. Score = did the solver reach
the operational outcome. Everything else in the gate pipeline (N≥3, isolated
dirs, terse prompt, semantic-failure classification) applies unchanged.
