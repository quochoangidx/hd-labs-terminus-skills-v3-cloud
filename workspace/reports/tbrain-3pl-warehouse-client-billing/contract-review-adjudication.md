# Contract review r1 adjudication (builder C), 2026-09-27

Reviewer: contract-review-r1.md (svr 2). Orchestrator: F1, F2 upheld; redesign 1/1. Skeleton cycle-1 (1/2 raw) discarded as ambiguity evidence (run_1 took F1 reading A); both runs found both "gives no rule" sentences.

| Finding | Builder | Resolution (snapshot after redesign) |
|---|---|---|
| F1 (blocking) open-lot discount has readings A/B/B' | accept | The open/closed accrual concept and the discount are removed. The new M1 rule (6.2) is "`surcharge_percent` of its storage charge": one figure the rule plainly needs, no "total of the charges" that could shrink to the rest. 2.6 adds "a figure a lot does not have ... is never taken as nought", closing the base-is-nought reading. |
| F2 (should-fix) reach of the 3.1 silence | accept | The static silence is removed: 1.4 now puts a client's first revision on or before every receipt of its lots and the period start, so a revision is always in force (3.1 governed). The instruction now says every other value, "including those worked out from it", follows the schedule, so a kept value flows into governed downstream rules; each kept value is a single figure (a lot's surcharge; a lot's peak). |
| F3 (polish) same-date dispatches | accept | 2.1: "Several dispatches may share a date." Envelope: "several on one day". |
| F4 (polish) example never exercises the trap | accept (by design) | The example carries no trap input; it now shows a minimum fee with a surcharge of nought. |
| Solver-path svr 2 | accept | Redesign: both traps now hang on computed membership (see trap-screen.json): a lot pays a minimum fee only when its repaired storage falls below the client's minimum, and a lot has no billed week only when the repaired anniversary weeks and on-hand counts leave none. One general value-level sentence (2.6) sits in the Terms section; no rule sentence carries a qualifier. |

# Strengthening (the one allowed), after skeleton cycle-2 2/2 and contract review r2, 2026-09-27

Cause: both cycle-2 solvers grepped 2.6 ("gives no rule for the value it defines"), listed the computed cases and kept both traps. Rebuilt to contract-closure §15 rules 1-3 and 9-17: the schedule no longer contains any "no rule" sentence; silence lives only in the instruction's universal clause with boundary categories in domain words ("entries of nought or below", "lots that have no billed week in the period") and "Add no exception, clamp or guard".

| r2 finding | Builder | Resolution |
|---|---|---|
| F1 (blocking) 1.3 competes with the minimum-fee surcharge silence | accept | The minimum-fee silence (2.5 storage charge, 2.6) is removed; 6.2 takes the surcharge on every lot's billed storage and 1.3 rounds every energy surcharge. No competing enumeration remains. |
| F2 (polish) silent peak on old vs new on-hand | accept | The instruction's "carried out on the values the schedule does define" stays; the kept peak uses the schedule's on-hand counts (model and Oracle). T2 families carry no entries below nought, so the two traps do not meet. |
| F3 (polish) rate-card sentence looser than 1.4 | accept | Envelope now says "the first taking effect before any of the client's lots arrive". |

Design changes: T1 is now an entry below nought in a lot's `dispatches` (a return to stock, README encodes the sign neutrally), excluded from "dispatch" only by 2.1's one-pallet threshold, so 2.2's next-day timing (departure D1) does not reach it and it keeps the package's same-day timing. T2 keeps a lot with no billed week on today's peak (the D8 expression's degenerate side). D4 changed to "a receipt at the receiving rate" so returns' handling is the same under the shipped step and the natural repair. See trap-screen.json.

# Contract review r3 and skeleton cycle-3 (raw 0/2), 2026-09-27

Cause analysis: skeleton-probe-verdict.cycle-3.json. Both runs missed T1 on timing only (handling identical; return pricing matched the model on 676 random return lots) and T2 by keeping the shipped `most = 0` accumulator over the new domain (an ambiguity of "today's calculation").

| r3 finding | Builder | Resolution |
|---|---|---|
| F1 (blocking) a return's handling price: today's rate choice vs the schedule's | accept | The shipped handling now skips entries below one pallet ("nothing leaves the warehouse"), and 5.3 reads "the total its receipt and its dispatches are billed": a return is billed nothing, uniquely, in both. The symptom sentence now says "receipts and dispatches", not "movements". |
| F2 (should-fix) "no other charge, credit" vs a negative handling line | accept | Closed by F1's repair: no return is billed, so no credit arises. |
| F3 (no defect) return timing trap | agree | Kept as T1. |
| F4 (polish) same-day +/- lets on-hand exceed pallets received | accept | 1.4: a lot's entries are on distinct dates; with the cumulative bound, on-hand stays within 0..pallets under the mixed timing. Generator and within_limits enforce distinct dates. |
| F5 (polish) silent peak relies on the instruction only | accept | T2 (peak) dropped: 4.5 now governs "a lot with no billed week has a peak of nought". |
| F6 (polish) effective-date wording | accept | The instruction now says "the first taking effect on or before the period's start and on or before the day each of the client's lots arrives". |

New T2: a lot whose `pallets` is nought has no receipt (2.1 "A receipt is an arrival of one pallet or more"), so no receipt fee (new departure D9: shipped bills no fee) and no receiving charge. The instruction's silence categories are now one class, "pallet counts of nought or below".

# Contract review r4 (clean) and skeleton cycle-4 (0/2: T1 missed by both, T2 kept by both), 2026-09-27

Orchestrator 0/8 screen on T1 (4 of 4 local misses): two flags, an unnamed shared step (on_hand treats governed dispatches and silent returns in one comparison) and the silence sentence's example pushing uniform treatment. Repaired without disclosing the trap:

| Item | Builder | Resolution |
|---|---|---|
| r4 F1 (polish) no-guard example can be over-read against T2 and calls 1.4-provided inputs "not provided for" | accept | The example is gone. The silence clause is now a reach rule by defined terms: "Each clause reaches exactly the lots, entries and figures that its defined terms cover, and no further. Whatever a clause does not reach keeps what the package does with it today, worked out from the values the schedule does define, and every value worked out from it in turn still follows the schedule. Add no exception, clamp or guard of your own." No site, no input named. |
| r4 F2 (polish) 1.2 "per pallet moved" vs a per-receipt fee | accept | 1.2 adds "the receipt fee is in cents per receipt"; 1.4 "a storage scale, a receipt fee and three handling rates". |
| r4 F3 (polish) example exercises neither trap | acknowledged | Kept trap-free by design. |
| T1 flag: unnamed shared step | accept | The governed/silent line is now drawn in the instruction by the defined terms (a clause reaches what its defined terms cover), and 2.2 names its subject ("a dispatched pallet", 2.1). |
| T1 flag: instruction pushes "treat every entry alike" | accept | Example removed; "no exception, clamp or guard of your own" names no input. |
| Coverage envelope | unchanged | Already names entries "of nought and some below nought ... on the first day of a storage week" neutrally among other input families (rule 17). |

Package, model and Oracle unchanged; only instruction.md and billing-schedule.md 1.2/1.4 wording changed.

# Contract recheck r5 and skeleton cycle-5 (0/2: T1 missed by both, T2 kept), 2026-09-27

T1 missed 6/6 locally and no run reasoned about returns in on_hand. Orchestrator resolution (rule 17, name the silent input, not the trap; rule 16, never disclose the kept behaviour), applied:

| Item | Builder | Resolution |
|---|---|---|
| Silent input invisible in the authority | accept | 2.1 adds "An entry below nought is a return: pallets the lot takes back into stock." No clause gives a return's timing; 2.2 still speaks only of a dispatched pallet; 5.3 still bills only receipt and dispatches, so a return is unbilled uniquely. No example added. |
| r5 N1 (polish) receipt fee range | accept | 1.4: "Every rate and every receipt fee is a whole number from 0 to 100,000." |
| r5 P1 (polish) reach wording | accept | Instruction: "Whatever no clause reaches keeps ..." |

Package, model, Oracle and T2 unchanged.
