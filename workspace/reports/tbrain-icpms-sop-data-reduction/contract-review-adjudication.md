# contract_review adjudication — tbrain-trace-metal-batch-quantitation

Reviewer: one fresh-context Claude subagent (model pin `opus`, general-purpose), blind to tests/solution (none existed). Packet: instruction.md + environment/.

## Round 1 (original design) — solver-path screen svr = 2, prediction collapses

| # | Finding | Builder | Orchestrator | Action |
|---|---|---|---|---|
| 1 | §7 recovery undefined for ND spike/parent; `recovery` null-ness unstated | accept | uphold | §7 given a stated domain (both results); §8 recovery always a number; complement falls to silence clause (restraint trap 3) |
| 2 | exact landing on CCV limits depends on float operation order | accept | uphold | exact CCV landing removed from coverage paragraph; round-2 later adds "rounded to one decimal" judgement |
| 3 | exact MDL/LOQ landing depends on fit arithmetic | accept | uphold | boundary fixtures built from exactly representable integer-line data, checked in Fraction arithmetic |
| 4 | unbounded is_counts → tolerance can fail a correct solution | accept | uphold | is_counts 1000..1e9; tolerance 1e-6; generator keeps batches well conditioned |
| 5 | `added` units unclear | accept | uphold | §1 states it |
| 6 | empty flag type | accept | uphold | "an empty string" |
| 7 | CCV invariant must hold under SOP fit | accept | uphold | generator `valid()` checks under the SOP fit |
| 8 | blank_levels key order | accept | uphold | stated as meaningless |

svr ≤ 2 → one redesign of the causal core before any verifier: §4 (≥2 blank results), §6 (CCV on both sides), §7 (both results) became domain-stated rules whose complements keep the shipped calculation.

## Round 2 (redesign) — svr = 3, prediction borderline/leaning resists, restraint_traps 4

| # | Finding | Builder | Orchestrator | Action |
|---|---|---|---|---|
| 1 | §1 "added is the concentration added as received" can be read to forbid keeping `added*dilution` in the silent spike case | accept | uphold | §1 now a pure unit statement; instruction silence clause says "keep the calculation the code makes for it today" (applies to all three sites equally) |
| 2 | exact MDL/LOQ fixtures need exact blank means under all mean forms | accept | uphold | boundary fixtures use blank readings with exact sums/means; checked with sum/len, fsum, statistics.mean |
| 3 | kept blank step may take an ND (even negative) first blank | accept (intended) | uphold as intended | model mirrors shipped `blanks.blank_level` on SOP readings |
| 4 | sample readings unbounded in text | challenge | narrow | no text change; graded batches bounded by generator |

Builder addition after round 2: the upper CCV limit cannot be landed exactly by `reading/true*100` (1.1 is not dyadic), so §6 now judges pass/fail on the recovery rounded to one decimal place (common laboratory practice); the reported recovery stays unrounded.

## Skeleton screen 1 (exploratory, 2 terminus-probe solvers, no verifier yet)

Both solvers passed every family and 60 generated batches (2/2) in about a minute: the domain qualifiers written at each rule ("two or more", "both results") were read literally. Strengthening before any verifier: §4 and §7 now use the defined term *result* without a qualifier, and §3 carries one general sentence about rules that speak of results.

## Skeleton screen 2 — 0/2, both failing only the non-detect spike recovery

Both kept the empty-blank-mean and unbracketed cases and fixed the §7 denominator for non-detect spikes too.

## Round 3 (fairness recheck of the two-hop wording) — svr = 3

| # | Finding | Builder | Orchestrator | Action |
|---|---|---|---|---|
| 1 | §3 sentence ("gives no rule for a non-detect") supports a term-level reading (keep only the ND term, apply §7 /added) as well as the value-level one; W7 48.75 vs 97.5 | accept | uphold | §3 now: "Where a rule of this SOP needs the result of a run that is a non-detect, it gives no rule for the value it defines." Skeleton-2 0/2 is therefore ambiguity evidence, not difficulty; discarded as a difficulty signal |
| 2 | rounding ties at x.x5 depend on method and operation order | accept | uphold | §1 now promises no CCV recovery within 1e-6 of a tie; seal.py checks it; generator margin 1e-5 relative |
| 3 | "the calculation" could mean the whole shipped chain | accept | uphold | silence clause: "keep the calculation the code makes for that value today from the values the SOP does define" |
| 4 | all-ND blanks: level via §3 + silence clause | accept | uphold | settled by finding-1 wording |
