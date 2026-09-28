#!/bin/bash
# score every wrong path through wrong_path_runner.py with workspace/tools/score.sh
cd "$(dirname "$0")/../../../.." || exit 2
R=workspace/reports/tbrain-supplier-rebate-settlement
T=workspace/tasks/tbrain-supplier-rebate-settlement
declare -a W=(
 "W01-invoice-date-for-every-line test_rule_3_1_carton_shipment_counts_by_receipt"
 "W02-tier-on-gross test_rule_3_5_tier_is_picked_on_net_purchases"
 "W03-strict-threshold test_rule_2_6_net_exactly_on_a_threshold"
 "W04-handling-25 test_rule_3_3_returns_less_40_cents_a_unit"
 "W05-bonus-on-all-net test_rule_4_1_growth_bonus_on_the_increase"
 "W06-minimum-5000 test_rule_6_2_minimum_settlement"
 "W07-rebate-truncated test_rule_3_6_volume_rebate_rounded_half_up"
 "W08-shared-small-credit-edited test_tidy_up_notices_keep_todays_credit"
 "W09-no-credit-for-tidy-ups test_tidy_up_notices_keep_todays_credit"
 "W10-notice-cutoff-removed test_tidy_up_notices_keep_todays_credit"
 "W11-shared-unit-handling-edited test_price_match_sales_keep_todays_chargeback"
 "W12-no-chargeback-for-price-match test_price_match_sales_keep_todays_chargeback"
 "W13-shift-every-line test_loose_units_keep_their_invoice_quarter"
 "W14-drop-loose-lines test_loose_units_keep_their_invoice_quarter"
 "H01-driver-tampered test_submitted_driver_unchanged"
 "H02-read-sealed-expectations test_generated_jobs"
)
for row in "${W[@]}"; do
  set -- $row
  (
  export CTRF_OUT=$PWD/$R/wrong-paths/.$1.ctrf.json
  python3 .agent/skills/terminus-regular-task-authoring/scripts/wrong_path_runner.py $T --id "$1" \
    --patch $R/wrong-paths/$1.patch --expect-failing "test_outputs.py::$2" --verifier workspace/tools/score.sh \
    --ctrf "$CTRF_OUT" --receipt $R/wrong-paths/$1.json > /dev/null 2>&1
  mv "$CTRF_OUT" $R/wrong-paths/$1.ctrf.json 2>/dev/null; rm -f "${CTRF_OUT%.json}.log"
  python3 -c "import json; r=json.load(open('$R/wrong-paths/$1.json')); print(r['wrong_path_id'], r['status'], 'reward', r['reward'], 'failed', [t.split('::')[-1][:40] for t in r['failed_test_ids']])"
  ) &
  while [ $(jobs -r | wc -l) -ge 4 ]; do sleep 1; done
done
wait
