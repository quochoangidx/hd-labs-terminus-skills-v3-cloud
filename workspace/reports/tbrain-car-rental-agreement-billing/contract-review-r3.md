# Contract review r3 — tbrain-car-rental-agreement-billing

Diff vs r2: only manual rule 4.2 changed. It now reads "Every bill carries a time charge, a mileage charge, a fuel charge and a tax, and a rental's total is the four added together."

## Finding 2 (fuel charge when fuel_in ≥ fuel_out): CLOSED as ambiguity, residual trap-quality note
- 4.2 now says every bill has a fuel charge. That takes away the r2 argument that a non-refuelling rental "has no fuel charge, so nought". The fuel charge of such a rental now clearly exists and is a figure the manual gives no rule for (3.3 covers only refuelling rentals). The instruction's silence sentence therefore applies, and the kept value is today's (fuel_out − fuel_in) × fuel_rate. That value is uniquely derivable.
- No sentence governs the value or makes nought the only reading. Neither 3.3 nor 4.1 ("Fuel is not taxed") nor 4.2 fixes it.
- Witness: 2032-02-28T10:00→2032-03-01T11:00, odo 999900→300, fuel 2→6, rates 5000/20/700 → days 3, miles 400, time 15000, mileage 0, fuel −2800, tax 1238, total 13438. Equal fuel (5→5) → fuel 0 under every reading.
- Residual (polish, not a two-reading defect): the word "charge" can suggest a value ≥ 0, so a solver might still clamp a fuel credit to 0 out of instinct. No sentence supports the clamp, and the instruction forbids clamps the manual does not give. This remains the task's one restraint site. It now has a definitional chain behind it (4.2 says the figure exists, 3.3 is silent on it, so the silence clause keeps today's value), but it still faces a strong contrary instinct.

## Other r2 items
- N1 (nought reading of 2.3 for sub-day days): unchanged. It is still a weak should-fix. 4.2's "every bill carries a time charge" slightly strengthens the kept value of 1 day, because a time charge exists for every bill, but it does not fix its size.
- N2 (renumbering vs the "rule numbers do not move" claim): unchanged, polish.

## New two-reading sentences
None. The new 4.2 is consistent with 4.3 and with the README's bill keys.

## Departures and Part 2
- Departure list: unchanged from r2.
- Scores: unchanged except authority_incomplete_for_grading, which improves from 3 to 2 because the fuel nought reading is removed.
- Current scores: reference_unreachable 2, authority_incomplete_for_grading 2, hidden_state_not_closed_form 1, restraint_traps 2, fuzz_blind_spot 2, self_verification_resistance 2.
- Prediction: collapses, confidence medium-high. The only divergence left is a solver's clamping instinct on the fuel credit.
