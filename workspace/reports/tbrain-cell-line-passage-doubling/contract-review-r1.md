# Contract review r1: tbrain-cell-line-passage-doubling

Scope: I read only `instruction.md` and `environment/` (the Dockerfile, the README, SOP CB-3, the driver, the `cellbank` sources and `examples/small-log.json`).

## Part 1: Contract review

### Summary of the contract as I read it

- Doublings = log2( (harvested * v_harvest/100) / (seeded * v_source/100) ), where v_source is the viability of the source suspension's count: the thaw's `viability`, or the source culture's harvest `viability` (SOP 2.2–2.4, 3.1).
- If either count has viability < 70.0, SOP 2.6 sets no value. The instruction then keeps today's figure, log2(harvested/seeded). No viability term enters that fallback, even when the other count is valid.
- Passage and PDL follow the lineage graph, not the log order:
  - A culture's passage is its source's passage + 1. Its PDL is its source's PDL + its doublings.
  - A supplier thaw starts at (`seed_passage`, `seed_pdl`) with no +1.
  - A bank thaw inherits the passage and PDL of its freeze's harvest.
- Age is the running maximum of PDL along the lineage:
  - A supplier thaw's age is `seed_pdl`.
  - A bank thaw's age is the age of its freeze's harvest (the age, not the PDL).
- Flag: `LIMIT` when age > max; `NEAR` when age > max − 3 and ≤ max; otherwise "". The inputs keep every age at least 10^-6 away from both thresholds, so `>` versus `>=` never matters.
- Banks:
  - `vials_left` = vials frozen − thaws against that bank's freezes.
  - `pdl` = the highest harvest PDL among the bank's freezes that still have vials in stock.
  - Banks are listed in the order of their first freeze.
- The current code has five defects:
  1. It uses raw rather than viable counts.
  2. It tracks state per line in log order.
  3. A thaw resets to the seed values and adds one passage.
  4. The flag uses PDL with `>=` and a band of 5.
  5. Banks never subtract thawed vials, and a bank's PDL is the last freeze's PDL.

  These map one-to-one onto the five symptoms in the instruction.

### Findings

**F1: should-fix. The PDL of an empty bank is governed only through the preservation paragraph, and the reader has to work that out.**

Citation, SOP 6.2: "A bank's **PDL** is the highest PDL of its vials in stock." The instruction also says banks are run "with none, some or all of their vials thawed".

When a bank has no vials left, the maximum is over an empty set, so the SOP sets no value. The instruction's "Where the SOP sets no value for a figure, the figure the code calculates for it today stands" then applies. Today's code sets `bank["pdl"]` to the PDL of the bank's *last freeze record in log order*. The values that go into it must now be the SOP-correct harvest PDLs.

The problem is the wording. The phrase "sets no value" echoes SOP 2.6 almost word for word ("this SOP sets no value for that figure"). A reader can fairly take the preservation paragraph to mean only the failed-count case in 2.6. That reader would then emit `null` or `0`, drop the bank, or take the maximum over all vials ever frozen.

Counterexample:
- Bank B has freeze F1 (harvest PDL 20, 1 vial) and then freeze F2 (harvest PDL 15, 1 vial). Both vials are later thawed.
- Readings: 15 (last freeze, today's rule), 20 (maximum over all vials), `null`, or 0.

The contract does determine 15, but only through an inference chain the instruction never spells out: max over an empty set → "sets no value" → today's last-freeze overwrite → SOP-correct freeze PDL. Suggested fix: make the SOP or the instruction name the empty-bank case, or add an explicit clause such as "including a bank with no vials in stock".

**F2: polish. The failed-count fallback is determinate, but a partial-viability reading is tempting.**

Citations: "worked out the way the code does it now from values the SOP does set", and SOP 2.6: "set only when every count the rule would use is valid".

Today's code is `log2(harvested/seeded)`. If the source count failed but the harvest count is valid, one plausible wrong reading uses the harvest's viable count over the raw seed.

Counterexample:
- A thaw at viability 60.0 seeds a culture: seeded 1e6, harvested 4e6, viability 80.0.
- The contract gives 2.0. The partial reading gives 1.678072.

The instruction's text resolves this, so it is not a defect. It is simply the most likely slip.

**F3: polish. Dependent figures after a fallback.**

The sentence "every other figure that depends on it still follows the SOP" settles whether PDL, age and flag follow the SOP after a fallback doublings value. It also blocks the reading that PDL itself is unset (because 4.1 is written in doublings) and should revert to today's log-order PDL.

The sentence is clear, but it relies on "depends on". Consider a harvest with a failed count whose child culture uses a valid count of its own harvest. Because the seed is counted at the parent's viability (2.4), the child's doublings also fall back. That is correct under 2.4 + 2.6, but it is easy to miss.

Counterexample:
- C1 has a harvest at viability 50.0. Child C2: seeded 1e6, harvested 2e6, viability 100.0.
- C2's doublings are 1.0 (fallback), not log2(2e6/(1e6*0.5)) = 2.0.

This is determinate.

**F4: polish. The output type of whole numbers.**

Citation: "every `passage` and `vials_left` as a whole number … compared exactly".

The instruction does not say whether `4.0` counts as equal to `4`. If `seed_passage` arrives as a JSON integer, Python arithmetic keeps it an int, so the risk is low. It becomes a problem only if a solver casts values through float.

**F5: none. Ranges, ordering and rounding are fully covered.**

- Ranges: every numeric input has both a floor and a ceiling (SOP 1.3, 1.5; instruction paragraph 3). Lineage PDL is bounded to −100 to 1,000.
- Ordering: cultures are listed in log order; banks in the order of their first freeze.
- Rounding: none ("Nothing in this SOP is rounded").
- Threshold ties: excluded by the 10^-6 margin.
- Tolerance: stated.

I found no arbitrary convention without an authority sentence.

**F6: none. The preservation and silence line.**

- The inputs left open are named in the SOP's own terms: out-of-range values, structural breaks and undescribed fields.
- No SOP sentence positively governs the failed-count doublings that the instruction keeps. SOP 2.6 explicitly abstains.
- The trailing 7.2 sentence ("These rules add no other correction, exclusion or guard") is consistent with the instruction's "add no exception, clamp or guard".
- The asides in 2.3 and 4.2 pre-empt the expert instinct to compute a viable figure at any viability, or to add a passage at a thaw. The restraint here comes from explicit authority text, not from a definition chain.

### Hand-worked witnesses

All witnesses use line L: `seed_pdl` 10, `seed_passage` 3, `max_pdl` 40, unless noted otherwise.

| # | Input (abridged) | Output the contract implies | Guess? |
|---|---|---|---|
| W1 | T1: supplier thaw, viability 90.0. C1 ← T1: seeded 1e6, harvested 4e6, viability 90.0 | C1: passage 4, doublings 2.0, pdl 12.0, flag "" | no |
| W2 | T1 at viability 60.0 (failed). C1 ← T1: seeded 1e6, harvested 4e6, viability 80.0 | C1: doublings 2.0 (fallback, not 1.678072), pdl 12.0, passage 4 | no |
| W3 | T1 at 100.0. C1 ← T1: seeded 1e6, harvested 2e6, viability 50.0 | C1: doublings 1.0 (fallback; the naive viable reading gives 0.0), pdl 11.0 | no |
| W4 | T1 at 100.0. C1 ← T1: 1e6 → 8e6 at 100. C2 ← C1: 1e6 → 2e6. Other records logged in between. C3 ← C1: 1e6 → 4e6 | C1: p4, pdl 13. C2: p5, pdl 14. C3: p5, pdl 15 (not p6/16) | no |
| W5 | Continue W4. F1 ← C2, bank B, 2 vials. T2: vial F1, viability 100. C4 ← T2: 1e6 → 2e6 at 100 | C4: p6, pdl 15.0 (14 + 1), flag "". Bank B: vials_left 1, pdl 14.0 | no |
| W6 | `max_pdl` 20, seed 10. C1 ← supplier thaw: +9 → pdl 19. C2 ← C1: seeded 1e6, harvested 5e5, both at 100 (−1) | C1: NEAR (19 > 17). C2: pdl 18, age 19 → NEAR (the old code on PDL with a band of 5 also says NEAR). Next child +2.5: pdl 20.5 → LIMIT. A child of that one at −2: pdl 18.5, age 20.5 → LIMIT (not NEAR) | no |
| W7 | Viability exactly 70.0 on a thaw. C1: 1e6 → 2e6 at 100.0 | doublings = log2(2/0.7) = 1.514573 (70.0 counts as valid) | no |
| W8 | Bank B: F1 (harvest pdl 20, 1 vial), F2 (pdl 15, 2 vials). One thaw of F1 | vials_left 2, pdl 15.0 | no |
| W9 | As W8, but one thaw of F1 and two of F2 | vials_left 0, pdl 15.0 (the last freeze's PDL, as today's code has it) | **yes, inferred via F1** |
| W10 | A bank thaw's vial has harvest age 22 and PDL 19. A culture from it gains 0.5 (`max_pdl` 21) | pdl 19.5, age 22 → LIMIT | no |

## Part 2: Solver-path screen

### A) Pre-mortem

A strong solver would do the following:
1. Read the whole SOP.
2. Rewrite `lineage.walk` as a per-record state map keyed by id: (passage, pdl, age, viability, line), resolved through `source` and `vial`.
3. Change `growth` to viable counts, keeping `log2(harvested/seeded)` whenever either viability is below 70. The instruction points straight at "today's calculation", and that fallback is exactly the current code, so a minimal-diff solver keeps it by default.
4. Fix the flag to use age, with `>` and a band of 3.
5. Rewrite `banks` to subtract thaws per freeze and take the maximum PDL of freezes still in stock.

It would self-check by writing a few logs like W1–W8 and fuzzing against its own reference.

The likely failure is concentrated in step 5. `max()` over an empty set raises, so the solver is forced to choose. It will emit `None` or 0, take the maximum over all freezes, or — if it connects "sets no value" to the preservation paragraph — keep the last-freeze overwrite. Its own reference shares whatever reading it picked, so fuzzing cannot reveal the error.

Secondary slips:
- A partial-viability fallback (F2).
- Forgetting that a child seeded from a failed harvest also falls back (F3).
- Setting a bank thaw's age to the vial's PDL instead of the harvest age. SOP 5.1 states this explicitly, so the slip is unlikely.

### B) Scores (5 = strongly resists solving)

| Axis | Score | Reason |
|---|---|---|
| reference_unreachable | 1 | A small closed-form DAG computation that fits in about 80 lines. |
| authority_incomplete_for_grading | 2 | Everything is determinate. The empty-bank PDL is reachable only by the inference in F1, which is a mild defect rather than a point. |
| hidden_state_not_closed_form | 1 | No hidden state. |
| restraint_traps | 2 | One qualifying site: the empty-bank PDL fallback. It sits inside the bank aggregate that the fix forces the solver to rebuild, and it keeps today's routing. The failed-count fallback is a condition written into the rule sentence (2.6) and matches the current code, so it counts zero. The 2.3 and 4.2 asides are explicit authority, not traps. |
| fuzz_blind_spot | 2 | Empty banks and failed counts are easy to generate. Self-fuzzing fails only because the solver's reference shares its own reading. |

### C) Verdict

| Item | Value |
|---|---|
| self_verification_resistance | 2 |
| prediction | collapses (both of two solvers likely solve fully) |
| confidence | 0.6 |

Decisive reason: every rule is an explicit closed-form sentence, and the one soft spot (the empty-bank PDL) is resolved by preserving code the solver already has. A careful Opus 5–class solver that keeps the current overwrite, or re-reads the preservation paragraph, will clear it, and nothing else resists.
