# Contract review r1: tbrain-crop-hail-loss-adjustment

Scope: `contract-review-packet-r1/instruction.md` and `environment/` only.

## Part 1: Contract review

### What the contract requires (my reading)

Required repairs, each with its authority:
- 3.3: averages taken over **all** plots (today `plot_average` drops zeros).
- 4.3: R4 is 40 (today 55).
- 4.2: loss = stand + half_up(leaf x (1000 - stand) / 1000) (today stand + leaf).
- 5.1: minimum loss 80 (today `minimum_loss` reads `trace_tenths` = 50).
- 5.2: straight deductible 100 (today 50); vanishing capped at the loss (today no cap).
- 5.3 + 1.1: indemnity is rounded half-up (today floored, which is the "cent short").
- 7.2: minimum claim 10000 (today `minimum_claim` reads `small_cents` = 2500).

Kept, per the preservation paragraph ("keeps the exact calculation today's code makes, with every constant of the package at its value today"):
- The stand figure of a plot that is **not** hail-thinned (2.1). Today's rule is half_up(dead*1000/stand), zeroed below 50. Nothing in the procedure gives it a value. `plot_trace` must stay at 50 even though it shares `trace_tenths` with `minimum_loss`.
- The replant line of a field that is **not** a replanted field (below 10.0 acres). Today's rule is replanted*300, zeroed below 2500. `replant_trace` must stay at 2500 even though it shares `small_cents` with `minimum_claim`.

The two shared-constant couplings in `figures.py` (`STEPS` maps two steps to one figure, twice) are the main place a solver has to hold back. If you just edit the `FIGURES` values, a kept calculation silently changes with them.

### Findings

**F1 (blocking): 6.2 arguably governs the replant trace clamp that the instruction otherwise leaves as silent/kept.**
- Authority: 6.2 "Every field whose sheet records replanted acres carries one replant line." Code: `replant.py` zeroes any line under 2500 cents with the comment "Too small to be worth a cheque line of its own."
- Reading A: the procedure never sets a value for a sub-10-acre line, so today's calculation is kept, clamp included.
- Reading B: 6.2 positively says that such a field *carries* a line. The clamp exists only to stop a line being carried, so 6.2 overrides it and the line is replanted*300.
- Reading C, the natural domain fix: 6.1 pays only replanted fields (2.2), so small replants get 0.
- Counterexample: a field with `replanted: 5` (0.5 ac). A gives `replant` 0, B gives 1500, C gives 0. With `replanted: 50`, A and B give 15000 and C gives 0. Inputs with 1 to 8 tenths are in range (1.3 "from none to the whole").
- The contract does not pick between A and B, because a line of 0 cents is still arguably "a line". The fix is to state what a non-replanted field's line is, or to drop 6.2's first sentence.

**F2 (should-fix): the stand figure of a plot that is not hail-thinned is a restraint site that fights strong domain instinct.**
- Authority: 3.1 defines stand loss only for hail-thinned plots. 3.2 says "Every sample plot has one stand-loss figure" but gives no value. 1.4 says light plots show losses from "cutworms, a planter skip or wind", which pushes the reader to count these as non-hail, i.e. 0.
- Readings: (keep-today) 0 below 5.0%, the raw share from 5.0% to 9.9%. (zero) 0. (raw, reading 3.2 as "every plot has *a* figure", with the trace clamp being "not carrying" it; the code comment even says "not worth carrying onto the field sheet") the raw share.
- Counterexample: a single plot `[100, 8, 0]`, full, V6. Keep-today gives stand 80, loss 80, payable 80. Zero gives loss 0, payable 0. Plot `[40, 1, 0]`: keep gives 0, raw gives 25.
- The instruction's preservation paragraph does decide this (keep-today), but 1.4 plus the definition chain in 2.1 is a strong competing signal. The same code-comment wording ("carrying") as in F1 invites the argument that 3.2 kills the clamp, so the two sites cannot both be read by the same principle unless one of them gives way. Treat this as a contract risk, not as difficulty.

**F3 (should-fix): the operator phrasing "as a share of" and "taken as a share of" switches meaning.**
- 3.1 "dead and broken plants as a share of its stand" means dead / stand.
- 4.2 "leaf loss taken as a share of what remains" and 5.3 "payable loss taken as a share of its liability" mean leaf x remaining and payable x liability.
- A literal reader of 4.2 could compute leaf / (1000 - stand). The complaint ("paid more than the crop was worth") and 5.3's parallel wording resolve it, so this does not block.
- Counterexample: stand 500, leaf 100. The intended reading gives loss 550. The ratio reading gives 500 + 200 = 700.

**F4 (polish): 1.1 rounding of liability and replant money.**
- Liability (2.3) in cents is per_acre x acres_tenths x 10, and 6.1 gives replanted x 300. Both are exact, so 1.1's "not rounded" clause is harmless.
- It would still help to say that the rounding in 5.3 is applied once, to payable x liability, and not to an intermediate liability in dollars. Two-step rounding is not possible here, so this is only clarity.

**F5 (polish): range floors and ceilings.** Every range in 1.2 to 1.4 has a floor and a ceiling. Leaf 0 to 1000 is given, "replanted from none to the whole" is given, and dead goes from none to the whole stand. Nothing is missing. Stages outside the chart and unknown deductibles are explicitly left open.

**F6 (polish): the output contract is complete.** The README lists exact keys, units and order, and the instruction fixes integer typing and ordering. The only arbitrary conventions are half-up rounding (1.1), strict "below" for minimums (5.1 "below 8.0", 7.2 "10,000 cents or more") and "one plant in ten ... or more" (2.1, so dead*10 >= stand). All have authority sentences.

### Grounded witnesses (hand-derived; with acres=10 and per_acre=10, indemnity = payable)

1. `examples/sample-job.json`:
   - North 80: stand 190, defoliation 365, leaf 128, loss 294, payable 194, indemnity 655099, replant 0, payment 655099.
   - Creek bottom: 690 / 620 / 93 / 719 / 719 / 985461 / 106800 / 1092261.
   - Total 1747360, paid 1747360.
   - North 80's stand average is 758/4 = 189.5, rounded to 190. Its [36,0,150] plot counts as a zero.
2. `[[100,8,0]]`, full, V6: stand 80, loss 80, payable 80, indemnity 80. **I had to guess** (F2): the zero reading gives 0.
3. `[[40,3,0],[40,1,0]]`, full, V6: stand (75+0)/2 = 37.5, rounded to 38. Loss 38, payable 0 (below the 80 minimum). **Guess** (F2).
4. `[[200,21,0]]`, acres 11, full, V6: stand 105, loss 105, indemnity 105x10x11/100 = 115.5, rounded to 116 (today floors to 115).
5. `[[20,20,0],[200,0,0]]`, vanishing, R4: stand 500, loss 500. 2x(500-200) = 600 is capped to 500, so payable is 500.
6. `[[20,20,1000]]`, straight, VT: stand 1000, leaf 1000, loss 1000 + 1000x0 = 1000, payable 900.
7. `[[40,8,500],[40,0,300]]`, acres 20, per_acre 20, full, R4: stand 100, defoliation 400, leaf 160, loss 100 + half_up(160x900/1000 = 144) = 244, indemnity 976.
8. Claim minimum: a claim whose total is 9999 has paid 0, and one whose total is 10000 has paid 10000.
9. `replanted: 5` on a 1.0-ac field: replant is 0 or 1500. **Guess** (F1).

## Part 2: Solver-path screen

**A) Pre-mortem.**
- A strong solver reads the 110-line procedure, diffs it against 8 small modules, and finds every priced defect quickly. Each one is paired one-to-one with a sentence in the complaint: averaging, R4, 4.2, the deductibles, rounding, and the two minimums.
- It writes a reference over the full input space and fuzzes within the section 1 limits.
- The only places it can go wrong are the two coupled constants and the two kept "non-X" branches.
- A careful solver reads "with every constant of the package at its value today", splits `STEPS` into separate figures, and keeps 50 and 2500.
- Its main risk is F1: it may treat 6.2 as authority to delete the replant clamp, or may zero small replants/non-thinned plots on the strength of the 2.1/2.2 definitions and 1.4.
- Its self-tests would encode whichever reading it chose, so no self-check catches the error. The outcome turns on reading, not on computation.

**B) Scores (5 = strongly resists solving).**
- reference_unreachable: 1. Everything can be computed in closed form from a public procedure.
- authority_incomplete_for_grading: 3. F1 is a real two-way split on in-range inputs, and F2 has a competing signal. Both are defects, not difficulty.
- hidden_state_not_closed_form: 1.
- restraint_traps: 2. Two coupled constants sit inside the `FIGURES`/`STEPS` table that the minimum-loss and minimum-claim repairs force the solver to rebuild; these count. The non-thinned plot and small-replant branches rest on definition chains (2.1, 2.2), but they meet strong contrary instinct (1.4), and F1 has a competing positive sentence (6.2). Under the 0/8 screen those two are contract defects, not points.
- fuzz_blind_spot: 2. Fuzzing within limits hits non-thinned plots and small replants often, but only against the solver's own reading.

**C)**
- self_verification_resistance: 2.
- prediction: collapses if F1 is resolved. As written, the likely outcome is split or noisy results driven by F1/F2 interpretation rather than real resistance.
- confidence: medium.
- decisive_reason: every required fix maps one-to-one onto a named complaint and a short procedure sentence, so the only thing between a strong solver and a full solve is an ambiguous preservation boundary (6.2 vs the replant clamp). That boundary should be fixed, not counted as difficulty.
