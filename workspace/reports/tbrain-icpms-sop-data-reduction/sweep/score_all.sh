#!/bin/bash
# score_all.sh: grade every sweep patch and legacy wrong path once (reference tree + patch), list failing tests.
set -uo pipefail
REPO=/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3; cd $REPO
S=tbrain-icpms-sop-data-reduction; T=workspace/tasks/$S; R=workspace/reports/$S
OUT=$R/sweep/scores; mkdir -p $OUT
for p in ${@:-$R/sweep/*.patch $R/wrong-paths/*.patch}; do
  id=$(basename $p .patch); W=$(mktemp -d); cp -R $T $W/t
  (cd $W/t/environment && git apply --unidiff-zero $REPO/$p) || { echo "$id APPLY-FAIL"; continue; }
  CTRF_OUT=$REPO/$OUT/$id.json workspace/reports/batch-task-batch-5/score_app.sh $W/t $W/t/environment/app >/dev/null
  python3 -c "
import json,sys; d=json.load(open(sys.argv[1])); f=[t['name'].split('::')[-1] for t in d['results']['tests'] if t['status']!='passed']
print(sys.argv[2], 'reward='+('1' if not f else '0'), ' '.join(f))" $OUT/$id.json $id 2>/dev/null || echo "$id NO-CTRF"
  rm -rf $W
done
