#!/bin/bash
# every wrong path of this revision on the returned snapshot (reproduction) and on the repaired one (closure)
cd /Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3
R=workspace/reports/tbrain-gnu-ed-reimplementation/revision-b06-rev1
WP=.agent/skills/terminus-regular-task-authoring/scripts/wrong_path_runner.py
RET=workspace/returned/tbrain-gnu-ed-reimplementation
REP=workspace/tasks/tbrain-gnu-ed-reimplementation
mkdir -p $R/work/ctrf $R/work/logs
one() { # tag snapshot id witnesses...
  tag=$1; S=$2; id=$3; shift 3
  args=(); for w in "$@"; do args+=(--expect-failing "test_outputs.py::$w"); done
  export CTRF_OUT="$PWD/$R/work/ctrf/$id-$tag.ctrf.json"
  python3 $WP $S --id $id --patch $R/wrong-paths/$id.patch "${args[@]}" --verifier "$PWD/workspace/tools/score.sh" \
    --ctrf "$CTRF_OUT" --receipt $R/receipts/$tag/$id.json < /dev/null > $R/work/logs/$id-$tag.log 2>&1
  python3 -c "import json; r=json.load(open('$R/receipts/$tag/$id.json')); print('$tag $id', r['status'], 'reward', r['reward'], 'failed', r['failed_test_ids'])" 2>/dev/null || echo "$tag $id ERROR"
}
LIST="v-allows-nested-global:test_global_commands"
for pair in $LIST; do
  id=${pair%%:*}; w=${pair##*:}
  one returned $RET $id $w &
  one repaired $REP $id $w &
  wait
done
echo DONE
