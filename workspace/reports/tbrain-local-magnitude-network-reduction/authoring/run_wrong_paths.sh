#!/bin/bash
# run_wrong_paths.sh: score every wrong path in wrong-paths/plan.json through wrong_path_runner.py
set -uo pipefail
ROOT=/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3
R=$ROOT/workspace/reports/tbrain-local-magnitude-network-reduction
T=$ROOT/workspace/tasks/tbrain-local-magnitude-network-reduction
cd $ROOT
for id in $(python3 -c "import json;print(' '.join(json.load(open('$R/wrong-paths/plan.json'))))"); do
  w=$(python3 -c "import json;print(json.load(open('$R/wrong-paths/plan.json'))['$id']['witness'])")
  ( export WP_CTRF=$R/wrong-paths/$id.ctrf.json
    python3 .agent/skills/terminus-regular-task-authoring/scripts/wrong_path_runner.py $T --id $id \
      --patch $R/wrong-paths/$id.patch --expect-failing "$w" --verifier $R/authoring/score_variant.sh \
      --ctrf $R/wrong-paths/$id.ctrf.json --receipt $R/wrong-paths/$id.json > $R/wrong-paths/$id.log 2>&1
    echo "$id rc=$?" ) &
  while [ "$(jobs -r | wc -l)" -ge 4 ]; do sleep 1; done
done
wait
