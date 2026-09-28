#!/bin/bash
# close.sh SLUG MODEL PKG — deterministic closure for one task; all receipts under reports/SLUG/.
set -uo pipefail
export PYTHONDONTWRITEBYTECODE=1
S=$1; M=$2; PKG=$3
REPO=/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3; cd $REPO
R=workspace/reports/$S; T=workspace/tasks/$S; B=workspace/reports/batch-task-batch-5
find $T -name .DS_Store -delete; find $T -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null
rm -rf $R/wrong-paths $R/preflight-final-logs
scripts/preflight.sh $T --strict --determinism --report-json $R/preflight-final.json --evidence-dir $R/preflight-final-logs > $R/preflight-final.txt 2>&1; echo "preflight exit=$? $(tail -1 $R/preflight-final.txt)"
grep -E '^(FAIL|WARN)' $R/preflight-final.txt
python3 $B/gen_wrong.py $S --run 2>&1 | grep -E 'rejected|ACCEPTED|could not|note:|Error' 
python3 $B/gen_matrix.py $S preflight-final-logs
python3 $B/gen_manifest.py $S --snapshot auto
echo "independence: documented exception (reports/$S/independence-exception.md)"
python3 .agent/skills/terminus-regular-task-authoring/scripts/panel_precheck.py $T --manifest $R/panel-precheck-manifest.json --full --profile builder_certified --output $R/panel-precheck.json > /dev/null; echo "precheck exit=$?"
python3 -c "import json; d=json.load(open('$R/panel-precheck.json')); print(d['status'], d['task_snapshot_sha256'], d['blockers'], [w['code'] for w in d['warnings']])"
