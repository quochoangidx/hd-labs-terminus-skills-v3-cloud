# Contract review r1 — tbrain-car-rental-agreement-billing

Scope: instruction.md + environment/ only.

## Part 1 — contract review

### Findings

1. **BLOCKING — mileage allowance for a sub-day rental (length < 1,440) has two or three defensible readings.**
   Manual 2.4: "The allowance days of a rental are the charged days of a day rental." 3.2: "150 miles for each allowance day." Instruction: "Where the manual gives no rule for a figure ... that step keeps working the figure out the way it does today."
   - Reading A (definition chain 2.2→2.3→2.4): a non-day rental has no charged days as a day rental, so 0 allowance days, allowance 0, every mile charged.
   - Reading B (silent): allowance days for a sub-day rental are undefined, so the step keeps today's `days()` (=1). The allowance is then 150 (the manual's per-day figure) or 100 (today's constant, "the way it does today").
   - Counterexample (shipped example RA-10442, 330 min, 80 mi, 25 c/mi, day 3900): A gives mileage 2000, tax 487, total 6387. B gives mileage 0, tax 322, total 4222.
   2.4 never says "a rental that is not a day rental has no allowance days". It reads more like a restatement than a definition that excludes sub-day rentals. If A is intended, it needs one explicit sentence (e.g. "A rental that is not a day rental has no allowance days."). The instruction's phrase "from the figures the manual does define" pushes a reader toward B.

2. **SHOULD-FIX (restraint trap may fail the 0/8 screen) — the fuel charge when a car comes back fuller or level.**
   3.3 covers only "A refuelling rental's fuel charge". For any other rental the silence clause keeps today's `(fuel_out-fuel_in)*fuel_rate`, which is **negative** when fuel_in > fuel_out, and the instruction bans adding a clamp. The value can be derived uniquely from shipped code, but it runs against a strong expert instinct (a negative "charge", i.e. a fuel credit, with no fee). The instruction says graders use "any fuel level from empty to full", so this case will be graded. Witness 3 below shows it. The behaviour is defensible because the instruction says "Add no exception, clamp", but expect solvers to clamp to 0. Either make it deliberate with a manual sentence or accept it as a trap that is visible only through the silence clause.

3. **SHOULD-FIX — the days and time charge for a sub-day rental rest only on the silence clause.** 2.3 and 3.1 define charged days only for day rentals, so the silent step keeps ceil(len/1440) = 1, giving `days`=1 and time charge = day_rate. This is uniquely derivable and consistent, but it interacts with finding 1: a solver that sets allowance days = charged days = 1 for sub-day rentals is using the "kept" days as if the manual defined them.

4. **POLISH — tax rounding scope.** 1.2 "rounded to the nearest cent, an exact half cent going up" is clear, and every taxable amount is ≥ 0, so there is no negative-half ambiguity. Half-cent inputs exist: taxable ∈ {200, 600, 1000, ...} (e.g. 2 days × 100). OK.

5. **POLISH — 1.3 ranges.** Floors and ceilings are all present. The bound "miles driven at most 20,000" with turnover is fine. There is no bound on the fuel_in/fuel_out relationship, which is intended. The ranges for `revenue` and the output integers are implicit. That is fine.

6. **POLISH — ordering and format.** "in the order of the file" (README) is the authority. Output keys come from the README, and "compared exactly, as a JSON integer" is stated. Key order and whitespace are not graded, which is fine.

Goal clarity: good. The symptoms listed in the instruction map one to one onto the departures below.

### Departures of the shipped package from the manual
- time_charge.days: ceil (every day begun) vs 2.3's 59-minute grace (day rentals).
- mileage: 100 mi/day vs 150 (3.2). The allowance also uses `days` for sub-day rentals (see finding 1).
- mileage.miles: no odometer turnover (2.5).
- fuel: no 1,500 refuelling fee (3.3). (It also charges/credits non-refuelling rentals, which is silent and kept.)
- tax: taxes the fuel charge (4.1) and floors instead of rounding half-up (1.2).
- run/bill_run/clock: no departure found (clock handles leap days and year ends correctly via datetime).

### Witnesses (fields: days, miles, time, mileage, fuel, tax, total)
1. Example RA-10441: 09:15 → +3d 25min, 435 mi, fuel 8→6, rates 4900/35/650 → 3, 435, 14700, 0, 2800, 1213, 18713.
2. Example RA-10442 (sub-day): → 1, 80, 3900, **2000 or 0**, 0, **487 or 322**, **6387 or 4222**. GUESS: this depends on finding 1.
3. 2032-02-28T10:00 → 2032-03-01T11:00 (leap, 2 d 60 min → 3 days), odo 999900→300 (400 mi), fuel 2→6, 5000/20/700 → 3, 400, 15000, 0, **-2800**, 1238, 13438 (negative fuel is kept per the silence clause).
4. 2031-12-31T23:30 → 2032-01-07T00:29 (6 d 59 min → 6 days), odo 0→1100, fuel 8→0, 100000/0/0 → 6, 1100, 600000, 0, 1500, 49500, 651000.
5. 1-minute rental, fuel 3→3, 100/500/2000, 0 mi → 1, 0, 100, 0, 0, 8, 108 (both readings agree).
6. 2031-01-01T00:00 → 01-02T00:59 (1 d 59 min → 1 day), fuel 1→0, rates 121/0/0 → 1, 0, 121, 0, 1500, 10 (9.9825 rounds up), 1631.
7. Half cent: 2 days × 100, 0 mileage → taxable 200 → 16.5 → tax 17.
8. Revenue for a file of witnesses 1+4 = 18713+651000 = 669713; its tax = 1213+49500 = 50713.

## Part 2 — solver-path screen

A) Pre-mortem: a strong solver reads the manual, lists the five departures (they are all listed in the instruction prose too), and patches days, the 150 constant, turnover, the fee, and tax base plus rounding. It then writes a reference from the manual and fuzzes it inside 1.3. The reference and the patch come from the same reading, so the self-check agrees with itself. The failure points are exactly the two silent/definitional sites: (i) the sub-day allowance (a natural patch keeps `150*days(agreement)`, giving 150 free miles for sub-day rentals, or else writes `if length>=1440`), and (ii) the negative fuel for fuel_in > fuel_out (the instinct is to clamp, or to write `if fuel_in<fuel_out ... else 0`). Neither site is caught by self-tests, because the solver's reference shares its reading. Everything else is closed-form and easy.

B) Scores
- reference_unreachable: 2. The manual is short and closed-form. Only the silent cases resist.
- authority_incomplete_for_grading: 2. Finding 1 is genuine ambiguity, which is a defect.
- hidden_state_not_closed_form: 1.
- restraint_traps: 3. The fuel non-refuelling site sits inside the fuel step the solver must rebuild (fee), and the kept negative is derivable. The sub-day allowance uses a definition chain, but that chain is weak (finding 1), so it partly fails the screen. The fuel site faces strong contrary instinct, so it is also borderline under 0/8.
- fuel_blind_spot / fuzz_blind_spot: 3. Fuzzing inside 1.3 hits sub-day and fuel-gain cases often, but the solver's own reference encodes the same reading, so fuzzing cannot expose the error.

C) self_verification_resistance: 3. Prediction: collapses on the main path, resists only through the two silent sites. Confidence: medium. decisive_reason: all departures are enumerated in the instruction, and the remaining difficulty lies in the sub-day allowance and the negative fuel. The first is ambiguous and the second runs against instinct, so any resistance comes from contract defects rather than legitimate difficulty.
