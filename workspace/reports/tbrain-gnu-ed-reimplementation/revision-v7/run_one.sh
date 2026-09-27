#!/bin/bash
# run_one.sh <returned|repaired> <id> <witness>: one wrong path, receipt and CTRF under revision-v7
cd /Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3
R=workspace/reports/tbrain-gnu-ed-reimplementation
case $1 in
  returned) SNAP=workspace/revision/fc57838e-86e3-431c-a65c-b8776a1f307e/v7/tbrain-gnu-ed-reimplementation; RC=$R/revision-v7/receipts/returned/$2.json ;;
  repaired) SNAP=workspace/tasks/tbrain-gnu-ed-reimplementation; RC=$R/wrong-paths/$2.json ;;
esac
export CTRF_OUT="$PWD/$R/revision-v7/work/ctrf/$2-$1.ctrf.json"
python3 .agent/skills/terminus-regular-task-authoring/scripts/wrong_path_runner.py $SNAP --id $2 --patch $R/wrong-paths/$2.patch \
  --expect-failing "test_outputs.py::$3" --verifier "$PWD/workspace/tools/score.sh" --ctrf "$CTRF_OUT" --receipt $RC \
  > $R/revision-v7/work/$2-$1.log 2>&1
python3 -c "import json; r=json.load(open('$RC')); print('$1 $2', r['status'], 'reward', r['reward'], 'failed', len(r['failed_test_ids']))" 2>/dev/null || echo "$1 $2 ERROR"
