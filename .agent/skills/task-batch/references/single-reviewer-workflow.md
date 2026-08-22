# Single-Reviewer Workflow

This is the default review geometry for new `task-batch` runs.

## Default role

- Launch exactly one fresh-context collaboration subagent as the reviewer.
- In Codex, use `gpt-5.6-sol` with medium reasoning.
- In Claude, use Opus 5 with medium reasoning.
- Do not expose `tests/`, `solution/`, hidden fixtures, campaign memory, builder
  reports, or intended mechanisms.
- Reuse the same reviewer session for exactly two review turns:
  `contract_review` and `final_review`.

The first turn reviews the task-visible goal, schemas, evidence, arbitrary
conventions, preservation promises, and 6--10 grounded witnesses. The second
turn reviews the stable task snapshot, assertion-to-source coverage,
multi-entry/stateful boundaries, semantic-equivalence policy, mutation
geometry, preservation, isolation, folder quality, and task-visible style.

## Mandatory adjudication

After each reviewer turn:

1. The persistent builder writes one `accept`, `challenge`, or `partial`
   disposition per finding, with evidence and an action.
2. The orchestrator independently writes `uphold`, `overrule`, or `narrow` for
   every finding before work continues.
3. A correct small finding is repaired and revalidated. Do not reject a
   candidate merely because the second review found a bounded repair.
4. Reject only for an unresolved repeated blocker, a required large redesign,
   a second disallowed semantic invalidation, or insufficient remaining batch
   budget.

There is no third reviewer turn. A repair after `final_review` is checked with
targeted deterministic evidence and the affected full gates; it does not buy a
new reviewer opinion.

## Optional Luna thread and optional auditor

Luna is an opt-in escalation, not the default path. Create a Codex task only
when the user explicitly requests one:

- reviewer escalation: `gpt-5.6-luna`, high reasoning;
- consolidated auditor: `gpt-5.6-luna`, max reasoning.

Follow `luna-thread-orchestration.md` and `review-role-quota-hooks.md` for any
opted-in Luna task. Record it in the ledger, but do not require a Luna receipt
when no Luna role was requested. The consolidated auditor is always optional;
mechanical folder, style, isolation, semantic-coverage, and ZIP checks remain
mandatory and are run by the orchestrator when no auditor is used.

## Direct-to-solver transition

A distinct "counted freeze" role or pause is optional. Once the exact task
snapshot passes all required pre-probe gates, run `probe.py prepare` as the
first mechanical action of the blind-solver stage and launch the solver pair.
The prepared copies and receipts must still hash-bind the exact snapshot.
Skipping the standalone freeze checkpoint never permits stale or unbound
evidence.
