# Domain-crux card (pattern-blind) — tbrain-sealed-source-decay-inventory

Written 2026-09-26 before reading task-miner/frontier_task_design_patterns.md.

- Natural domain failure mode: a radiation-safety officer's inventory tool
  reports wrong current activities for sealed sources (decay applied with the
  wrong time base, wrong half-life unit, daughters double counted or dropped),
  so storage-location sums, exempt/leak-test flags and decay-to-disposal
  eligibility are wrong on the survey report. Physically: A(t) = A0 * 2^(-dt/T½),
  secular-equilibrium daughters carry the parent's activity, and whether they
  enter a regulatory sum is a definitional matter, not a physics one.
- Native work surface / artifact: a small Python inventory package that reads a
  source inventory (CSV/JSON) and a survey date, and writes a per-source and
  per-location survey report (JSON). The authority is the lab's numbered source
  inventory manual shipped in the environment.
- Why difficulty survives removing incidental schema: the hard part is which
  activity figure each rule is defined on (parent only vs parent plus
  equilibrium daughters; recorded vs decayed; active vs disposed entries) and
  where a decay law with a signed interval is still valid (reference date after
  survey date). Those are definitional chains through the manual, not field
  names or ordering.
- Two natural but wrong repairs on distinct surfaces:
  1. Decay surface: "fix" a negative elapsed interval by clamping it to zero or
     rejecting it (the manual's formula is valid for back-correction; the shipped
     signed code is right) — a guard where none belongs.
  2. Aggregation surface: rebuild the location sum by summing every listed row
     (including disposed/transferred entries, or including equilibrium daughter
     activity) because the rebuilt sum "should use total activity" — wrong by the
     manual's definition of "possessed activity".
- Direct observable an isolated verifier can discriminate: the emitted report
  JSON — per-source current activity (Bq, rounded per manual), per-source flags
  (exempt, leak-test due, disposal-eligible), per-location summed possessed
  activity and fraction-of-limit — compared to an independent model on hidden
  inventories.
