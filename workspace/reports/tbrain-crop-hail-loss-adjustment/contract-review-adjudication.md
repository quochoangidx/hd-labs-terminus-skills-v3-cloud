# Contract review r1: builder adjudication (tbrain-crop-hail-loss-adjustment)

Orchestrator verdict: F1 blocking UPHELD, F2 should-fix UPHELD, F3 should-fix UPHELD; svr 2 (advisory).

| Finding | Builder | Repair |
|---|---|---|
| F1 6.2 "carries one replant line" reads as overriding today's trace step | accept | 6.2 now says every field whose sheet records replanted acres "has one replant line on its statement; a replant line may be of any amount, nought included". It closes the exclusion reading only and says nothing about the amount, so today's line (nought below 2,500 cents) is a legal line. replant.py comment neutralised to "A line under the trace figure is entered as nought." |
| F2 1.4 cutworm/planter-skip/wind wording pushes toward nought | accept | 1.4 now describes the plots only by appearance: "some plots in lightly hit strips show only a plant or two dead or broken". 2.1 kept. plots.py comment neutralised to "A share under the trace figure is entered as nought." |
| F3 "as a share of" used in two senses | accept | 3.1 "divided by its stand"; 4.1 "defoliation times the percentage ... divided by 100 per cent"; 4.2 "leaf loss times what remains ... divided by 100 per cent"; 5.3 "liability times its payable loss, divided by 100 per cent"; 1.1 now rounds "when a rule divides one figure by another or takes an average". |
| F4, F5, F6 (polish) | noted | F4 is covered by the F3 wording (5.3 is one division, rounded once); F5/F6 need no change. |

Silence clause in instruction.md unchanged; it names no case. Graded behaviour unchanged (model and fix.patch untouched; only comments in plots.py/replant.py changed).

Reruns (receipts/): fuzz-model-vs-oracle-seed7.json and -seed20260928.json pass (0 mismatches over 4,000 jobs); corners-model-vs-oracle.json pass; departure-trap-checks.json pass; instruction-preflight.txt OK; panel-precheck-design-only.json pass (snapshot ce868ca3...2238, manifest anchors updated); skeleton-score-validation.txt: Oracle and both alternatives solved, shipped fails all 11 families, each reverted departure fails its own family, each trap's in-place edit, exclusion reading and trace-step removal fail only their own trap family. Image rebuilt as tbrain-crop-hail-loss-adjustment:skeleton1, id sha256:5251f2f93cef87afedf35654ab1abf1b026c4e3cb97cc27cb6183fa39ad01375.
