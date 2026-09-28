# Contract review r2 — tbrain-microbial-plate-count-reporting (reviewer B)

Scope: packet r2, instruction.md + environment/ only.

## Part 1 — Contract review

What changed: 2.6 now defines a sparse sample as one with neither a countable nor a crowded plate. The new 2.8 defines counted plates as the non-crowded plates of the counted dilutions. 4.1 now divides over the counted plates. 4.4 now applies to a sample with a crowded plate and no countable plate, taking the last dilution that holds a crowded plate. The instruction adds "plates of every kind side by side on one dilution". The code keeps the r1 defects and adds a new one: `in_count` treats a TNTC plate as 0 colonies and includes it in a count. Classes now partition every sample: countable → 4.1; otherwise crowded → 4.4; otherwise sparse → 4.2/4.3.

### r1 findings
- r1-1 (mixed crowded + sparse sample ungoverned): **closed.** 4.4 now governs it: `[TNTC,3]@1` gives `>3.0E3`. 2.6 keeps such samples out of 4.2/4.3.
- r1-2 (step k+1 vs next listed dilution): **unchanged, still polish.** The SOP text is clear; it is a trap, not a defect.
- r1-3 (which plates on a counted dilution join a count): **changed deliberately.** Sparse and 0-reading plates on counted dilutions now join (2.8), and crowded ones do not. The sentence governs every case.
- r1-4, r1-5: closed / unchanged. Limits and rounding are fully stated.

### New findings
1. **polish — the preservation sentence has no evident target.** With the partition complete, I found no figure the SOP leaves ungoverned. "Where the SOP gives no rule ... keep the figure" is now close to vacuous, and it may push a solver to hunt for something to preserve. One example is the `estimate()` pooling, which 4.2 fully replaces. It does no grading harm as long as no hidden test relies on a preserved figure. If one does, it must be named.
2. **polish — 2.8 against expert instinct.** Under the reference-method (BAM/ISO) habit, a plate below 20 on a counted dilution is dropped. 2.8 plainly includes it, together with 0 readings: `@2 [150,12], @3 [0,25]` gives `8.5E3` under 2.8 and `8.8E3` if the sparse plates are dropped (175/0.02). A definition chain in the rule text covers this, and there is no competing enumeration, so it is not a defect. The 4.1 parenthetical about n1 + 0.1 n2 could prime the reference-method reading, but it only addresses the divisor.
3. **polish — TNTC on a counted dilution.** Today's `in_count` adds a TNTC plate as 0 colonies with a plated amount. 2.5 and 2.8 exclude it. This is clear but easy to miss: `@1 [TNTC,280,5], @2 [30]` gives `1.5E3` under the SOP and 315/0.31 = 1016 → `1.0E3` if the TNTC plate joins.
No blocking or should-fix findings.

### Witnesses (hand-worked, no guesses)
| # | input (v1.0 unless stated) | kind / apc |
|---|---|---|
| W1 | @2 [150,12], @3 [0,25] | count `8.5E3` (187/0.022) — sparse and 0 plates beside countable ones |
| W2 | @2 [150,0], @3 [18,5] | count `7.5E3` (150/0.02; @3 has no countable plate, so it is not counted) |
| W3 | @1 [TNTC,280,5], @2 [30] | count `1.5E3` (315/0.21) |
| W4 | example RM-101: @1 [TNTC,TNTC], @2 [212,187], @3 [19,24] | count `2.0E4` (442/0.022=20090.9) |
| W5 | @1 v0.1 [301,20] | count `2.0E3` (20/0.01; 301 is crowded) |
| W6 | @1 [TNTC,5], @2 [400,3], @3 [2] | above `>3.0E4` (last crowded dilution is @2) |
| W7 | @1 [0,0], @2 [0,3] | estimate `1.5E2` (3/0.02) |
| W8 | @0 v0.1 [0], @1 [0] | below `<1.0E1` |
| W9 | @1 [125] | count `1.3E3` (half up) |
| W10 | @1 [250], @3 [30] | count `2.5E3` (skipped step) |
| W11 | @1 v0.1 [250], @2 v1.0 [30] | count `1.4E4` (280/0.02) |

## Part 2 — Solver-path screen

A) Pre-mortem: a strong solver reads the short SOP clause by clause against about 70 lines of code and rewrites `plates.py` and `results.py` with Fractions. The code's defects map one to one onto SOP sentences: volume, 20–300, TNTC as crowded, k+1 counted dilution, 2.8 counted plates, half-up rounding, 4.4 last crowded dilution with 300, 4.2 first dilution with a colony, 4.3 first dilution. The solver writes its own reference from the same sentences and fuzzes it. Likely slips, in order: including TNTC as 0 in a count (inherited `in_count`), dropping the sparse plates of counted dilutions (reference-method instinct), and next-listed instead of k+1. Each has a direct sentence, and a careful solver with a clause checklist catches all three. No step requires information the solver cannot see.

B) Scores: reference_unreachable 1; authority_incomplete_for_grading 1; hidden_state_not_closed_form 1; restraint_traps 1 (the TNTC exclusion, the crowded-plate exclusion in 2.8 and k+1 are all conditions written into rule sentences, so they score 0; nothing ungoverned needs to be kept); fuzz_blind_spot 1.

C) self_verification_resistance 1. prediction: collapses. confidence: high. decisive_reason: the contract is now complete and closed-form, and every defect is a one-sentence diff that the solver's own SOP-derived reference and fuzzing will confirm.
