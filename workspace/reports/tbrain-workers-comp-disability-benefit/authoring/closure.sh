#!/bin/bash
# closure.sh: every phase-2 closure receipt, in order, on the task as it stands.
cd "$(dirname "$0")/../../../.." || exit 2
R=workspace/reports/tbrain-workers-comp-disability-benefit
T=workspace/tasks/tbrain-workers-comp-disability-benefit
S=.agent/skills/terminus-regular-task-authoring/scripts
find $T -name __pycache__ -prune -exec rm -rf {} + ; find $T $R -name .DS_Store -delete
rm -rf $R/preflight-evidence
scripts/preflight.sh $T --strict --report-json $R/preflight.json --evidence-dir $R/preflight-evidence > $R/preflight.txt 2>&1; echo "preflight --strict rc=$?"
scripts/preflight.sh $T --determinism --report-json $R/preflight-determinism.json > $R/preflight-determinism.txt 2>&1; echo "preflight --determinism rc=$?"
scripts/python3 $S/independence_check.py $T --model solution/model.py --package tdbenefit --report-json $R/independence.json > $R/receipts/independence.txt 2>&1; echo "independence rc=$?"
cp $R/preflight-evidence/oracle-ctrf.json $R/oracle-ctrf.json
python3 $R/authoring/make_matrix.py
scripts/python3 $S/verifier_architecture_check.py matrix $R/verifier-matrix.json --task-slug tbrain-workers-comp-disability-benefit > $R/receipts/verifier-architecture.txt 2>&1; echo "verifier-architecture rc=$?"
rm -f $R/wrong-paths/*.json $R/wrong-paths/*.log
$R/authoring/run_wrong_paths.sh | awk '{print "  " $1, $2, $3, $4}'
scripts/python3 $S/fixture_bounds_check.py $T --spec $R/bounds/ranges.json --adapter $R/bounds/observe.py --output $R/bounds/receipt.json > $R/bounds/receipt.txt 2>&1; echo "bounds rc=$? gaps=$(grep -c '^GAP' $R/bounds/receipt.txt)"
rm -rf $R/bounds/__pycache__
find $R/sweep -mindepth 1 -not -name catalog.json -exec rm -rf {} + 2>/dev/null
scripts/python3 $S/sound_verifier_sweep.py $T --catalog $R/sweep/catalog.json --out $R/sweep --verifier workspace/tools/score.sh --jobs 4 > $R/sweep/sweep.txt 2>&1; echo "sweep rc=$?"; grep -E 'BAD|as expected' $R/sweep/sweep.txt
D=.agent/skills/task-client-feedback-review/scripts
scripts/python3 $D/review_task.py $T > $R/review-task.txt 2>&1; echo "review_task rc=$?"
scripts/python3 $D/verifier_static_checks.py $T > $R/receipts/verifier-static-checks.txt 2>&1; echo "verifier_static_checks rc=$?"
find $T -name __pycache__ -prune -exec rm -rf {} +
SNAP=$(scripts/python3 $S/panel_precheck.py $T --manifest $R/panel-precheck-manifest.json --design-only --profile builder_certified | python3 -c "import json,sys; print(json.load(sys.stdin)['task_snapshot_sha256'])")
python3 - "$R/panel-precheck-manifest.json" "$SNAP" <<'PY'
import json, sys
m = json.load(open(sys.argv[1])); m["task_snapshot_sha256"] = sys.argv[2]; json.dump(m, open(sys.argv[1], "w"), indent=1)
PY
echo "snapshot $SNAP"
scripts/python3 $S/panel_precheck.py $T --manifest $R/panel-precheck-manifest.json --full --profile builder_certified --output $R/panel-precheck.json > $R/receipts/panel-precheck-full.txt 2>&1; echo "panel_precheck --full rc=$?"
find $T -name __pycache__ -prune -exec rm -rf {} +
