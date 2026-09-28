# Contract review r2: tbrain-cell-line-passage-doubling

Scope: I read the r2 packet fresh — only `instruction.md` and `environment/`. The package source, the driver and the example are unchanged in substance from r1. The redesign sits in these places:
- SOP 1.1: whole numbers are JSON integers.
- SOP 2.3: the "failed count" term and the aside about other laboratories are removed.
- SOP 2.5: new term "in use".
- SOP 2.6: removed.
- SOP 6.2: now "The PDL of a bank in use".
- The instruction's keep-today's-step sentence is reworded.

## Part 1: Contract review

### A. Inventory of graded values, and whether each is ruled

| Report value | Ruled by | Unruled case? |
|---|---|---|
| culture `id`, order | 7.1 | no |
| culture `line` | 7.2 (root of the lineage) | no |
| `passage` | 4.1, 4.2 (supplier thaw = `seed_passage`; bank thaw = the harvest's passage, no +1), 4.3 | no |
| `doublings` | 3.1 via 2.3 and 2.4 | **U1: when the harvest count or the seed count has viability < 70.0** |
| `pdl` | 4.1, 4.2, 4.3 | no (it depends on doublings, see U1b) |
| `flag` | 5.1, 5.2 on age, with `>` and a band of 3 (ties excluded by 1.5) | no |
| bank `bank`, order | 7.1 | no |
| bank `line` | not stated directly. It follows from 1.5 ("A bank holds vials of one line only") | no divergence possible |
| `vials_left` | 6.1 | no |
| bank `pdl` | 6.2 for a bank in use | **U2: a bank not in use (`vials_left` = 0)** |

### B. The unruled values

**U1: doublings when a count is not valid.**

(a) *Can a careful engineer tell it is unruled?* Yes, but only through a chain of definitions:
- 3.1 is written in terms of viable counts.
- 2.3 defines a viable count only "of a valid count" (viability ≥ 70.0).
- 2.4 gives the seed the viability of its source suspension's count, so a seed from a sub-70 thaw or harvest has no viable count.

Nothing now says so out loud. The r1 sentence "has no viable count" and SOP 2.6 are both gone. The only evidence is the qualifier "of a valid count", together with the fact that the 70.0 threshold would otherwise be dead text. That is enough for a careful reader: the term "valid count" is defined and used nowhere else, so its only possible job is to restrict.

The competing reading is the common laboratory practice of taking viable = cells × viability / 100 at any viability. A reader who treats "valid" as a label rather than a restriction gets a different number:
- Thaw at 100.0. C1: seeded 1e6, harvested 2e6, viability 50.0.
- Unruled reading: kept step gives 1.0. Viable-at-any-viability reading: log2(1e6/1e6) = 0.0.

(b) *What does the keep-today's-step sentence yield?* Today's step is `growth.doublings` = `log2(harvested/seeded)`. Both inputs are figures the SOP defines (the counts' cell numbers, 2.2 and 2.4). So the answer is `log2(harvested/seeded)` with no viability term, whichever of the two counts is invalid.

One tempting mixed reading uses "the figures the SOP does define" to put the valid side's viable count into the ratio:
- Thaw at 60.0. C1: seeded 1e6, harvested 4e6, viability 80.0.
- The contract gives 2.0. The mixed reading gives log2(3.2e6/1e6) = 1.678.

"As it does today" settles this in favour of 2.0. I think a careful engineer reaches one answer.

Inheritance: a child seeded from a sub-70 harvest is also unruled (2.4).
- C1 harvest at 50.0. C2 ← C1: seeded 1e6, harvested 2e6, viability 100.0.
- The contract gives 1.0. A reader who checks only the child's own harvest viability gets log2(2e6/(1e6×0.5)) = 2.0.

This is determinate, but it is the easiest slip in the task.

**U1b: PDL, age and flag downstream of a kept doublings value.**

"Every other step still follows the SOP". The 4.1 PDL rule exists; it is simply fed the kept doublings value. So PDL = source PDL + log2(harvested/seeded), and age and flag follow from that.

The reading "PDL is also unruled, so keep today's log-order per-line walk" is weak:
- 4.3 rules lineage-following independently of how the doublings were obtained.
- The instruction scopes preservation to "a figure … the SOP has no rule for", and PDL does have a rule.

I rate it polish at most. In r1 the words "every other figure that depends on it" said this directly; the new "every other step" wording is slightly less direct but still sufficient.

**U2: PDL of a bank not in use.**

(a) Clearly unruled. SOP 6.2 now scopes itself to "a bank in use", and 2.5 defines that term. This fixes r1-F1.

(b) Today's step (`banks.summarise`) overwrites `bank["pdl"]` at every freeze record in log order, so it ends on the PDL of the bank's **last freeze record in the log**. The freeze's PDL is a figure the SOP defines (6.2: the PDL of the harvest the freeze was taken from, under 4.1 and 4.3). So the value is the SOP-correct PDL of that last freeze's harvest, not today's log-order line-state number.

Two readings are possible:
- Take the stored number that today's walk produces (`frozen[id][0]`, the per-line state at freeze time) as "today's step" output.
- Recompute that input by the SOP.

The phrase "from the figures the SOP does define" plus "every other step still follows the SOP" rules out the first reading.

Example:
- Line seed 10. Lineage A: T1 → C1 (+3, pdl 13). Lineage B: T2 → C2 (+1, pdl 11).
- F1 ← C1 into bank B1. Log order: T1, C1, T2, C2, F1. One thaw of F1 empties the bank.
- The contract gives 13.0. Today's stored value would be 11.0 (line state after C2).

A second example, with two freezes of different PDL, the lower one frozen last, both emptied:
- Contract: the last freeze's PDL.
- Maximum-over-all-vials reading: the higher one.
- A reader who emits `null` breaks "add no … guard of your own".

With both instruction sentences in play I find this uniquely derivable.

### C. Findings

**F1: should-fix. U1 depends only on a definition chain, with a strong contrary expert habit.**

Citation, SOP 2.3: "The **viable count** of a valid count is its number of cells multiplied by its viability and divided by 100."

This is the only sentence that stops an agent from computing viable counts at every viability. Many laboratories do exactly that, and r2 deleted the text that had anticipated the habit ("Many laboratories take a viable figure at any viability…"). Counterexample above: 1.0 against 0.0.

It is still derivable. The 70.0 threshold has no other function, and the instruction flags "thaws and harvests counted at every viability from 1.0 to 100.0". But this is exactly the "bare unlabelled subtype excluded only by a domain-word definition chain" pattern. If the intent is for it to act as a trap, it passes the chain test (there is a chain and no competing positive enumeration), but it is borderline on expert instinct. To make it unambiguous without giving the answer away, add one neutral sentence such as "A count below 70.0 has no viable count."

**F2: polish. The seed's validity is inherited, and the text does not say so directly.**

Citation, SOP 2.4: "A seed is counted at the viability of the count of its source suspension."

The seed is not itself a suspension (2.1), so "valid count" (2.3, defined on counts of suspensions) applies to it only through this sentence. The result is determinate. Counterexample: C2 above, 1.0 against 2.0.

**F3: polish. Bank `line` has no explicit rule.**

7.1 lists bank `line`, but only 7.2 defines `line`, and only for cultures. 1.5 implies it ("A bank holds vials of one line only"), and every reading gives the same value, so there is no grading risk.

**F4: resolved from r1.** Integer output is now explicit in SOP 1.1 and 7.1 ("JSON integer").

**F5: none. Ranges and conventions are fully covered.**
- Ranges: every range has both a floor and a ceiling.
- Rounding: none.
- Ordering: explicit.
- Thresholds: `>` versus `>=` is made moot by the 10^-6 exclusion; the band is 3, stated.
- Asides: the thaw +1 aside remains (4.2).
- Open inputs: named in the SOP's own terms.
- The "no correction, exclusion or guard" line (7.2) matches the instruction.
- No SOP sentence positively governs U1 or U2.

### D. Hand witnesses

All witnesses use line L: `seed_pdl` 10, `seed_passage` 3, `max_pdl` 40, unless noted otherwise. None required a guess.

| # | Input (abridged) | Expected |
|---|---|---|
| W1 | T1: supplier thaw, 90.0. C1 ← T1: seeded 1e6, harvested 3e6, viability 80.0 | C1: passage 4, doublings log2(3e6·0.8 / (1e6·0.9)) = 1.415037, pdl 11.415037, flag "" |
| W2 | T1 at 69.9. C1 ← T1: 1e6 → 2e6 at 100.0 | doublings 1.0 (kept; the viable-at-any-viability reading gives 1.516636), pdl 11.0 |
| W3 | T1 at 70.0. C1 ← T1: 1e6 → 2e6 at 100.0 | doublings log2(2/0.7) = 1.514573 (70.0 is valid) |
| W4 | T1 at 100. C1 ← T1: 1e6 → 2e6 at 50.0 | doublings 1.0 (the viable reading gives 0.0). Then C2 ← C1: 1e6 → 2e6 at 100 gives doublings 1.0 (inherited invalid seed), pdl 12.0, passage 5 |
| W5 | T1 at 100. C1 ← T1: 1e6 → 8e6 at 100 (pdl 13). C2 ← C1: 1e6 → 2e6. Other lineages logged in between. C3 ← C1: 1e6 → 4e6 | C1: p4, pdl 13. C2: p5, pdl 14. C3: p5, pdl 15 |
| W6 | Continue W5. F1 ← C2, bank B, 2 vials. T2: vial F1, 100. C4 ← T2: 1e6 → 2e6 at 100 | C4: p6, pdl 15.0. Bank B: vials_left 1, pdl 14.0 |
| W7 | `max_pdl` 20. C1 ← supplier thaw: +9 → pdl 19 (NEAR). C2 ← C1: +1.5 → pdl 20.5 (LIMIT). C3 ← C2: 1e6 → 2.5e5 at 100 (−2) | C3: pdl 18.5, age 20.5 → LIMIT (not NEAR) |
| W8 | Bank B: F1 (harvest pdl 20, 1 vial), F2 (pdl 15, 2 vials). One thaw of F1 | vials_left 2, pdl 15.0 (in use, maximum over in-stock vials) |
| W9 | As W8, with F1 thawed once and F2 thawed twice | vials_left 0, pdl 15.0 (not in use: kept step, last freeze) |
| W10 | Lineages A and B interleaved as in U2(b). F1 ← C1 (pdl 13) after C2 (pdl 11). F1 thawed once | vials_left 0, pdl 13.0 (not 11.0) |

## Part 2: Solver-path screen

### A) Pre-mortem

A strong solver would do the following:
1. Read the SOP.
2. Rebuild `lineage.walk` as an id-keyed DAG of (passage, pdl, age, viability, line).
3. Fix the thaw handling (seed values with no +1; a bank thaw inherits from its freeze).
4. Switch the flag to age, with `>` and a band of 3.
5. Rebuild `banks` to track stock per freeze.

The bank-not-in-use case is now labelled "in use" in the rule sentence, so a solver that reads the instruction keeps the last-freeze overwrite. The exception is one that writes `max(...)` and patches the empty case with `None`.

The main risk is `growth.doublings`. A solver that implements "viable count = cells × viability / 100" without honouring "of a valid count" gets every sub-70 culture and its descendants wrong. Its self-written tests and fuzz reference share the same reading, so self-verification cannot catch it.

A careful Opus 5 / GPT-5.6-class solver will usually ask "what is the 70.0 threshold for?" and keep `log2(harvested/seeded)` there. That is the single decisive point. The secondary slip is missing the inherited invalid seed (F2).

### B) Scores (5 = strongly resists solving)

| Axis | Score | Reason |
|---|---|---|
| reference_unreachable | 1 | Closed-form DAG, about 80 lines. |
| authority_incomplete_for_grading | 1 | Every graded value is uniquely derivable. F1 is a readability risk, not a gap. |
| hidden_state_not_closed_form | 1 | None. |
| restraint_traps | 2 | One qualifying site: the U1 sub-70 doublings. It sits inside the doublings aggregate that the repair forces the solver to rebuild, and the exclusion comes only from the "valid count" definition chain. It passes the chain test, though expert instinct pushes the other way. U2 counts zero: "in use" is written into the rule sentence. |
| fuzz_blind_spot | 2 | Sub-70 counts and empty banks are easy to fuzz, but a self-built reference inherits the solver's reading. |

### C) Verdict

| Item | Value |
|---|---|
| self_verification_resistance | 2 |
| prediction | collapses |
| confidence | 0.55 |

Decisive reason: everything except the sub-70 doublings is stated outright, and the sub-70 case is resolved by keeping today's `growth.doublings` behind a threshold that a careful solver will notice is otherwise meaningless. At most one of two strong solvers is likely to slip.
