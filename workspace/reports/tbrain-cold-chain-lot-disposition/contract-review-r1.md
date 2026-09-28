# Contract review r1: tbrain-cold-chain-lot-disposition

Packet read: `instruction.md`, `environment/Dockerfile`, `.dockerignore`, `app/README.md`,
`app/docs/qa-sop-lot-disposition.md`, `app/tools/coldchain_run.py`, `app/src/coldchain/*.py`,
`app/examples/depot-week/*`. Nothing else was opened.

## Part 1: Contract review

### Defect sites visible in the package (what the SOP requires the solver to change)

1. `attribution.attribute` gives interval minutes to the reading that closes the interval. SOP 3.1 gives them to the reading that opens it.
2. `attribute` also attributes the minutes of logger gaps. SOP 3.1 attributes logged intervals only, so a reading that opens a gap gets weight 0.
3. `GAP_MINUTES = 60` with a strict `>` test. SOP 2.4 says a gap is any interval over 30 minutes.
4. `band_of` uses `low <= temp < high`, so the labelled upper limit falls out of range. SOP 2.1 includes both limits.
5. `band_of` uses `temp >= band.lower` for bands above the range, so 25.0 is charged to `hot`. SOP 2.5 gives above-range bands an exclusive lower end, so 25.0 belongs to `warm`.
6. `band_of` charges readings outside the table's span to the outermost band (the loop's fall-through). SOP 2.6/3.2 charge excursion readings only, and those must lie inside the span. See finding F2.
7. `lot_band_minutes` takes the `max` over legs. SOP 4.1 says to sum them.
8. `remaining` ignores `prior_minutes`. SOP 4.2 subtracts them.
9. `KELVIN_OFFSET = 273.0`. SOP 1.3 uses 273.15.
10. The MKT is an unweighted mean. SOP 5.1 weights each reading by its attributed minutes.
11. The quarantine test uses `round(mkt, 1) > high`. SOP 1.2 and 6.2 require the unrounded value.
12. `report.hours` truncates. SOP 1.2 rounds to the nearest hundredth, which also matters for negative remaining allowances.

The instruction's symptom list points at 7, 8, 4, 9/10/11 and 3. The instruction does not signal 1, 2, 5, 6 or 12 directly, but the SOP text covers each of them.

### Findings

**F1 (blocking): MKT is undefined when no minute is attributed to any of a lot's readings, and section 1 admits such lots.**
SOP 1.4 allows "from 2 to 20,000 readings ... consecutive stamps from 1 to 1,440 minutes apart", and the instruction promises "exports of two readings" and "logger spacing from one minute to a full day". 5.1 weights "each reading ... by the minutes attributed to it". 3.1 attributes only logged-interval minutes.
Counterexample: one lot, one leg, readings `00:00,5.0` and `00:45,5.0`. The total weight is 0, so the weighted mean is 0/0. Possible readings:
- (a) The job crashes with ZeroDivisionError, and the whole 200-lot report is lost.
- (b) The step falls back to the unweighted mean, giving `mkt_c` 5.0 and `release`.
- (c) The step emits NaN, which is not a valid JSON number.
- (d) The silence clause applies: "that figure stays what the step makes of it now, from the figures the SOP does define". That would be the current unweighted formula, but with 273.15 or 273.0? The text doesn't say.

The instruction's left-open list names MKTs "inside the margins of 1.5". It does not name an undefined MKT. The disposition also depends on this value through 6.2. Fix: either exclude the case in 1.4 ("each lot has at least one logged interval") or add it to the left-open list, and make sure the generator never emits it.

**F2 (should-fix, borderline blocking): the silence clause competes with SOP 2.6/3.2 for readings outside the table's span.**
Instruction: "When one of the package's steps works out a figure the SOP gives no rule for, that figure stays what the step makes of it now". The package currently charges a 45.0 reading (span ends at 40.0) to `hot` and a -12.0 reading (span starts at -10.0) to `cold`. The SOP does govern this case, but only through a definition chain: 2.6 "within the table's span", then 3.2 "Each excursion reading is charged". It never says in so many words that an out-of-span reading is charged to no band.
Counterexample: range [2,8], bands cold [-10,2), warm (8,25], hot (25,40], hot allowance 2 h. One leg: `00:00,45.0`, `00:30,5.0`, `01:00,5.0`.
- Reading A, governed by the SOP: `band_hours.hot` = 0.0, `remaining.hot` = 2.0, MKT 38.2, `quarantine`.
- Reading B, kept as silent: `band_hours.hot` = 0.5, `remaining.hot` = 1.5, still `quarantine`.
With 150 minutes at 45.0, reading B gives remaining -0.5 and `reject`, while reading A still gives `quarantine`. So the disposition itself can flip.
Below the span, the freeze point is at or above the lowest band's lower end (1.4), so the lot is rejected either way. `band_hours.cold` still differs. Fix: add an explicit sentence such as "A reading outside the labelled range and outside the table's span is charged to no band", or state which case the silence clause is aimed at.

**F3 (should-fix): the silence clause has no identifiable target.**
Apart from F1 and F2, I could not find any figure a package step computes that the SOP leaves ungoverned. Handover time between legs is governed by 2.3 ("Within one leg's export"). The last reading of an export gets weight 0 under 3.1. "May be below nought" rules out a clamp. So the clause is either aimed at F1 or F2 (and then it is ambiguous as written) or it is a decoy. A reviewer should confirm with the author which case it means, and the text should name it.

**F4 (polish): the README and SOP 1.1 describe decimal places differently.**
README: "at most one decimal place". SOP 1.1: "given to one decimal place". Integers such as `25` in JSON are harmless because `float()` is exact. No output difference.

**F5 (polish): attribution for gap-opening readings in the MKT is inferred, not stated.**
5.1 says "the minutes attributed to it", and only 3.1 attributes minutes. That gives a clean chain: a gap opener gets weight 0. A one-line reminder in 5.1 ("a reading that opens a logger gap or ends its export carries no weight") would still head off a solver who keeps gap minutes for the MKT.
Counterexample: `00:00,12.0`, `00:45,5.0`, `01:00,5.0`. The contract gives MKT 5.0. Attributing the gap to its opener gives about 10.3.

**F6 (none): exact conventions are covered.**
- Hours are rounded to the nearest hundredth (1.2). A whole number of minutes is never halfway, since m/60·100 = 5m/3.
- The MKT is rounded to the nearest tenth, and 1.5 keeps it away from halves.
- Comparisons use unrounded values (1.2), with a 1.5 margin at the upper limit.
- Band ends are inclusive or exclusive as 2.5 states, the labelled range is inclusive (2.1), the gap test is `>30` (2.4), the unlogged test is `>120` (6.2), and the reject test is `<0` (6.1).
- Lot order and the decimal-point format are stated.
- Every numeric range in 1.4 has both a floor and a ceiling. Weights are ≥0 and minutes are integers, so a negative zero cannot appear in the hour figures. A −0.0 `mkt_c` for an MKT in (−0.05, 0) compares equal as a number.

### Hand-worked witnesses

Common record: range [2.0, 8.0], freeze 0.0, H 9880. Bands: cold [-10, 2) with 12 h, warm (8, 25] with 72 h, hot (25, 40] with 2 h. Each witness is a single-leg lot with no prior time unless stated.

| # | Input | Expected |
|---|---|---|
| W1 | `00:00,8.0` `00:30,8.0` `01:00,8.0` | band_hours all 0.0; remaining 12.0/72.0/2.0; unlogged 0.0; mkt 8.0 (not > 8.0) → `release` |
| W2 | `00:00,25.0` `00:20,5.0` `00:40,5.0` | warm 0.33, hot 0.0, remaining warm 71.67; MKT 19.655 → 19.7 → `quarantine` |
| W3 | `00:00,5.0` `00:45,5.0` `01:00,5.0` | weights 0/15/0; unlogged 0.75; mkt 5.0 → `release` |
| W4 | `00:00` `01:01` `01:11` `02:11` `02:21`, all 5.0 | gaps 61+60 → unlogged 121 min = 2.02 → `quarantine`; mkt 5.0 |
| W5 | prior hot 120; `00:00,25.1` `00:01,5.0` `00:02,5.0` | hot 0.02 (1 min); remaining hot −0.02 → `reject`. Truncation would give −0.01. |
| W5b | as W5 with prior hot 119 | remaining hot 0.0 → not rejected; MKT is well above 8 → `quarantine` |
| W6 | two legs A and B, each 19 readings of 10.0 at 10-min spacing (180 min each), handover 60 min | warm 6.0, remaining warm 66.0; unlogged 0.0 (handover is not an interval); mkt 10.0 → `quarantine` |
| W7 | `00:00,8.1` `00:01,8.0` … `01:00,8.0` (1 min at 8.1, 59 min at 8.0) | warm 0.02; MKT 8.00168 → reported 8.0 but `quarantine` (the unrounded value is > 8.0, beyond the 0.001 margin) |
| W8 | `00:00,-0.1` `00:10,4.0` `00:20,4.0` | cold 0.17; frozen → `reject` (a reading of exactly 0.0 would not be frozen) |
| W9 | `00:00,45.0` `00:30,5.0` `01:00,5.0` | reading A: hot 0.0, mkt 38.2, `quarantine` (guessed; see F2) |
| W10 | `00:00,5.0` `00:45,5.0` | undefined (see F1); I had to guess |

W9 and W10 are the witnesses where I had to guess.

## Part 2: Solver-path screen

**A) Pre-mortem.** A strong solver reads the SOP and diffs it against the six small modules. There are about 12 defects, each tied to a numbered rule. It rewrites attribution, band lookup, summation, prior subtraction and the weighted MKT, then checks itself by hand-building W1–W8-style fixtures. The code is short (about 150 lines) and the SOP is precise, so its self-written reference and the task's reference should match on nearly everything.

The likely failure points are the three things the instruction's symptom list does not signal:
- the exclusive lower end of above-range bands (25.0 goes to warm),
- readings outside the span (F2), where the silence clause may lead it to keep the current fall-through,
- the zero-weight MKT (F1), where it will crash, fall back, or add a guard it was told not to add.

Truncation versus rounding and gap-opener weights are easy catches. Beyond those spots, nothing in the task resists a careful solver.

**B) Scores** (5 = strongly resists solving)

| Axis | Score | Why |
|---|---|---|
| reference_unreachable | 1 | A closed-form reference follows directly from the SOP. |
| authority_incomplete_for_grading | 2 | F1 and F2 are real defects, not difficulty. Everything else is complete. |
| hidden_state_not_closed_form | 1 | Everything is deterministic from the files. |
| restraint_traps | 1 | Handover-not-an-interval and "may be below nought" are written into rule sentences (count 0). The out-of-span case has a definitional chain, but the instruction's silence clause competes with it, so it counts as a contract defect, not a point. |
| fuzz_blind_spot | 2 | Boundary values (25.0, 8.0, 30 vs 31 min, 120 vs 121 min) are easy to fuzz. Only readings outside the span and zero-weight lots sit off the obvious path. |

**C) Verdict**

- self_verification_resistance: 2
- prediction: collapses (both solvers fully solve), unless the hidden tests exercise F1 or F2, in which case failures come from contract ambiguity, not legitimate difficulty.
- confidence: medium-high
- decisive_reason: every defect maps to a single, explicitly numbered SOP rule in a small package, and the only places a strong solver can miss are the two contract gaps (a zero-weight MKT and out-of-span readings versus the silence clause), which have to be fixed, not counted as difficulty.
