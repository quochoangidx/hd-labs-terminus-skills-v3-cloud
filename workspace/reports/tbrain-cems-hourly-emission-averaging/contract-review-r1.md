# Contract review r1: tbrain-cems-hourly-emission-averaging

Reviewer A. I read only the packet's instruction.md and environment/.

## Part 1: Contract findings

1. **should-fix: the reported concentration of a valid non-firing hour depends on what counts as an "input" and what counts as a "constant".**
   Rule 3.2 covers only firing hours: "(209 less the reference oxygen) divided by (209 less its oxygen average)". Rule 2.4 defines a firing hour by its oxygen average: "below 190 tenths". The procedure never says what a valid hour with an oxygen average of 190 or more reports, so the silence clause applies: "keeps the calculation the package performs for it today, with the package's own constants left at today's values; only the inputs ... which the procedure itself determines take the procedure's values". Today that calculation is `corrected()`, which uses AMBIENT_O2=210 and the cap `min(o2, 190)`. Reading 1 treats 210 and 190 as package constants and keeps them. Reading 2 treats "209" as a procedure-determined value and uses it. Reading 3 swaps in 209 everywhere and drops the cap.
   Counterexample: ref 30, one hour of four operating OK quarters with nox 100, o2 195, flow 1,000,000. Reading 1 gives 100*180/20 = **900**. Reading 2 (209, cap kept) gives 17900/19 = **942**. Reading 3 (209, no cap) gives 17900/14 = **1279**. The "own constants" wording points to 900, and I believe that is intended. A solver will still hesitate, because the natural repair of `corrected()` changes 210 to 209 in the same function. The value also feeds `days[].rolling`.
2. **should-fix: CAL-hour validity (2.3).** The rule reads "An operating hour holding a CAL record is also a valid hour when it has two valid readings or more." Two points are open:
   (a) Does a CAL record in a non-operating quarter count? Take quarters [load0 CAL, op OK, op OK, op MNT]. Read literally, the hour is valid. If only an operating quarter's CAL counts, it is a substitute hour.
   (b) Does the rule excuse MNT/OOC quarters in the same hour? Take [op CAL, op OK, op OK, op OOC]. Read literally, it is valid. A reader who thinks the rule only forgives the calibration quarter calls it a substitute.
   In both cases the output changes in `kind`, `valid_hours`, `nox`/`lb`, the neighbouring interpolations and the rolling averages. The literal reading is defensible, but domain instinct (Part 75-like: calibration is excused, OOC is not) pulls the other way.
3. **should-fix / trap: substitute hours that are not lost.** 4.1 makes every non-valid operating hour a substitute hour. 4.2 and 4.3 only govern *lost* hours, meaning hours with no valid reading at all. An hour with some valid readings but not all, such as [op OK, op MNT], is therefore silent. The silence clause keeps today's `fill()`, which carries forward the last valid hour's reported figures, or (0,0) if there is none. The natural repair rewrites `fill()` to interpolate every substitute hour. The instruction already calls this out ("hours the monitor lost are filled with whatever the last good hour said"), so the line is drawn with the authority's defined term "lost hour". It is fair, but it is the task's main restraint point.
4. **polish: 6.1 window unit.** "twenty-nine operating days before it" and "that operating day and the twenty-nine operating days before it" count operating days, not calendar days. That is clear enough. The package uses a calendar-span window, so the fix is forced.
5. **polish: exact half and sign.** 1.1 gives half-up. All quantities are non-negative within the section 1 ranges (209-190>0, 210-190>0), so the negative-half ambiguity never comes up. The ranges and floors in 1.3 and 1.4 are complete. No problem here.
6. **polish: silent-case enumeration in the instruction.** The listed open inputs (out-of-range figures, skipped, repeated or reordered quarter-hours, bad job files) are clean. An export that starts mid-hour gives a partial first hour. That is inside the contract ("starting at any quarter-hour") and is fully governed by 2.1 and 2.3 because only records present count. The package's `len(records)==4` check has to go.

Everything else is governed without ambiguity:
- The mass rate uses the measured NOx average (3.3 says so explicitly).
- Mass is rate × quarters/4, rounded once over the total.
- The rolling average is weighted by hour, using valid hours only.
- An exceedance is strictly "above".
- Lost hours use the nearest valid hour on each side across the whole job, averaged, with half rounding up.

## Hand-worked witnesses (ref/limit given; records [start, load, nox, o2, flow, code])

W1. ref 30. One record `2031-04-07 05:45, 1500, 1000, 30, 1000000, OK`.
- Firing, so nox = 1000*179/179 = **1000**.
- lb = 1.194e-7*100*1e6 = 11.94 lb/h, giving **119**.
- Mass is 119/4 tenths lb, so tons = 0.149 hundredths, giving **0**.
- days = [{2031-04-07, null, false}]. op=1, valid=1.

W2. ref 0. Four operating OK quarters, each nox 1000, o2 109, flow 10,000,000.
- nox = 1000*209/100 = **2090**.
- lb = 1.194e-7*100*1e7 = 119.4 lb, giving **1194**.
- tons = 1194/200 = 5.97, giving **6**.

W3. The same hour with only 2 operating quarters: lb 1194, mass 597 tenths lb, so tons = 2.985, giving **3**. The current package gives 6.

W4. ref 30. Quarters [op CAL, op OK (1000, 30, 4e6), op OK (1200, 50, 6e6), op MNT].
- Valid under the literal reading of 2.3 (guess, see finding 2).
- Averages are 1100/40/5e6, so nox = 196900/169, giving **1165**.
- lb = 1.194e-7*110*5e6*10 = 656.7, giving **657**.

W5. ref 30. Non-firing valid hour: 4 operating OK quarters at 100/195/1e6.
- nox = **900** (guess, package constants kept, see finding 1).
- lb = 11.94, giving **12**.

W6. Four operating hours in a row:
- H1 valid (1000, 119).
- H2 [op OK, op MNT] is a non-lost substitute, so it carries forward (**1000, 119**).
- H3 is all MNT, so it is lost.
- H4 valid (2000, 239).
- H3 = (1500, (119+239)/2 = **179**).

W7. Lost-hour tie: neighbours (1000, 100) and (1001, 101) give **(1001, 101)** (1000.5 and 100.5 both round up).

W8. Rolling: 30 operating days, calendar gaps allowed, each with one valid hour at conc 1000, limit 1000.
- Days 1–29 are null.
- Day 30 rolling is **1000**, exceed **false** because the rule says "above". The current package gives true.

W9. Rolling is weighted by hour: a window with 3 valid hours at 900 and 1 at 1300 gives **1000**, not the daily mean of 1100.

Guessed: W4 (CAL literal reading) and W5 (constants kept).

## Part 2: Solver-path screen

A) Pre-mortem. A strong solver reads DRP-4 and rewrites five things:
- `is_valid` (operating quarters plus the CAL rule);
- the averages over valid readings only;
- `corrected` changed to 209;
- `mass_rate` fed the measured average, and mass × quarters/4;
- `fill` with two-sided interpolation, and `rolling` on an operating-day window, weighted by hour, with `>`.

It then writes its own reference from the DRP text and fuzzes the package against it. That self-check is circular for every silent case, because the solver's own reference encodes the same interpretive choices. It will go wrong where the natural rewrite overreaches:
- (i) interpolating non-lost substitute hours inside the rebuilt `fill`;
- (ii) applying 209 or no cap to non-firing valid hours inside the rebuilt `corrected`;
- possibly (iii) a stricter CAL reading.

The instruction's silence paragraph is explicit, so a careful solver that enumerates "which case does no rule settle" will catch (i) and probably (ii).

B) Scores
- reference_unreachable: **2**. The authority is short and fully readable, and a reference is easy to write.
- authority_incomplete_for_grading: **2**. Findings 1 and 2 are real ambiguities, and that counts against the task, not as a point.
- hidden_state_not_closed_form: **1**.
- restraint_traps: **3**. Two traps sit inside aggregates the repair forces the solver to rebuild: non-lost substitute carry-forward in `fill`, and the non-firing constants/cap in `corrected`. The firing-hour exclusion follows a domain definition chain (2.4 + 3.2). CAL does not count, because it is written into the rule sentence.
- fuzz_blind_spot: **2**. Random fuzz hits both silent cases often, but only against a correct oracle, which the solver does not have.

C) self_verification_resistance: **3**. Prediction: **resists (narrowly)**, confidence low-medium (~55%). Decisive reason: both traps sit inside functions the repair must rewrite, and the solver's self-written reference shares its blind spots. But the instruction names the silence rule so plainly that one of two careful solvers could well get both right, and the ambiguity in finding 1 means that if the task does resist, it may be for defect reasons rather than difficulty.
