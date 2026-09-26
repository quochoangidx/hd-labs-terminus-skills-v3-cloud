# Single-Reviewer Workflow

This is the default review geometry for new `task-batch` runs. Under
`builder_certified` the skeleton probe (step 4a) runs between `contract_review`
and the verifier build, the builder's scripted Sound Verifier sweep (step 5b)
follows the closure gates, and the difficulty rescore and narrow pre-submission
panel close the route (steps 7–8).

## What the one reviewer is for

The deterministic gates already cover everything a script can decide: coverage
bookkeeping, isolation, determinism, receipt integrity, and — through
`expected_source` and `independence_check.py` — the circularity that would
otherwise make Oracle=1 meaningless.

What no script decides is whether a second competent engineer would read the
contract the same way. That needs someone who has **not** seen the tests or the
solution, which is exactly the `contract_review` visibility below. Protect that
blindness: a reviewer who has read the answer resolves ambiguity without noticing
it, and then cannot see the ambiguity at all.

Under `builder_certified` the reviewer's turns are the only semantic judgement
before closure, and the pre-submission panel (step 8) reads a snapshot they have
already cleaned, so do not skip the second turn or fold it into the first.

## Default role

- Launch exactly one fresh-context collaboration subagent as the reviewer.
- In Codex, use `gpt-5.6-sol` with medium reasoning.
- In Claude, use Opus 5 with medium reasoning.
- Do not expose `tests/`, `solution/`, hidden fixtures, campaign memory, builder
  reports, or intended mechanisms.
- Reuse the same reviewer session for the two required review phases:
  `contract_review` and `final_review`. Corrective rechecks remain in that
  session and have no turn or remediation cap.

The first turn runs as soon as the authority and instruction exist, before any
verifier is written (`builder_certified` step 3). Its packet is `instruction.md`
plus `environment/`, so its findings are repaired while repairs are cheap. It
reviews the task-visible goal, schemas, evidence, arbitrary
conventions, preservation promises, and 6--10 grounded witnesses that the
reviewer works out by hand from the contract (no verifier exists yet). It also
returns the [solver-path screen](../../task-miner/solver_path_screen.md): a
pre-mortem of how a strong solver would solve and self-check the task, the five
scores and `self_verification_resistance`. The screen was calibrated on exactly
this visibility. The second
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

There is no second reviewer identity under `builder_certified`. The former
adversarial verifier pass was replaced on 2026-09-26 by the builder's scripted
Sound Verifier sweep (`execution-profiles.md` step 5b), which covers the classes
every accepted task's panel returns were about at no session cost.

## Auditor

`campaign_ready` only. `builder_certified` does not run one: its deterministic
receipts cover what a full-visibility auditor would check, and the reviewer above
covers what receipts cannot. Say so in the report rather than recording a missing
auditor as an expected failure.

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
