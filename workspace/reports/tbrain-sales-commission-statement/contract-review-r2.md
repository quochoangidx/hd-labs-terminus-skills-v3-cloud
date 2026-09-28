# Contract review r2: tbrain-sales-commission-statement

Scope: `contract-review-packet-r2/instruction.md` and `environment/` only. I diffed r2 against r1. The only edits are:

- instruction paragraph 2: the preservation clause
- README: the `bonus` key
- plan: 1.6, 2.3, 2.4 and 5.1

The code, driver and example are unchanged.

## Status of r1 findings

| # | Closed? | One value per case? | Evidence |
|---|---|---|---|
| F1 (courtesy age limit, 90 or 120) | **Closed** | Yes | Plan 5.1 now reads "The clawback window of a reversal is 120 days". The instruction now reads "an input of that calculation moves only where the plan states that figure for that same item". The plan states a window only for reversals, so a courtesy credit keeps `window_days` at 90. A courtesy credit of 30,000 at split 100, aged 91 to 120, gives **0**. The same credit aged 90 or less gives **2,400**. |
| F2 ("new-logo bonus" label) | **Closed** | Yes | The README now reads "the total of the first-order bonus lines". A trial first order (value under 250,000) keeps today's line: share under 10,000 gives **0**, otherwise 300 bp of the share. [200000, 100, true] gives **6,000**. [200000, 4, true] gives **0**. The plan states neither the floor nor the rate for a trial item, so neither moves. The 25,000 minimum payment is stated only for the due, so `bonus_floor` stays at 10,000. The trial-order flavour in plan 1.4 remains, but it is no longer contradicted by a label. |
| F3 (value or share thresholds) | **Closed** | Yes | Both definitions now say "whose amount credited" or "whose value", then "whatever the rep's split". [300000, 3, true] is new-logo, bonus **270**. A credit of 60,000 at split 50, aged 100, is a reversal, clawback **2,400**. |
| F4 (1.6 against 1.5 and the example) | **Closed** | Yes | 1.6 now limits the rep's own orders and credit-note raise dates to the window, and it says outright that a credit note's order may be booked earlier. The example's 2027-01-28 order is now inside the limits. |
| F5 ("reaches" the line against its amount) | **Closed in effect** | Yes | The wording of "reaches" is unchanged. The new clause resolves it at item level: a figure moves only where the plan states that figure for that item. 5.2 and 6.2 state that the line exists but give no amount for courtesy or trial items, so today's calculation is the only reading that yields a value. |

## New findings

1. **polish: the antecedent of "that figure" is loose.** The clause reads "an input of that calculation moves only where the plan states that figure for that same item". "That figure" has to mean "that input", but the nearest noun is the figure the package works out. Neither reading changes any value I can build: courtesy credit lines and trial bonus lines have no plan-stated input or result either way. Suggested wording: "moves only where the plan states that input for that same item".
2. **polish, no action needed:** the trial-order flavour in plan 1.4 still invites an expert to zero trial bonuses. The authority (6.2 plus preservation) and the README label now both point the other way, so this is difficulty, not a defect.

I found no new blocking or should-fix issues. The rounding, tie, ordering, range and output-key authorities are unchanged from r1 and still complete.

## Solver screen (short)

**Pre-mortem.** A strong solver maps the eight `USES` entries to plan rules. It has to split the two shared constants:

- `small_cents`: `bonus_floor` stays at 10,000; `minimum_payment` becomes 25,000.
- `window_days`: courtesy credits keep 90; reversals get 120.

The instruction now spells out item-level preservation, so a careful solver does this. It could still fail through the quick fix of editing `FIGURES` globally, or by zeroing trial bonuses on domain instinct. Self-fuzzing against its own reference catches neither.

| Axis | Score |
|---|---|
| reference_unreachable | 2 |
| authority_incomplete_for_grading | 1 (down from 2) |
| hidden_state_not_closed_form | 1 |
| restraint_traps | 3 (both sites are now clean: unlabelled subtypes via the 2.3 and 2.4 definition chains inside aggregates the solver rebuilds, tied to shared constants) |
| fuzz_blind_spot | 3 |

**Verdict**

- self_verification_resistance: 2
- prediction: collapses
- confidence: medium (about 65%)
- decisive_reason: The contract is now determinate and loudly flags the shared-constant preservation, so the only resistance left is solver carelessness (a global `FIGURES` edit or instinctive zeroing of trial bonuses), not ambiguity.
