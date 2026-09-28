# Contract review r1: tbrain-3pl-warehouse-client-billing (reviewer C)

Packet read: `instruction.md`, `environment/` (Dockerfile, .dockerignore, app/README.md, app/docs/billing-schedule.md, app/tools/stockbill_run.py, app/src/stockbill/*.py, app/examples/small-job.json). Nothing else opened.

The package has seven visible bugs, all named in the instruction: `on_hand` uses `<=`, weeks start on Mondays, one tier is used for the whole period (taken at `end`), dispatch handling is not multiplied by pallets, holidays are ignored, the latest revision is always used, and the discount is floored. There is one more bug the instruction does not name, which clauses 6.2/6.3 govern: the discount base is `amount`, but the schedule says "total of the lot's charges", and an open lot's storage is not a charge. The silence mechanism is 3.1 (no revision in force), 6.2 (open-lot storage charge) and "today's calculation".

## Part 1: contract findings

**F1 (blocking): the open-lot discount has at least three readings.**
Citation, 6.2: "The storage of an open lot is an accrual ... Where a rule needs the storage charge of an open lot, it gives no rule for the value it defines." Citation, 6.3: "its client's discount percentage of the total of the lot's charges".
- Reading A: 6.3 is fully governed. An open lot's charges are just its handling, so no rule "needs" an open-lot storage charge and the 6.2 sentence does nothing. Discount = round_half_up(pct x handling).
- Reading B: 6.3 does need that storage charge, which is exactly why 6.2 routes it to silence. The discount then keeps today's calculation on defined values: `amount * pct // 100` (floor).
- Reading B': same as B, but the 1.3 half-up rounding still applies, because 1.3 names "a discount (6.3)".

The 6.2 sentence is written in the same "gives no rule" style as the designed silence in 3.1. That strongly suggests the author meant something by it. But no rule literally consumes an open-lot storage *charge*.
Counterexample (W7): open lot, storage 1005, handling 1000, discount 10%. A gives 100 (net 1905), B gives 200 (net 1805), B' gives 201 (net 1804).
Fix: state the open-lot discount base positively. Either "an open lot's charges are its handling" or "an open lot's discount keeps ...", and drop or rewrite the 6.2 silence sentence.

**F2 (should-fix, close to blocking): the scope of the 3.1 silence ("the value it defines") is not pinned.**
Citation, 3.1: "where a rule needs the revision in force on such a day, it gives no rule for the value it defines". The instruction adds: "that value keeps the calculation the package makes for it today".
- Narrow reading: only the 3.2 value (the week's or movement's *rates*) is silent. That becomes today's `revisions[-1]`, and 4.3, 5.1 and 5.2 still govern the tier choice, the per-pallet multiplication and the after-hours selection.
- Cascade reading: 5.1/4.2 also "need" the revision in force, through the rate, so the billed amount for that movement or week is silent. Today's code then bills a dispatch at `rate x 1` and picks after-hours by weekends only.
- Tier sub-ambiguity: today's code computes the storage rate as `tier_rate(week_number(lot, end), latest)`. Does the silent week keep that whole expression, or only the revision choice?

Counterexample W8 (tier): the revision takes effect 2026-06-10 with storage [[3,100],[null,500]]. The lot is received 2026-05-25 with 1 pallet and stays open. Period is 2026-06-01..06-30. Weeks #2 (6/1) and #3 (6/8) are silent. Narrow/per-week gives 100+100+500+500+500 = **1700**. "Today's tier at end" gives 5x500 = **2500**.
Counterexample W9 (cascade): the revision takes effect 2026-06-15 with out=480. A dispatch of 10 pallets on Wed 2026-06-10 is within the period. Narrow gives **4800**; cascade gives **480**.
The instruction's "every other value still follows the schedule" leans towards narrow. A second engineer could still reasonably pick the cascade reading, or keep the end-week tier.
Fix: add a sentence such as "a week or movement with no revision in force takes its rates (storage scale and handling rates) from ...", naming exactly which value is silent.

**F3 (polish): 2.1 "each on its own date" versus 1.4.**
1.4 does not require dispatch dates to be distinct, but 2.1 can be read that way. It doesn't change any output, because on-hand and handling are additive, but the instruction's "dispatches that clause 1.4 does not allow" list makes it look as if same-date dispatches might be out of scope. Worth one clarifying word.

**F4 (polish): the instruction lists symptoms but not the discount-base bug.**
"a few discounts come out a cent short" covers rounding. The base change (charges versus amount) is visible only through 6.2/6.3. That is legitimate, since the authority governs it, but it is also exactly where F1 bites. It is also worth knowing that the example job has no open lot with a nonzero discount (BLUEHARBOR is at 0%), so the example never exercises this.

Items checked with no defect found:
- **Rounding:** 1.3 gives one site, half-up, and everything else is exact.
- **Ordering:** "in the job's order".
- **Output types:** "Counts and money are integers".
- **Numeric ranges:** every range in 1.4 has both a floor and a ceiling (period 0–61 days; 400-day window; lots 1–300; pallets 1–1000; dispatches 0–50 of 1–1000; clients 1–20; discount 0–50; revisions 1–6, strictly increasing; tiers 1–5 with lengths 1–52; rates 0–100000; holidays 0–60).
- **Left-open list:** it matches 1.4's "and for no others".
- **Silence boundary:** no authority sentence positively governs anything the instruction calls open. Apart from F1/F2, the governed/silent line uses the authority's own terms ("in force", "charge", "accrual").

## Witnesses (worked by hand, checked against my own scratch reference)

The client is on one revision effective 2026-01-01 unless noted. Handling rates are in=10, out=20, after_hours=50, and the discount is 0 unless noted.

| # | Input | Expected entry |
|---|---|---|
| W1 | Period 06-01..06-30; storage [[null,100]]; lot received Mon 06-01, 10 pallets, all 10 dispatched Mon 06-08 | closed, weeks 2, storage 2000, handling 100+200=300, amount 2300 |
| W2 | Period 06-01..06-28; received Wed 06-03, 1 pallet | open, weeks 4 (06-03/10/17/24; Monday-based code gives 3), storage 400, handling 10 |
| W3 | Storage [[3,100],[2,200],[null,300]]; received 05-18, 1 pallet; period June | weeks #3..#7: 100+200+200+300+300 = 1100 |
| W4 | Holiday Fri 06-19; storage 0; received 06-19 5 pallets; dispatch Mon 06-22 3 pallets | handling 5x50 + 3x20 = 310; weeks 2 (06-19, 06-26) |
| W5 | Revisions 01-01 (storage 100, out 20) and 06-10 (storage 1000, out 40); received 06-01 2 pallets, dispatched Fri 06-12 2 | storage 200+200=400 (both week starts are before 06-10); handling 20 + 2x40 = 100 |
| W6 | Storage 1000, in=5, out=0, 10%; period 06-01..06-07; received and dispatched 06-01, 1 pallet | closed, amount 1005, discount 101 (100.5 rounded up), net 904 |
| W7 | Open lot, storage 1005, handling 1000, 10% | **guess**: 100 (A) / 200 (B) / 201 (B'), see F1 |
| W8 | See F2 | **guess**: 1700 (narrow) or 2500 (end-tier) |
| W9 | See F2 | **guess**: 4800 (narrow) or 480 (cascade) |
| Ex | `examples/small-job.json` | my reference (readings A and narrow) gives total 197151; the shipped code gives 176000 |

## Part 2: solver-path screen

**A) Pre-mortem.** A strong solver would read the 8 short files and the 1-page schedule, then list the seven named bugs. Each maps to a one-line fix (`<` in on_hand, a receipt+7k loop, a per-week in-force revision plus tier, `x pallets`, holidays in is_out_of_hours, a half-up discount). It would write a ~60-line independent reference straight from the schedule, fuzz it against its patched package over the 1.4 envelope (leap days, year turn, 6 revisions, 5 tiers), and converge quickly, since everything is closed-form date arithmetic. The unnamed discount-base bug (charges versus amount) is visible from 6.2/6.3, and a careful solver catches it.

It can only go wrong at the interpretive sites:
- F1 (open-lot discount): the solver will probably pick reading A. Some solvers will read the 6.2 sentence as a deliberate silence and keep `amount*pct//100`.
- F2 (pre-earliest-effective weeks and movements): most will use latest-revision rates with the per-week tier. A literal "keep today's calculation" reader might keep the end-week tier.

Self-tests cannot detect any of these, because the solver's own reference encodes the same reading.

**B) Scores** (5 = strongly resists)
- reference_unreachable: **2**. The reference is short and fully derivable; the only unreachable parts are the ambiguous ones.
- authority_incomplete_for_grading: **1**. This is a defect score, not a point: F1 is blocking and F2 is should-fix. Everything else is complete.
- hidden_state_not_closed_form: **1**. Everything is deterministic calendar arithmetic.
- restraint_traps: **2**. One legitimate site: a week or movement before a client's earliest effective date must keep `revisions[-1]`, which sits inside the rate lookup the solver has to rebuild, and the natural expert instinct is the earliest revision or zero. The F1 site fails the screen (it has a competing positive reading), so it is a defect, not a point.
- fuzz_blind_spot: **2**. Differential fuzzing against one's own reference is blind only at the reading-dependent sites.

**C)**
- self_verification_resistance: **2**
- prediction: **collapses**. Both solvers are likely to fully solve if the grader uses reading A and the narrow per-week-tier silence. If the grader uses reading B or end-tier, the failures would come from contract ambiguity, not from difficulty.
- confidence: medium
- decisive_reason: every governed rule is a short closed-form fix a solver can re-derive and fuzz, and the only places that might resist are the ambiguous 6.2 open-lot discount and the scope of the 3.1 silence, which are contract defects rather than legitimate difficulty.
