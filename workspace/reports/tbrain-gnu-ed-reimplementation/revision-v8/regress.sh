#!/bin/bash
# every manifest wrong path on the repaired tree (regression suite), plus the valid escape-crash submission on both snapshots
cd /Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3
R=workspace/reports/tbrain-gnu-ed-reimplementation
WP=.agent/skills/terminus-regular-task-authoring/scripts/wrong_path_runner.py
RET=workspace/revision/fc57838e-86e3-431c-a65c-b8776a1f307e/v8/tbrain-gnu-ed-reimplementation
REP=workspace/tasks/tbrain-gnu-ed-reimplementation
V8="k-suffix-ignored group-interval-refused group-plus-optional-refused backref-5-8-refused filename-first-word four-address-slots"
python3 - > /tmp/regress-list.txt <<'PY'
import json
d = json.load(open("workspace/reports/tbrain-gnu-ed-reimplementation/panel-precheck-manifest.json"))
for w in d["wrong_paths"]:
    r = json.load(open("workspace/reports/tbrain-gnu-ed-reimplementation/" + w["receipt"]))
    print(w["id"], ",".join(r.get("expected_failing_test_ids", [])) or "-")
PY
while read id wl; do
  case " $V8 " in *" $id "*) continue;; esac
  args=(); IFS=, read -ra ws <<< "$wl"; for w in "${ws[@]}"; do [ "$w" != - ] && args+=(--expect-failing "$w"); done
  export CTRF_OUT="$PWD/$R/revision-v8/work/ctrf/$id-regress.ctrf.json"
  python3 $WP $REP --id $id --patch $R/wrong-paths/$id.patch "${args[@]}" --verifier "$PWD/workspace/tools/score.sh" \
    --ctrf "$CTRF_OUT" --receipt $R/wrong-paths/$id.json < /dev/null > $R/revision-v8/work/$id-regress.log 2>&1
  python3 -c "import json; r=json.load(open('$R/wrong-paths/$id.json')); print('regress $id', r['status'], 'reward', r['reward'], r['failed_test_ids'])" || echo "regress $id ERROR"
done < /tmp/regress-list.txt
for tag in returned repaired; do
  S=$RET; [ $tag = repaired ] && S=$REP
  rm -rf /tmp/escapp-$tag; cp -R $S/environment/app /tmp/escapp-$tag; cp $S/solution/pyed/*.py /tmp/escapp-$tag/pyed/
  python3 - "$S" /tmp/escapp-$tag <<'PY'
import sys, os
s = open(os.path.join(sys.argv[2], "pyed/posixre.py")).read()
a = "        if n in table:\n            return table[n]"
assert s.count(a) == 1
open(os.path.join(sys.argv[2], "pyed/posixre.py"), "w").write(s.replace(a, "        if n in table:\n            raise SystemExit(\"unsupported escape\")"))
PY
  export CTRF_OUT="$PWD/$R/revision-v8/work/ctrf/escape-$tag.ctrf.json"
  out=$(bash workspace/tools/score.sh $S /tmp/escapp-$tag)
  python3 - "$S" "$tag" "$out" "$CTRF_OUT" <<'PY'
import sys, json, pathlib
sys.path.insert(0, ".agent/skills/terminus-regular-task-authoring/scripts")
from revision_ledger_check import tree_hash
S, tag, out, ctrf = sys.argv[1:5]
c = json.load(open(ctrf))
failed = [t["name"] for t in c["results"]["tests"] if t["status"] != "passed"]
p = pathlib.Path("workspace/reports/tbrain-gnu-ed-reimplementation/revision-v8/receipts") / tag / "excluded-escape-submission.json"
json.dump({"schema_version": 1, "task_snapshot_sha256": tree_hash(pathlib.Path(S)), "finding": "v8-1",
           "submission": "the reference, exiting on any of the GNU escapes the instruction excludes (evidence/excluded-escape-crashes.patch)",
           "reward": out.strip().split("=")[-1], "failed_tests": failed}, open(p, "w"), indent=1)
print("escape", tag, out.strip(), failed)
PY
done
echo DONE
