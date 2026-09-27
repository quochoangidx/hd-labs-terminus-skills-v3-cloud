#!/bin/bash
# reproduction receipts on the returned v8 snapshot, closure receipts on the repaired tree
cd /Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3
R=workspace/reports/tbrain-gnu-ed-reimplementation
WP=.agent/skills/terminus-regular-task-authoring/scripts/wrong_path_runner.py
RET=workspace/revision/fc57838e-86e3-431c-a65c-b8776a1f307e/v8/tbrain-gnu-ed-reimplementation
REP=workspace/tasks/tbrain-gnu-ed-reimplementation
one() { # snapshot id witness receipt tag
  export CTRF_OUT="$PWD/$R/revision-v8/work/ctrf/$2-$5.ctrf.json"
  python3 $WP $1 --id $2 --patch $R/wrong-paths/$2.patch --expect-failing "test_outputs.py::$3" \
    --verifier "$PWD/workspace/tools/score.sh" --ctrf "$CTRF_OUT" --receipt $4 > $R/revision-v8/work/$2-$5.log 2>&1
  python3 -c "import json; r=json.load(open('$4')); print('$5 $2', r['status'], 'reward', r['reward'], 'failed', r['failed_test_ids'])" 2>/dev/null || echo "$5 $2 ERROR"
}
NEW="k-suffix-ignored:test_addresses group-interval-refused:test_regex group-plus-optional-refused:test_regex backref-5-8-refused:test_regex filename-first-word:test_files_and_write four-address-slots:test_addresses"
if [ "${1:-all}" != "repaired" ]; then
  for pair in $NEW; do id=${pair%%:*}; w=${pair##*:}; one $RET $id $w $R/revision-v8/receipts/returned/$id.json returned; done
fi
if [ "${1:-all}" != "returned" ]; then
  for pair in $NEW; do id=${pair%%:*}; w=${pair##*:}; one $REP $id $w $R/wrong-paths/$id.json repaired; done
fi
echo DONE
