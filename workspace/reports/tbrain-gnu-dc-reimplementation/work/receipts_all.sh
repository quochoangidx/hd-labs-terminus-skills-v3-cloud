#!/bin/sh
# Rebuild every snapshot-bound receipt for the ed task.
cd /Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3
T=workspace/tasks/tbrain-gnu-dc-reimplementation
R=workspace/reports/tbrain-gnu-dc-reimplementation
find $T -name .DS_Store -delete
rm -rf $R/preflight-evidence
scripts/preflight.sh $T --strict --determinism --report-json $R/preflight.json --evidence-dir $R/preflight-evidence > $R/preflight.log 2>&1; echo "preflight exit=$?"
find $T -name .DS_Store -delete
printf '%s\n' "mul-full-scale test_arithmetic" "hex-lowercase test_parameters" "no-line-split test_printing" "empty-register-l-nothing test_registers" "Z-counts-leading-zeros test_status_inquiry" "q-one-level test_strings_and_macros" "negcmp-ignored test_strings_and_macros" "delegate-to-system-dc test_options_and_files" | xargs -P 2 -L 1 $R/work/run_wp.sh
python3 .agent/skills/terminus-regular-task-authoring/scripts/independence_check.py $T --model tests/test_outputs.py --package pydc --package dc --report-json $R/independence.json > /dev/null; echo "independence exit=$?"
python3 - <<'PY'
import json, hashlib, sys
sys.path.insert(0, '.agent/skills/terminus-regular-task-authoring/scripts')
from pathlib import Path
import panel_precheck as p
R = 'workspace/reports/tbrain-gnu-dc-reimplementation/'
m = json.load(open(R + 'verifier-matrix.json'))
m['ctrf']['sha256'] = hashlib.sha256(open(R + 'preflight-evidence/oracle-ctrf.json', 'rb').read()).hexdigest()
json.dump(m, open(R + 'verifier-matrix.json', 'w'), indent=1)
man = json.load(open(R + 'panel-precheck-manifest.json'))
man['task_snapshot_sha256'] = p.tree_hash(Path('workspace/tasks/tbrain-gnu-dc-reimplementation'))
json.dump(man, open(R + 'panel-precheck-manifest.json', 'w'), indent=1)
print('snapshot', man['task_snapshot_sha256'])
PY
find $T -name .DS_Store -delete
python3 .agent/skills/terminus-regular-task-authoring/scripts/panel_precheck.py --manifest $R/panel-precheck-manifest.json --full --profile builder_certified --output $R/panel-precheck.json $T | python3 -c "import json,sys; d=json.load(sys.stdin); print('precheck', d['status'], d['blockers'], d['warnings'])"
