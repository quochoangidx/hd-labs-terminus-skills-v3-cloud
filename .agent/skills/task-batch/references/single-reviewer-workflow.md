# Single-Reviewer Workflow

This is the default review geometry for new `task-batch` runs.

## Default role

- Launch exactly one fresh-context collaboration subagent as the reviewer.
- In Codex, use `gpt-5.6-sol` with medium reasoning.
- In Claude, use Opus 5 with medium reasoning.
- Do not expose `tests/`, `solution/`, hidden fixtures, campaign memory, builder
  reports, or intended mechanisms.
- Reuse the same reviewer session for the two required review phases:
  `contract_review` and `final_review`. Corrective rechecks remain in that
  session and have no turn or remediation cap.

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
4. Continue correction and recheck without an internal attempt limit. Reject
   only for an intrinsic fairness defect, unreachable authority, fundamental
   redesign, or an evidence-backed inability to make further progress.

A repair after `final_review` is checked with targeted deterministic evidence,
the affected full gates, and a recheck by the same reviewer when semantic
judgment is involved. Do not launch a second reviewer identity merely to obtain
a different opinion.

## Mandatory auditor

After final-review remediation and the complete mechanical Oracle/NOP/quality
gates pass, launch exactly one distinct independent auditor. Use
`gpt-5.6-sol` medium in Codex or Opus 5 medium in Claude. The auditor may inspect
the task, verifier, Oracle, semantic coverage, isolation evidence, and folder
quality, but not campaign memory or the builder's intended answer. Audit
findings return to the same builder and the same auditor rechecks them until
green or fundamentally blocked; there is no remediation-count limit.

## Direct-to-solver transition

A distinct "counted freeze" role or pause is optional. Once the exact task
snapshot passes all required pre-probe gates, run `probe.py prepare` as the
first mechanical action of the blind-solver stage and launch the solver pair.
The prepared copies and receipts must still hash-bind the exact snapshot.
Skipping the standalone freeze checkpoint never permits stale or unbound
evidence.
