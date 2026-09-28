#!/bin/bash
# every phase-2 closure receipt on the current snapshot
cd "$(dirname "$0")/../../../.." || exit 2
S=workspace/reports/tbrain-supplier-rebate-settlement
T=workspace/tasks/tbrain-supplier-rebate-settlement
P=workspace/local-solve-probes/tbrain-supplier-rebate-settlement-cycle-2
K=.agent/skills/terminus-regular-task-authoring/scripts
find $T -name __pycache__ -o -name .DS_Store | xargs rm -rf
python3 $K/fixture_bounds_check.py $T --spec $S/bounds/ranges.json --adapter $S/bounds/observe.py --output $S/bounds/receipt.json > $S/bounds/receipt.txt; echo bounds=$? ok=$(grep -c ^OK $S/bounds/receipt.txt)
python3 $K/instruction_preflight.py $T/instruction.md > $S/receipts/instruction-preflight.txt 2>&1; echo instruction=$?
rm -rf $S/preflight-evidence; scripts/preflight.sh $T --strict --report-json $S/preflight.json --evidence-dir $S/preflight-evidence > $S/preflight.txt 2>&1; echo strict=$?
cp $S/preflight-evidence/oracle-ctrf.json $S/oracle-ctrf.json
scripts/preflight.sh $T --strict --determinism --report-json $S/preflight-determinism.json > $S/preflight-determinism.txt 2>&1; echo determinism=$?
python3 $K/independence_check.py $T --model solution/model.py --report-json $S/independence.json > $S/receipts/independence.txt 2>&1; echo independence=$?
rm -f $S/wrong-paths/*.json; $S/authoring/run_wrong_paths.sh 2>&1 | awk '{print $1,$2,$3,$4}' | sort > $S/wrong-paths/summary.txt; echo wrong_paths_not_pass=$(grep -vc ' pass reward 0' $S/wrong-paths/summary.txt)
python3 $K/sound_verifier_sweep.py $T --catalog $S/sweep/catalog.json --out $S/sweep --verifier workspace/tools/score.sh --jobs 4 > $S/sweep/sweep.txt 2>&1; echo sweep=$? "$(tail -1 $S/sweep/sweep.txt | cut -c1-40)"
mkdir -p $S/rescore-cycle-2; for r in 1 2; do CTRF_OUT=$PWD/$S/rescore-cycle-2/run_$r.ctrf.json workspace/tools/score.sh $T $P/run_$r/solve/environment/app > $S/rescore-cycle-2/run_$r.txt 2>&1; echo run_$r $(cat $S/rescore-cycle-2/run_$r.txt) $(python3 -c "import json;d=json.load(open('$S/rescore-cycle-2/run_$r.ctrf.json'));print([t['name'].split('::')[-1] for t in d['results']['tests'] if t['status']!='passed'])"); done
python3 $S/authoring/make_matrix.py
python3 - <<'PY'
import json,sys
sys.path.insert(0,".agent/skills/terminus-regular-task-authoring/scripts")
from pathlib import Path
from panel_precheck import tree_hash
R="workspace/reports/tbrain-supplier-rebate-settlement/"
m=json.load(open(R+"panel-precheck-manifest.json")); m["task_snapshot_sha256"]=tree_hash(Path("workspace/tasks/tbrain-supplier-rebate-settlement"))
json.dump(m,open(R+"panel-precheck-manifest.json","w"),indent=1); print("snapshot", m["task_snapshot_sha256"])
PY
python3 $K/panel_precheck.py $T --manifest $S/panel-precheck-manifest.json --full --profile builder_certified --output $S/panel-precheck.json > $S/receipts/panel-precheck-full.txt 2>&1; echo precheck=$?
python3 -c "import json;d=json.load(open('$S/panel-precheck.json'));print(d['status'],[b['code'] for b in d['blockers']],[w['code'] for w in d['warnings']])"
