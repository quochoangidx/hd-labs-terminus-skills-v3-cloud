# Contract review r1: adjudication (tbrain-fleet-tire-tread-compliance)

Reviewer C, svr 2 (advisory; the skeleton pair decides), no blocking finding.

| Finding | Builder | Orchestrator | Repair |
|---|---|---|---|
| F1 should-fix: wear-bar reading, 4.1 "the depth of its latest reading" reads as governing every reading (5 / 8 / 0) | accept | uphold | Narrowed the definitions, adding no sentence that names the case. 3.1 now defines "a measurement's measured depth"; 2.3 uses the first reading's measured depth; 4.1 is "the measured depth of its latest reading". Every figure sections 4-5 take now comes from a term whose domain is measurements, so a wear-bar reading's value flows only through today's code (the reach rule). Signpost not reinforced. |
| F2 should-fix: non-fresh tire worn/distance | accept as intended trap | fair trap, no change | none |
| F3 polish: first depth above new | accept | polish | 1.5 limit: the first reading's figure plus its gauge offset is never above the new depth. model.within_limits and gen.py enforce it. |
| F4 polish: negative worn/rate | no change | not raised | 1.1 already settles negative halves |
| F8 polish: list order | accept | polish | 1.5 now reads "listed in date order" |

Package code, solution/fix.patch and solution/model.py figures are unchanged; only the standard's wording, one section-1 limit and the model's limits check changed.
Receipts rerun: receipts/panel-precheck-design-only.txt (pass, snapshot 10b11ab8...), instruction-preflight.txt (OK),
receipts/fuzz-model-vs-oracle.json (pass), receipts/score-skeleton-validation.json (pass, image
tbrain-fleet-tire-tread-compliance:skeleton2 sha256:1bc813e2d9bbe1c7d5fd8a3de06d4a5a5c45599e5d47866c560ca6b0e8069a67).

## Strengthening after skeleton cycle-1 (2/2, both 11/11)

Orchestrator direction: subject-membership traps collapse on claude-opus-5; rebuild both traps as value-level / shared-helper traps.
- Old T1 (wear-bar reading) and T2 (part-worn tire) are now governed and their inputs are outside section 1: every reading shows 10-320 tenths and takes its offset (3.1); every tire's first depth is 0-10 tenths below new, and wear is measured from new (4.2). Definitions 2.1 (measurement) and 2.3 (fresh) are removed.
- New D3: drive and trailer removal depth 30 tenths (shipped 32 everywhere), with steer at 40.
- New T1: km_left (README only) keeps today's half-even rounding through the shared rounding.divide.
- New T2: regroove (README only) keeps today's floor REMOVAL(32)+20 = 52.
- Instruction softened: "Take each rule of the standard exactly as far as it reaches" became "Change only what the standard governs". Envelope and symptoms updated.
Receipts: receipts/fuzz-model-vs-oracle.json, receipts/score-skeleton-validation.json, receipts/panel-precheck-design-only.txt, instruction-preflight.txt; image :skeleton3.
