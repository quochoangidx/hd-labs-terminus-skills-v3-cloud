#!/bin/bash
# Deterministic closure for tbrain-climate-observer-monthly-summary (authoring only): run from the repo root.
set -u
R=workspace/reports/tbrain-climate-observer-monthly-summary
T=workspace/tasks/tbrain-climate-observer-monthly-summary
S=.agent/skills/terminus-regular-task-authoring/scripts
export PYTHONDONTWRITEBYTECODE=1
find $T $R \( -name .DS_Store -o -name __pycache__ \) -prune -exec rm -rf {} +
export CTRF_OUT=${TMPDIR:-/tmp}/coopsum-wp-ctrf.json
python3 $S/fixture_bounds_check.py $T --spec $PWD/$R/ranges.json --adapter $PWD/$R/observe.py --output $R/receipts/fixture-bounds.json > $R/receipts/fixture-bounds.txt 2>&1; echo "fixture-bounds rc=$?"
run() { id=$1; shift; args=(); for t in "$@"; do args+=(--expect-failing "test_outputs.py::$t"); done
  python3 $S/wrong_path_runner.py $T --id $id --patch $R/wrong-paths/$id.patch --verifier workspace/tools/score.sh --ctrf $CTRF_OUT --receipt $R/wrong-paths/$id.json "${args[@]}" > $R/wrong-paths/$id.log 2>&1; echo "wrong-path $id rc=$?"; }
run D1_max_on_form_day test_rule_3_1_morning_maximum_on_the_day_before
run D2_precip_on_form_day test_rule_3_3_morning_precipitation_on_the_day_before
run D3_dd_from_unrounded_mean test_rule_4_4_degree_days_from_the_rounded_daily_mean
run D4_mean_of_daily_means test_rule_4_3_mean_of_a_well_observed_month
run D5_strict_temperature_thresholds test_rule_4_5_threshold_days_include_their_value
run D6_first_day_on_ties test_rule_4_2_tied_extremes_take_the_latest_day test_rule_5_4_tied_greatest_takes_the_latest_day
run D7_trace_as_hundredth test_rule_1_2_trace_counts_nought
run D8_strict_precip_thresholds test_rule_5_3_heavy_days_include_their_threshold
run T1_natural_shift_every_amount test_accumulated_amount_keeps_its_form_day
run T2_natural_new_formula_everywhere test_month_with_gaps_keeps_its_mean_of_daily_means
run T2_natural_null_when_incomplete test_month_with_gaps_keeps_its_mean_of_daily_means
run H01_driver_tampered test_submitted_driver_unchanged
run H02_read_sealed_expectations test_rule_3_1_morning_maximum_on_the_day_before
python3 $S/sound_verifier_sweep.py $T --catalog $R/sweep/catalog.json --out $R/sweep --verifier workspace/tools/score.sh --jobs 4 > $R/sweep/sweep.log 2>&1; echo "sweep rc=$?"
python3 $S/independence_check.py $T --model solution/model.py --package coopsum --report-json $R/independence.json > $R/receipts/independence.txt 2>&1; echo "independence rc=$?"
scripts/preflight.sh $T --strict --report-json $R/preflight.json --evidence-dir $R/preflight-evidence > $R/preflight.txt 2>&1; echo "preflight-strict rc=$?"
scripts/preflight.sh $T --strict --determinism --report-json $R/preflight-determinism.json > $R/preflight-determinism.txt 2>&1; echo "preflight-determinism rc=$?"
