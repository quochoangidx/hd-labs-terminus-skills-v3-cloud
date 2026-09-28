# Contract review r1: tbrain-supplier-rebate-settlement

Scope: instruction.md, environment/ (Dockerfile, README, schedule R-4, example, driver, src/rebate). Nothing else opened.

## Part 1: Contract review

### Deltas between the schedule and today's code (what a repair must change)
| Site | Today | Schedule |
|---|---|---|
| ledger.quarter_purchases | every line dated by invoice | carton (>=12 units, 2.2) counts at invoice+4 days (3.1); loose lines: no rule names a quarter, so they keep the invoice date |
| returns.HANDLING_PER_UNIT | 25 | 40 (3.3); the constant is shared with chargeback.py |
| tiers.tier_rate | `amount > threshold`, applied to **purchases** | at or above (2.6), applied to **net** (3.5) |
| tiers.volume_rebate | floor | half-up (1.1) |
| growth.growth_bonus | 200 bp of **net** | 200 bp of **net - prior** (4.1); the 110% test and prior>0 stay the same |
| chargeback | below >= 25 (HANDLING_PER_UNIT) | contract sale: below >= 100 (2.5) |
| protection | per-notice credit < 5000 -> 0, every notice | only price drops (>= 250 cents, 2.4) |
| settle.MINIMUM_CREDIT | 5000 | 25,000, paid when >= (6.2); the constant is also imported by protection.py |

### Findings
1. **should-fix: the preservation clause and the aggregate definitions in 5.1/5.2 pull in different directions.** Instruction: "a step it takes with an item, that no rule of the schedule reaches keeps the exact calculation today's code makes ... This comes before everything else". Schedule 5.1: "An account's price protection is the total of these credits"; 5.2: "An account's chargebacks are the total of these." A tidy-up notice (drop < 250) or a counter sale (below < 100) is not positively governed item by item, but the aggregate sentence closes the total over price drops and contract sales only. Counterexample: one notice in the quarter, old 1000, new 800, on_hand 100. Closed reading: protection = 0. Preservation reading: today's credit is 200*100 = 20000 >= 5000, so protection = 20000. The same applies to a sale with cost 1000, price 950, 100 units: 0 under the closed reading, 5000 under preservation. I think the closed reading is the intended one, because a total definition is a positive rule, but the words "comes before everything else" make the other reading defensible. Fix: add a sentence saying that a notice that is not a price drop earns no credit and a sale that is not a contract sale earns no chargeback, or state in the instruction that an aggregate defined by the schedule is reached as a whole.
2. **polish: hidden constant coupling.** `chargeback.py` imports `HANDLING_PER_UNIT` and `protection.py` imports `MINIMUM_CREDIT`. Under reading (1)-preserve, a solver that edits those constants silently changes the "preserved" figure. The instruction's "every constant of the package at its value today" covers this, so a careful reader resolves it. It is a trap rather than a defect, but it only matters if finding 1 is read the preserve way.
3. **polish: the loose-unit quarter is governed only by silence.** 3.2 says every line "counts toward exactly one quarter" but names none for lines under 12 units; 1.4 mentions a courier and gives no transit time. Under the preservation clause the invoice date stays, and there is no competing figure for the lag, so this is a sound restraint site and not a defect. Counterexample to check: 11 units invoiced 2027-09-30 counts in 2027-Q3, while 12 units invoiced the same day count in Q4.
4. **polish: negative-total paths.** When net < 0, rebate = 0 (no tier), and growth = 0 because the 110% test fails when prior > 0. Every other figure is non-negative, so the total is never negative and 6.2 needs no sign rule. This is closed.
5. Rounding, ordering, format, ranges: 1.1 gives half-up with a visible authority sentence, and it applies only to the rebate and growth. The 1.3–1.8 ranges all have a floor and a ceiling. The README fixes the keys, job order and integer values. I found no gaps.

### Witnesses (tiers from the example unless stated: 0->100 bp, 5,000,000->250, 20,000,000->400)
1. Example NW-0117 (2027-Q3): purchases 444000+1074000+356400 = 1874400; returns 24*(1850-40) = 43440; net 1830960; tier_bp 100; rebate 18310 (18309.6 rounded up); growth 0 (net < 110% of 4,100,000); protection 500*180 = 90000; chargebacks 290*40 = 11600; total 119910; paid 119910; carried 0.
2. Example SE-0402: purchases 105600 (invoiced 07-21, received 07-25), returns 0, net 105600, tier_bp 100, rebate 1056, growth 0 (prior 0), protection 0, chargebacks 0, total 1056, paid 0, carried 1056.
3. Q3 with a carton [2027-09-28, 12, 100] -> received 10-02 -> not in Q3 (purchases 0). Loose [2027-09-30, 11, 100] -> Q3, purchases 1100 (this assumes finding 3 is read as preserve).
4. Carton [2027-06-28, 12, 1000] in a Q3 job -> received 07-02 -> purchases 12000.
5. Net exactly 5,000,000 -> tier_bp 250, rebate 125000 (today: 100 bp on purchases, floored).
6. Purchases 0, return [in-quarter, 1, 100] -> returns 60, net -60, tier_bp 0, rebate 0.
7. prior 1,000,000, net 1,100,000 -> growth 2000. prior 1, net 2 -> growth half_up(1*200/10000) = 0. prior 1, net 1 -> 0 (the 110% test fails).
8. Tiers [0->100], net 150 -> rebate 2 (1.5 rounded up). Net 149 -> 1.
9. Notice drop 200 x 100 on hand -> protection 0. **I had to guess here** (finding 1; preservation gives 20000). Drop 250 x 100 -> 25000.
10. Total 24999 -> paid 0, carried 24999. Total 25000 -> paid 25000, carried 0.

## Part 2: Solver-path screen

**A) Pre-mortem.** A strong solver reads the 6-page schedule, lists the eight deltas above in about 10 minutes, and patches each module (every one is 1–3 lines). It writes a reference straight from the schedule and fuzzes it against the package; the reference comes from the same reading, so the self-check only confirms that reading. The likely failure points are these:
- (a) Adding a courier lag or folding loose lines into the carton rule. This is unlikely, because no number is given.
- (b) Missing that the tier moves from purchases to net. It is easy to see, since 3.5 is explicit.
- (c) Changing HANDLING_PER_UNIT to 40 without noticing that chargeback.py depends on it. This is harmless, because 2.5 re-fixes that threshold at 100.
- (d) Finding 1: whether tidy-ups and counter sales go to 0 or keep today's figure. This is the only real split, and it is a contract ambiguity, not honest difficulty.

Most strong solvers take the closed reading (0), so the task most likely collapses.

**B) Scores (5 = strongly resists)**
- reference_unreachable: 1. It is a small closed-form package with explicit rules.
- authority_incomplete_for_grading: 2. Finding 1 is the only material split, and it counts as a defect.
- hidden_state_not_closed_form: 1.
- restraint_traps: 2. The loose-unit quarter is a bare subtype excluded by the 2.2 definition inside the purchases aggregate the solver rebuilds (1 point). The tier-on-net and growth-on-excess changes are rule-sentence conditions and score 0. The tidy-up and counter-sale exclusions are conditions written through the 2.4/2.5 definitions, with natural fixes pointing the right way, so they score about 0. The shared-constant coupling adds a little.
- fuzz_blind_spot: 2. A carton near the quarter end, net on a threshold and the 25,000 boundary all appear readily under random fuzz within the 1.8 window.

**C)** self_verification_resistance: 2. Prediction: **collapses**. Confidence: medium-high. Decisive reason: every delta is spelled out as a numbered rule with an explicit constant, and the only restraint site (loose units) has no competing number to tempt a solver, so two strong solvers will both reach the full reference unless finding 1 splits the grading.
