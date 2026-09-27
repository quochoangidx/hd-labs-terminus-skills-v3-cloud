#!/bin/bash
# close.sh: deterministic closure for tbrain-icpms-sop-data-reduction; receipts under reports/<slug>/
set -uo pipefail
export PYTHONDONTWRITEBYTECODE=1
REPO=/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3; cd $REPO
S=tbrain-icpms-sop-data-reduction; T=workspace/tasks/$S; R=workspace/reports/$S
find $T -name .DS_Store -delete; find $T -name __pycache__ -type d -prune -exec rm -rf {} +
rm -rf $R/preflight-evidence; rm -f $R/wrong-paths/*.json $R/wrong-paths/*.log
( scripts/preflight.sh $T --strict --determinism --report-json $R/preflight.json --evidence-dir $R/preflight-evidence > $R/preflight.txt 2>&1; echo "preflight exit=$?" ) &
( JOBS=${JOBS:-8} python3 $R/authoring/wrong_paths.py --run > $R/wrong-paths/run.txt 2>&1; echo "wrong paths: $(grep -c '^OK' $R/wrong-paths/run.txt) ok, $(grep -c '^BAD' $R/wrong-paths/run.txt) bad" ) &
wait
grep -E '^(FAIL|WARN)' $R/preflight.txt
python3 .agent/skills/terminus-regular-task-authoring/scripts/independence_check.py $T --model solution/model.py --model solution/jobgen.py --model solution/fixtures.py --model solution/seal.py --report-json $R/independence.json > /dev/null; echo "independence exit=$?"
python3 $R/authoring/gen_manifest.py
python3 .agent/skills/terminus-regular-task-authoring/scripts/panel_precheck.py $T --manifest $R/panel-precheck-manifest.json --full --profile builder_certified --output $R/panel-precheck.json > /dev/null; echo "precheck exit=$?"
python3 -c "import json; d=json.load(open('$R/panel-precheck.json')); print(d['status'], d['task_snapshot_sha256'][:16], d.get('blockers'), [w.get('code') for w in d.get('warnings',[])])"
