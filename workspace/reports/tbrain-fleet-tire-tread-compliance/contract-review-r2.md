# Contract review r2 — tbrain-fleet-tire-tread-compliance (reviewer C)

Scope: packet r2 (`instruction.md` + `environment/`). Diff against r1: only `docs/tread-standard.md` §1.5, §2.3, §3.1 and §4.1 changed. The instruction and the code are unchanged.

## Part 1 — Contract review

### Status of r1 findings

1. **Wear-bar depth: CLOSED.** §3.1 now defines only a "measurement's measured depth", and §4.1 reads "the measured depth of its latest reading". A reading below 10 tenths has no measured depth, so §4.1 no longer reaches it and nothing else in the standard gives it a depth. The instruction's precedence rule then yields exactly one value: today's `depth = shown`, with no offset. Example: shown 5 on a +3 gauge gives latest 5. The readings of 8 (offset added) and 0 (depth taken as the wear bar) no longer have a textual basis, because the word "depth" alone is no longer defined anywhere. There is a residual risk that a solver reads the undefined term as a gap to fill with the offset. That would be a misreading, not ambiguity.
2. **Non-fresh worn/distance: unchanged and still fair.** §4.2 still reaches only fresh tires. Today's first-to-last working applies, with measured depths as inputs. The last reading can be a wear-bar reading (raw shown). One value.
3. **First depth above new depth: CLOSED.** §1.5 now says the first shown + offset is never above `new_depth`, so the abs-difference reading can no longer change the outcome.
4. **Negative worn: still possible, polish.** Only the first reading is capped. A later reading can exceed `new_depth`, e.g. new 60, first 60, latest 70, worn −10. The half-up rule (§1.1) settles it: −2.5 goes to −2. No defect.
5. **Rounding, ranges, status, retread: unchanged and clean.**
6. **Ordering: unchanged.** "listed in date order" makes list order explicit, which slightly tightens the wording.

### New issues
None. The renamed term "measured depth" is used consistently in §2.3, §3.1 and §4.1. §2.3's first reading is always a measurement (shows ≥ 20), so freshness is always defined.

### Witnesses (all r1 witnesses still hold; W3 no longer a guess)
- W1 sample: latest 91, worn 85, distance 67812, rate 13, in service, retread false.
- W2: steer 40 → pull, 56 → watch, 57 → in service; drive 32 → pull, 48 → watch.
- W3: drive, latest shown 5 on a +3 gauge → latest 5, pull. Fresh: new 100, mount 0, last odometer 50000 → worn 95, rate 19.
- W4 non-fresh: worn 40, distance 20000, rate 20.
- W5: worn 1, distance 4000 → rate 3.
- W6: casing age 2189 days, pulled, retreads 1 → true. 2190 days → false. Retreads 2 → false.
- W7: fresh, new 60, latest 70, distance 40000 → worn −10, rate −2.
- W8: shown 9, offset −9 → latest 9. Shown 10, offset −9 → latest 1.

## Part 2 — Solver-path screen

A) The pre-mortem is as in r1. The rewording makes restraint site (a) easier to spot: a solver who follows the term "measured depth" sees that §4.1 does not cover wear-bar readings. The natural one-line edit in `reading_depths` (add the offset to every reading) is still the main way to fail. Non-fresh routing is still the second.

B) Scores:
- reference_unreachable: 2
- authority_incomplete_for_grading: 1 (r1 finding 1 closed)
- hidden_state_not_closed_form: 1
- restraint_traps: 3 (offset limited to measurements inside the rebuilt `reading_depths`; the kept non-fresh routing)
- fuzz_blind_spot: 2

C) self_verification_resistance: 2. Prediction: **collapses**. Confidence: medium-high (about 65%). decisive_reason: the contract is now closed with one value per witness, and both traps are signposted by defined terms, so careful solvers converge on the reference.
