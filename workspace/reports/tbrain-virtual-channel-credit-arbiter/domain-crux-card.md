# Domain-crux card (pattern-blind, written before the pattern catalog)

Slug: tbrain-virtual-channel-credit-arbiter
Date: 2026-09-28, builder F, task-batch 9 (builder_certified, CORE+ bar)

## Domain-native failure mode

A link-layer transmit arbiter with credit-based flow control per virtual channel
(VC) fails in silicon not on any one rule but where several rules meet at one
clock edge: a credit returned in the cycle a VC is out of credits, a credit
count loaded by software in the cycle the arbiter spends one, a flush arriving
while the VC also writes a byte or while the output register holds its byte,
back-pressure lifting in the cycle a new grant could load, a full buffer that
is granted and offered a byte at once. Each rule is textbook; the design bug is
an ordering choice at the coincidence (credit used before it is counted, a
pass-through ready that creates a combinational loop, a flush that eats the
same-edge write, a load that silently discards a same-cycle spend).

## What an expert has to judge

- Which values are pre-edge (registered) and which are same-edge inputs, for
  every rule, and keep all outputs Moore.
- How a run (burst of two) interacts with eligibility gaps, flushes and stalls.
- Saturating credit arithmetic when load, spend and return coincide.

## Work surface and deliverable

One synthesizable Verilog-2005 module from a numbered timing document, graded
cycle by cycle at every port under coincidence-heavy constrained-random
stimulus against an independent cycle-accurate model.

## Why difficulty survives removing incidental schema

The ports are trivial; the difficulty is the per-edge ordering across eight
interacting rules, which a solver's own bench (written from the same reading)
tends to share.
