#!/bin/bash
# every earlier manifest wrong path on the repaired tree (regression suite), three at a time
cd /Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3
R=workspace/reports/tbrain-gnu-ed-reimplementation
WP=.agent/skills/terminus-regular-task-authoring/scripts/wrong_path_runner.py
REP=workspace/tasks/tbrain-gnu-ed-reimplementation
mkdir -p $R/revision-b06-rev1/work/regress
python3 - > $R/revision-b06-rev1/work/regress-list.txt <<'PY'
import json
d = json.load(open("workspace/reports/tbrain-gnu-ed-reimplementation/panel-precheck-manifest.json"))
for w in d["wrong_paths"]:
    r = json.load(open("workspace/reports/tbrain-gnu-ed-reimplementation/" + w["receipt"]))
    print(w["id"], ",".join(r.get("expected_failing_test_ids", [])) or "-")
PY
run() {
  id=$1; wl=$2
  args=(); IFS=, read -ra ws <<< "$wl"; for w in "${ws[@]}"; do [ "$w" != - ] && args+=(--expect-failing "$w"); done
  export CTRF_OUT="$PWD/$R/revision-b06-rev1/work/regress/$id.ctrf.json"
  python3 $WP $REP --id $id --patch $R/wrong-paths/$id.patch "${args[@]}" --verifier "$PWD/workspace/tools/score.sh" \
    --ctrf "$CTRF_OUT" --receipt $R/wrong-paths/$id.json < /dev/null > $R/revision-b06-rev1/work/regress/$id.log 2>&1
  python3 -c "import json; r=json.load(open('$R/wrong-paths/$id.json')); print('regress $id', r['status'], 'reward', r['reward'], r['failed_test_ids'])" || echo "regress $id ERROR"
}
n=0
while read id wl; do
  run $id $wl &
  n=$((n+1)); if [ $((n % 3)) -eq 0 ]; then wait; fi
done < $R/revision-b06-rev1/work/regress-list.txt
wait
echo DONE
