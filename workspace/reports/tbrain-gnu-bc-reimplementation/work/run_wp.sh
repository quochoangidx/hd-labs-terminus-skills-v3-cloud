#!/bin/sh
# run_wp.sh <id> <expected-failing-test>
cd /Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3
R=workspace/reports/tbrain-gnu-bc-reimplementation
CTRF_OUT="$PWD/$R/work/wp-$1.ctrf.json" python3 .agent/skills/terminus-regular-task-authoring/scripts/wrong_path_runner.py workspace/tasks/tbrain-gnu-bc-reimplementation \
  --id "$1" --patch "$R/wrong-paths/$1.patch" --expect-failing "test_outputs.py::$2" \
  --verifier "$PWD/workspace/tools/score.sh" --ctrf "$PWD/$R/work/wp-$1.ctrf.json" --receipt "$R/wrong-paths/$1.json" > "$R/work/wp-$1.log" 2>&1
python3 -c "import json; r=json.load(open('$R/wrong-paths/$1.json')); print('$1', r['status'], r.get('reward'), len(r.get('failed_test_ids',[])))" 2>/dev/null || { echo "$1 FAILED"; tail -5 "$R/work/wp-$1.log"; }
