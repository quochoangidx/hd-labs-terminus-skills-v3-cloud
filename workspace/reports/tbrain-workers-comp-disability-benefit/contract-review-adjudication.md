# Contract review adjudication (builder)

## r1 (2026-09-27) and skeleton cycle-1 = 2/2: strengthening 1/1

Root cause (orchestrator, accepted): in both cycle-1 traps the minimal natural fix already branched on
the governed subtype (`if Friday`, `if full_time`), so today's handling of the silent subtype survived by
default. Redesign rule: the minimal natural fix of each trap's departure must change the silent case.

| Finding | Builder | Change |
|---|---|---|
| F1 should-fix: bonus week, three readings (keep / exclude / shift) | accept | Bonuses and weekday discrimination removed: every wage line is a Friday payday line (1.4). "A week's pay" is now a wage line of 2,000 cents or more (2.2); corrections are described only in domain words in 1.4. 3.2 now says every wage line counts toward one payroll week, which closes the exclusion reading; only 3.1 places lines, and only a week's pay, so the reach rule keeps a smaller line's payday week. Shift is the over-repair (new T1). |
| F2 should-fix: part-time divisor, two figures | accept (by removal) | The full-time definition and the part-time trap are gone; 3.3 divides every AWW by thirteen (D2). |
| F3 polish: precedence sentence reads per input | accept | The reach rule now speaks of a figure: "Where the package works out a figure for which no rule of the manual covers the case in hand, that figure keeps coming out the way today's code works it out ... while every other figure of the same claim still follows the manual." |
| F4 polish: bonus-only week and full-time count | moot | Full-time removed. |
| svr 2, "minimal edit keeps both traps" | accept | New T1: the shipped loop treats every line alike, so `week_ending(day) - WEEK` moves corrections too. New T2: the weekly-rate fraction is one shared constant (rates.py) read by partial.py; the minimal fix of 3.4 edits the constant and moves weeks below 1,000 cents (2.8: not a week of partial disability; 1.6 domain words; 5.2 gives every week a benefit) from today's 60 per cent to two thirds. Keeping either needs added code. |

Departures now 8: D1 crediting (2.2/3.1), D2 AWW over 13 (3.3), D3 two thirds (3.4, shared with 5.1), D4 row in force (2.4), D5 low wage (3.5), D6 both ends (2.5), D7 three waiting days (2.6), D8 TTD rounding (4.3). The earlier partial-cap departure is now shipped-correct.
Receipts: receipts/score-skeleton-validation.json (image :skeleton2), receipts/departure-trap-checks.json, receipts/fuzz-model-vs-oracle-seed{20260927,7}.json, receipts/panel-precheck-design-only.json, trap-screen.json, solver-path-screen.json.

## r2 (2026-09-27), skeleton cycle-2 raw 1/2 discarded as ambiguity (run_1 paid two thirds on low weeks = r2 F1)

| Finding | Builder | Change |
|---|---|---|
| F1 blocking: reach rule lets the manual's two thirds replace today's 3/5 for weeks under 1,000 cents | accept | Reach rule rewritten at value level (instruction ¶2): "Whatever the package works out, or does with an item, that no rule of the manual reaches stays exactly the calculation today's code makes, with the package's own constants at the values they have today; only those inputs of that calculation that the manual itself settles take their manual values. This comes ahead of everything else in this paragraph, and everything else about the same claim follows the manual." No site, no example; "Add no exception, clamp or guard of your own" kept. |
| F2 should-fix: README tpd_weeks vs 6.1 | accept | README: "`tpd_weeks`: the number of weeks in the partial earnings;" |
| F3 should-fix: 'a figure' vs T1's week placement | accept | Covered by "or does with an item" in the new reach rule. |
| F4 polish: half-up never reachable | accept (narrow) | Manual 1.1 now says only "rounded to the nearest cent"; the divisors 13, 3, 5, 7 never leave an exact half. Model/solve.sh comments updated; no code change. |

Reran: instruction_preflight, design-only precheck, fuzz (both seeds), departure-trap checks, scorer validation on image :skeleton3.

## Phase 2 (verifier and closure), snapshot 024101da

No agent-visible change: instruction.md and environment/ are byte-identical to cb72b8d5 (probe solver-contract hash 44542c65 unchanged). r3 P1/P2 polish left unapplied on purpose (notes to the orchestrator). Cycle-3 diffs rescored on the finished verifier: run_1 22/23 (fails only test_week_below_1000_cents_keeps_todays_share, the T2 miss), run_2 23/23 (local-solve-probes/tbrain-workers-comp-disability-benefit-cycle-3/rescore-024101da/).

## Panel discovery (5806f1bc) and final_review: one consolidated batch, snapshot 739e9dab (panel hash ad6e645e)

SV-A, SV-B, FR-F1, FR-F2, FR-F3 backed; FR-F4 acknowledged (no change). Only tests/, solution/ (jobgen, seal) and task.toml changed; instruction.md and environment/ byte-identical (probe solver-contract hash 44542c65 unchanged). Rows with reproduction (returned tree rebuilt from the discovery packets, hash 024101da) and closure receipts: revision-ledger.json (revision_ledger_check.py OK). Cycle-3 rescore on the new verifier: run_1 22/23 (T2 only), run_2 23/23 (local-solve-probes/tbrain-workers-comp-disability-benefit-cycle-3/rescore-739e9dab/). Clearance axes: coherent_contract, correct_reference_solution, sound_verifier, deterministic_execution (protected_ground_truth carried).
