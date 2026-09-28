#!/bin/bash
# score every wrong path through wrong_path_runner.py with workspace/tools/score.sh
cd "$(dirname "$0")/../../../.." || exit 2
R=workspace/reports/tbrain-sales-commission-statement
T=workspace/tasks/tbrain-sales-commission-statement
while IFS=$'\t' read -r id test; do
  (
  export CTRF_OUT=$PWD/$R/wrong-paths/.$id.ctrf.json
  python3 .agent/skills/terminus-regular-task-authoring/scripts/wrong_path_runner.py $T --id "$id" \
    --patch $R/wrong-paths/$id.patch --expect-failing "test_outputs.py::$test" --verifier workspace/tools/score.sh \
    --ctrf "$CTRF_OUT" --receipt $R/wrong-paths/$id.json > /dev/null 2>&1
  mv "$CTRF_OUT" $R/wrong-paths/$id.ctrf.json 2>/dev/null; rm -f "${CTRF_OUT%.json}.log"
  python3 -c "import json; r=json.load(open('$R/wrong-paths/$id.json')); print(r['wrong_path_id'], r['status'], 'reward', r['reward'], 'failed', [t.split('::')[-1][:40] for t in r['failed_test_ids']])"
  ) &
  while [ $(jobs -r | wc -l) -ge 4 ]; do sleep 1; done
done < $R/wrong-paths/map.tsv
wait
