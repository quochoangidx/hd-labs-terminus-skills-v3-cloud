#!/bin/sh
# Rebuild every snapshot-bound receipt for the ed task.
cd /Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3
T=workspace/tasks/tbrain-gnu-grep-reimplementation
R=workspace/reports/tbrain-gnu-grep-reimplementation
find $T -name .DS_Store -delete
rm -rf $R/preflight-evidence
scripts/preflight.sh $T --strict --determinism --report-json $R/preflight.json --evidence-dir $R/preflight-evidence > $R/preflight.log 2>&1; echo "preflight exit=$?"
find $T -name .DS_Store -delete
printf '%s\n' 'leftmost-first-regex test_only_matching' 'first-pattern-wins test_only_matching' 'word-first-match-only test_mixed_6' 'no-group-separator test_context' 'binary-prints-lines test_binary_input' 'null-data-ignored test_null_data' 'missing-file-not-error test_files_and_status' 'max-count-ignored test_output_controls' 'delegate-to-system-grep test_null_data' | xargs -P 2 -L 1 $R/work/run_wp.sh
python3 .agent/skills/terminus-regular-task-authoring/scripts/independence_check.py $T --model tests/test_outputs.py --package pygrep --package grep --report-json $R/independence.json > /dev/null; echo "independence exit=$?"
python3 - <<'PY'
import json, hashlib, sys
sys.path.insert(0, '.agent/skills/terminus-regular-task-authoring/scripts')
from pathlib import Path
import panel_precheck as p
R = 'workspace/reports/tbrain-gnu-grep-reimplementation/'
m = json.load(open(R + 'verifier-matrix.json'))
m['ctrf']['sha256'] = hashlib.sha256(open(R + 'preflight-evidence/oracle-ctrf.json', 'rb').read()).hexdigest()
json.dump(m, open(R + 'verifier-matrix.json', 'w'), indent=1)
man = json.load(open(R + 'panel-precheck-manifest.json'))
man['task_snapshot_sha256'] = p.tree_hash(Path('workspace/tasks/tbrain-gnu-grep-reimplementation'))
json.dump(man, open(R + 'panel-precheck-manifest.json', 'w'), indent=1)
print('snapshot', man['task_snapshot_sha256'])
PY
find $T -name .DS_Store -delete
python3 .agent/skills/terminus-regular-task-authoring/scripts/panel_precheck.py --manifest $R/panel-precheck-manifest.json --full --profile builder_certified --output $R/panel-precheck.json $T | python3 -c "import json,sys; d=json.load(sys.stdin); print('precheck', d['status'], d['blockers'], d['warnings'])"
