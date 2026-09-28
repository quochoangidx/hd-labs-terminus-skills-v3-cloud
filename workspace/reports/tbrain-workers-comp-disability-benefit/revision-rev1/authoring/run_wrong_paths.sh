#!/bin/bash
# run_wrong_paths.sh: score every wrong path through wrong_path_runner.py with workspace/tools/score.sh
cd "$(dirname "$0")/../../../../.." || exit 2
R=workspace/reports/tbrain-workers-comp-disability-benefit/revision-rev1
T=workspace/revision/5576eee5-02b0-40db-b2b7-4130441b597c/rev1/tbrain-workers-comp-disability-benefit
export CTRF_OUT=$PWD/$R/wrong-paths/.ctrf.json
declare -a W=(
 "W01-credit-by-payday-week test_rule_3_1_weeks_pay_counts_toward_the_week_it_pays"
 "W02-divide-by-weeks-paid test_rule_3_3_average_weekly_wage_divides_by_thirteen"
 "W03-sixty-per-cent test_rule_3_4_rate_is_two_thirds"
 "W04-newest-rate-row test_rule_2_4_row_in_force_on_the_date_of_injury"
 "W05-low-wage-lifted-to-minimum test_rule_3_5_low_wage_rate_is_the_aww"
 "W06-period-one-day-short test_rule_2_5_both_ends_of_a_period_count"
 "W07-seven-waiting-days test_rule_2_6_three_waiting_days"
 "W08-ttd-truncated test_rule_4_3_amount_rounded_to_the_cent"
 "W09-shift-every-line test_correction_below_a_weeks_pay_keeps_its_paydays_week"
 "W10-drop-lines-below-a-weeks-pay test_correction_below_a_weeks_pay_keeps_its_paydays_week"
 "W11-one-fraction-for-every-week test_week_below_1000_cents_keeps_todays_share"
 "W12-low-week-pays-nothing test_week_below_1000_cents_keeps_todays_share"
 "W13-low-week-uncapped test_week_below_1000_cents_keeps_todays_share"
 "W14-low-week-floored test_week_below_1000_cents_keeps_todays_share"
 "W15-maximum-floored test_rule_3_4_row_figures_at_their_ends_decide_the_rate"
 "H01-driver-tampered test_submitted_driver_unchanged"
 "H02-read-sealed-expectations test_generated_jobs"
)
for row in "${W[@]}"; do
  set -- $row
  scripts/python3 .agent/skills/terminus-regular-task-authoring/scripts/wrong_path_runner.py $T --id "$1" \
    --patch $R/wrong-paths/$1.patch --expect-failing "test_outputs.py::$2" --verifier workspace/tools/score.sh \
    --ctrf "$CTRF_OUT" --receipt $R/wrong-paths/$1.json > /dev/null 2>&1
  cp "$CTRF_OUT" $R/wrong-paths/$1.ctrf.json 2>/dev/null
  cp "${CTRF_OUT%.json}.log" $R/wrong-paths/$1.ctrf.log 2>/dev/null
  python3 -c "import json,sys; r=json.load(open('$R/wrong-paths/$1.json')); print(r['wrong_path_id'], r['status'], 'reward', r['reward'], 'failed', [t.split('::')[-1] for t in r['failed_test_ids']])"
done
rm -f "$CTRF_OUT" "${CTRF_OUT%.json}.log"
