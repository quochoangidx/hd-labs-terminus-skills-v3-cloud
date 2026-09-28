#!/bin/sh
# Rebuild every snapshot-bound receipt for the ed task.
cd /Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3
T=workspace/tasks/tbrain-gnu-bc-reimplementation
R=workspace/reports/tbrain-gnu-bc-reimplementation
find $T -name .DS_Store -delete
rm -rf $R/preflight-evidence
scripts/preflight.sh $T --strict --determinism --report-json $R/preflight.json --evidence-dir $R/preflight-evidence > $R/preflight.log 2>&1; echo "preflight exit=$?"
find $T -name .DS_Store -delete
printf '%s\n' 'product-full-scale test_arithmetic_and_scale' 'leading-zero-printed test_arithmetic_and_scale' 'column-per-number test_strings_and_print' 'constants-at-block-start test_numbers_and_bases' 'unary-minus-below-power test_relational_and_boolean' 'error-ends-program test_runtime_errors' 'sqrt-scale-ignores-argument test_builtin_functions' 'print-leaves-last test_assignment_and_variables' 'for-header-prints test_control_flow' 'array-values-aliased test_user_functions' 'delegate-to-system-bc test_printing_and_radixes' | xargs -P 2 -L 1 $R/work/run_wp.sh
python3 .agent/skills/terminus-regular-task-authoring/scripts/independence_check.py $T --model tests/test_outputs.py --package pybc --package bc --report-json $R/independence.json > /dev/null; echo "independence exit=$?"
python3 - <<'PY'
import json, hashlib, sys
sys.path.insert(0, '.agent/skills/terminus-regular-task-authoring/scripts')
from pathlib import Path
import panel_precheck as p
R = 'workspace/reports/tbrain-gnu-bc-reimplementation/'
m = json.load(open(R + 'verifier-matrix.json'))
m['ctrf']['sha256'] = hashlib.sha256(open(R + 'preflight-evidence/oracle-ctrf.json', 'rb').read()).hexdigest()
json.dump(m, open(R + 'verifier-matrix.json', 'w'), indent=1)
man = json.load(open(R + 'panel-precheck-manifest.json'))
man['task_snapshot_sha256'] = p.tree_hash(Path('workspace/tasks/tbrain-gnu-bc-reimplementation'))
json.dump(man, open(R + 'panel-precheck-manifest.json', 'w'), indent=1)
print('snapshot', man['task_snapshot_sha256'])
PY
find $T -name .DS_Store -delete
python3 .agent/skills/terminus-regular-task-authoring/scripts/panel_precheck.py --manifest $R/panel-precheck-manifest.json --full --profile builder_certified --output $R/panel-precheck.json $T | python3 -c "import json,sys; d=json.load(sys.stdin); print('precheck', d['status'], d['blockers'], d['warnings'])"
