# Contract recheck r5: tbrain-3pl-warehouse-client-billing (reviewer C)

Packet read: `contract-review-packet-r5/instruction.md` and `environment/` only. I diffed it against r4.

The changes are:
- the instruction's silence paragraph;
- 1.2, which adds "the receipt fee is in cents per receipt";
- 1.4, where the revision contents change from "four handling rates" to "a storage scale, a receipt fee and three handling rates".

The package code, README and example are unchanged, so the r4 defect list (8 defects) and witnesses W1–W9 stand. The example total is still 222454.

## Does the new silence paragraph read one way?

The new text: "Each clause reaches exactly the lots, entries and figures that its defined terms cover, and no further. Whatever a clause does not reach keeps what the package does with it today, worked out from the values the schedule does define, and every value worked out from it in turn still follows the schedule. Add no exception, clamp or guard of your own."

**Yes, in substance.** Moving the silence test from "no rule for a value" to "reach of defined terms" suits the two remaining traps, because both hang on defined terms in 2.1 ("A receipt is an arrival of one pallet or more"; "A dispatch is an entry of one pallet or more"). The r4 source of misreading, the example "such as pallet counts of nought or below" next to "inputs the schedule does not provide for", is gone. "Of your own" also makes clear that the package's existing `if pallets < 1: continue` in `handling` stays, and that 2.1's one-pallet condition is part of the clause, not a guard.

Only one wording nit (P1 below): "Whatever *a* clause does not reach" literally means "whatever some clause misses". The intended meaning is "whatever no clause reaches". Read literally, it would undo every rule, because each value is missed by most clauses, so no competent reader will take that reading.

## Is every kept value still uniquely derivable?

| Kept value | Which clause stops short | Today's behaviour on defined values | Unique? |
|---|---|---|---|
| When a return (entry below 0) changes on-hand | 2.2's next-day sentence reaches only "a dispatched pallet". 2.2's first sentence ("entries ... change them") reaches returns but gives no timing. | `on_hand`: `when <= day`, so the change applies on the entry day | **Yes.** Even the reading that "entries change them" applies from the entry date, by analogy with "on hand from its `received` date", gives the same day. W6: on-hand 8 on Mon 06-08; storage 4200, not 3900. |
| Receipt handling for a 0-pallet arrival in the period | 5.1 and 5.2 reach only "a receipt" (one pallet or more). 5.3 sums "its receipt", and there is none. | `lot["pallets"] * rate` = 0, no fee | **Yes: 0** under both the silence route and the 5.3 route. W7: handling 0, not 1000. |
| Zero entries | Not a dispatch | Subtract 0 | Yes, and inert. |
| Returns in handling | Not reached by 5.1 or 5.2, and 5.3 sums only dispatches | Skipped by the existing `pallets < 1` check | Yes: 0 by both routes. |

No other package behaviour falls outside every clause. Peak with no billed week (4.5, "nought"), billed storage (4.4, "Any other lot's"), and storage with no billed weeks (4.3) are all positively governed.

## New findings

**N1 (polish, should be fixed before freeze): the receipt fee has no numeric range.**
1.4 now reads "Every revision holds a storage scale, a receipt fee and three handling rates ... Every rate is a whole number from 0 to 100,000." Because the fee is now listed separately from "rates", the closing sentence no longer clearly covers it. Under r4's "four handling rates" it did. The fee therefore has no floor or ceiling, and only 1.2 ("Money is in whole cents") implies it is an integer.
The output formula is linear in the fee, so no two readings give different outputs for an integer fee. The divergence is about scope: a fee of -500 or 250000 is either in scope and must be billed as given, or it is a "rate outside the limits" and open.
Fix: "Every rate and every receipt fee is a whole number from 0 to 100,000."

**P1 (polish): "Whatever a clause does not reach"** should be "Whatever no clause reaches". I found no counterexample that a reasonable reader would produce.

I found no competing positive sentence in the authority for either kept value.

## r4 polish points

| r4 | Status |
|---|---|
| F1: no-guard example could be over-read against the fee's one-pallet test; "not provide for" misnamed in-scope inputs | **Closed.** The example and the "does not provide for" phrase are removed; the text is now "no exception, clamp or guard of your own". |
| F2: 1.2 said handling rates are "per pallet moved" while the fee is per receipt | **Closed** (1.2 now adds "the receipt fee is in cents per receipt"). The fix introduced N1. |
| F3: the example exercises neither trap | **Open (polish, unchanged).** The example is unchanged: BH-0921's -2 is on Tue 06-16, not a week start, and there is no 0-pallet lot. This is acceptable. |

## Part 2 (brief)

- reference_unreachable: **2**
- authority_incomplete_for_grading: **1**. No two-reading output divergence (N1 affects scope only).
- hidden_state_not_closed_form: **1**
- restraint_traps: **3**. Two legitimate sites, both inside aggregates the repairs force the solver to rebuild and both excluded by a definition in 2.1:
  1. same-day timing for returns inside `on_hand`;
  2. no fee or `in` charge on a 0-pallet arrival inside the rebuilt receipt branch.
- fuzz_blind_spot: **3**. A return on a week start and a 0-pallet lot in the period are corners that self-fuzz reproduces with the solver's own reading.
- self_verification_resistance: **3**
- prediction: **resists** (I expect at least one of two solvers to miss the return timing or the 0-pallet fee).
- confidence: medium-low
- decisive_reason: the contract now reads one way and every kept value is uniquely derivable. What remains is whether a solver notices that 2.1's "one pallet or more" definitions keep same-day return timing and the no-fee 0-pallet arrival outside the obvious `<` and fee fixes, and self-tests cannot surface that.
