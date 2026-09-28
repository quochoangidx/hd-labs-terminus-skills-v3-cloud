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
LIST="backref-run-memo-shared:test_regex open-repeat-cap-64:test_regex global-f-refused:test_global_commands global-file-commands-refused:test_global_commands v-allows-nested-global:test_global_commands ere-upper-bound-unchecked:test_regex_extended marks-a-b-x-only:test_addresses line-number-cap-33:test_addresses offset-magnitude-2:test_addresses bare-signs-max-3:test_addresses s-count-cap-64:test_regex"
for pair in $LIST; do
  id=${pair%%:*}; w=${pair##*:}
  one returned $RET $id $w &
  one repaired $REP $id $w &
  wait
done
# finding 11: an entry point in source that imports the editor from a compiled .pyc under /app
for tag in returned repaired; do
  S=$RET; [ $tag = repaired ] && S=$REP
  export CTRF_OUT="$PWD/$R/work/ctrf/pyc-submission-$tag.ctrf.json"
  out=$(bash workspace/tools/score.sh $S $R/work/pyc-submission/app)
  python3 - "$S" "$tag" "$out" "$CTRF_OUT" <<'PY'
import sys, json, pathlib
sys.path.insert(0, ".agent/skills/terminus-regular-task-authoring/scripts")
from revision_ledger_check import tree_hash
S, tag, out, ctrf = sys.argv[1:5]
c = json.load(open(ctrf))
failed = [t["name"] for t in c["results"]["tests"] if t["status"] != "passed"]
p = pathlib.Path("workspace/reports/tbrain-gnu-ed-reimplementation/revision-b06-rev1/receipts") / tag / "pyc-submission.json"
json.dump({"schema_version": 1, "task_snapshot_sha256": tree_hash(pathlib.Path(S)), "finding": "11",
           "submission": "work/pyc-submission/app: /app/pyed/ed.py is source and imports the reference editor compiled to /app/pyed/implementation.pyc",
           "reward": out.strip().split("=")[-1], "failed_tests": failed}, open(p, "w"), indent=1)
print("pyc", tag, out.strip(), failed)
PY
done
echo DONE
