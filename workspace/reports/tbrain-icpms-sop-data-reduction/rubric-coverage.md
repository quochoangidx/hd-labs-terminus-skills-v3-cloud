# Rubric coverage matrix — tbrain-trace-metal-batch-quantitation

| contract_id | source | observable_requirement | witness_ids | discrimination | coverage | criterion_id |
|---|---|---|---|---|---|---|
| calibration | SOP §2 | OLS with fitted intercept | test_calibration_line_has_fitted_intercept, test_section_one_limits_reached | cal-through-origin, c3-conc/counts/is_counts caps, p2/p8 is_counts floor 1024, p4 three-level guard, p5 slope floor, p7 reading clamp | covered | 1 |
| blank_mean | SOP §3–4 | mean of blank results anywhere | test_blank_level_is_mean_of_results_anywhere, test_nondetect_blanks_stay_out_of_the_mean, test_single_blank_result_is_the_level | blank-first-blank-only, blank-mean-of-all-blanks, c1-blanks-before-first-sample-only | covered | 2 |
| amount | SOP §5 | (reading − level) × dilution | test_blank_comes_off_before_dilution, test_section_one_limits_reached | amount-dilute-then-subtract, p1 amount cap 10^6, p6 spike dilution cap 250 | covered | 3 |
| flags | SOP §5 | ND/J/'' on corrected reading, a hair either side of each limit (SOP §1 margin, v9) | test_flags_judged_on_corrected_reading, test_flags_just_either_side_of_mdl_and_loq, test_section_one_limits_reached | flag-on-amount, p9-limit-tolerance-1e-4, c3-mdl/loq caps | covered | 4 |
| ccv_pass | SOP §6 | rounded 90.0–110.0 inclusive; recovery unrounded | test_ccv_pass_on_rounded_recovery_inclusive | ccv-exclusive/inclusive-unrounded, c8 floor/ceil, c1-ccv-recovery-reported-rounded | covered | 5 |
| bracketing | SOP §6 | both nearest CCVs must pass | test_bracketed_runs_need_both_ccvs, test_generated_batches | bracket-preceding-only, c14-bracket-uses-unrounded-pass | covered | 6 |
| spike_results | SOP §7 | (spike − parent)/added when both results | test_spike_recovery_of_results | spike-dilution-in-denominator, c8-spike-recovery-clamped | covered | 7 |
| blank_silence | SOP §3 last sentence + instruction silence clause | first blank reading / 0.0 | test_batch_without_blank_results_keeps_shipped_level | blank-no-results-zero, c4-no-blank-level-none, c13 | covered | 8, neg 13 |
| bracket_silence | SOP §6 + silence clause | nearest earlier CCV else true | test_unbracketed_runs_keep_shipped_check | bracket-either-side, unbracketed-is-not-ok | covered | 9, neg 15 |
| spike_silence | SOP §3/§7 + silence clause | /(added×dilution) for ND spike/parent | test_nondetect_spikes_keep_shipped_recovery | spike-added-for-every-spike, spike-nondetect-parent-as-zero, spike-result-on-spike-only | covered | 10, neg 14 |
| negatives | SOP §3 | no clamping below nought | test_readings_below_nought_are_not_clamped | blank-level-floor-zero, c8-amount-clamped | covered | 11 |
| driver | instruction ¶2 | driver byte-identical | test_driver_is_unchanged | driver-shim | covered | 12 |
| order/types | SOP §8 | run order, analyte order, exact types | test_report_order_and_types | c15 mutants, W01 | covered | 1-7 (every report is compared in order and type) |
| authority_tamper | instruction ¶1 | SOP is the authority | reads-expected-files, H01/H02 | harness bypass rejected | covered | neg 16 |
