# Scaffold five-axis answers (phase 1)

State table: not applicable (one-shot report, no stored state between runs).

## Rule x region (witness planned in phase 2; every row graded through the driver)

| Rule | Regions | Planned witness |
|---|---|---|
| 1.2 hours | 0; positive; negative remaining; m = 3k+1 / 3k+2 (x.x33, x.x67); largest lot time (12 x 20,000 x 1,440 min) | test_rule_1_2_hours_rounded_to_the_hundredth; test_section_one_limits_reached |
| 1.2/1.5 MKT tenth | negative, 0.x, above 40; hair either side of a half tenth (>= 0.0005 away) | test_rule_5_1_mkt_is_time_weighted_in_kelvin |
| 2.1 labelled range | reading = lower, = upper, lower-0.1, upper+0.1 | test_rule_2_5_band_ends |
| 2.4 logged/gap | spacing 1, 30, 31, 1,440 | test_rule_3_1_...; test_rule_3_3_... |
| 2.5 band ends | every inner and outer end, 1-3 bands per side, widths 0.5 and 40.0 | test_rule_2_5_band_ends |
| 2.6/3.2 beyond span (silent) | 0.1 beyond the top, far below the bottom, table ending at -40.0 / 60.0 (no beyond region) | test_reading_beyond_the_table_keeps_todays_band |
| 3.1 attribution | first reading, last reading, 1- and 30-minute intervals | test_rule_3_1_logged_interval_goes_to_the_reading_that_opens_it |
| 3.1 gap (silent) | gap first / last / between bands; gap of 31 and 1,440 | test_logger_gap_keeps_todays_attribution |
| 4.1 carry | 1 and 12 legs; shared export across lots | test_rule_4_1_band_time_carries_across_legs |
| 4.2 prior | 0, absent band, 120,000; remaining exactly 0 and -1 minute; allowance 0 and 2,000 | test_rule_4_2_prior_time_counts_against_the_allowance; test_rule_6_1_... |
| 5.1 MKT | ratio 5,000 / 20,000; temps -40.0 / 60.0; unequal weights; handover 0 / 1 / 30 / 31 / 2,880 | test_rule_5_1_...; test_mkt_of_a_lot_does_not_bridge_handovers |
| 6.1 reject | reading = freeze point (not frozen), 0.1 below; remaining 0 / -1 min | test_rule_6_1_frozen_reading_or_exhausted_allowance_rejects |
| 6.2 quarantine | MKT above the upper limit by >= 0.001 rounding onto it; unlogged 120 / 121 min | test_rule_6_2_mkt_compared_unrounded; test_rule_3_3_... |

## Global claims vs silence

- "a band's remaining allowance ... may be below nought": holds for every input, silent cases included.
- 5.1 "over every reading of every leg": total weight is positive for every legal leg (>= 2 readings, spacing >= 1), including gap-only legs, because gap minutes are attributed by today's step.

## Exact conventions (each with its anchor)

- hours to the nearest hundredth (1.2); MKT to the nearest tenth (1.2); kelvin = C + 273.15 (1.3);
  comparisons unrounded (1.2); report keys and lot order (README "Report").

## Numerics

- Hours are exact integer arithmetic in the model; 5m/3 never lands on a half, so float `round(m/60, 2)` agrees (fuzz receipt).
- MKT: exp(-20,000 / 233.15) ~ 1e-38, well inside double range; 1.5 margins (0.001 to the upper limit, 0.0005 to a half tenth) dwarf float error (~1e-11); model uses fsum.
- Temperatures are compared as written (one decimal); a reading and a band end with the same decimal text parse to the same double.

## Alternatives to run in phase 2

- attribution by a single pass that credits `minutes[i-1]` or `minutes[i]` by spacing (Oracle); a pairwise `zip` variant.
- band lookup by explicit two-sided ends plus an explicit outermost-band fallback.
