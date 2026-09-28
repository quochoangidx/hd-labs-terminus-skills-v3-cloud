#!/bin/bash
# Reproduce the v6 size-cap finding on the returned snapshot and its closure on the repaired one.
set -u
ROOT=/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3
R=$ROOT/workspace/reports/tbrain-bakery-fleet-dispatch
RET=$ROOT/workspace/revision/f60dccff-203d-4d8c-a21e-6c733293dd9e/v6/tbrain-bakery-fleet-dispatch
REP=$ROOT/workspace/tasks/tbrain-bakery-fleet-dispatch
LEDGER=$ROOT/.agent/skills/terminus-regular-task-authoring/scripts/revision_ledger_check.py
CASES=$R/rev4-cases
rm -rf "$CASES"; mkdir -p "$CASES/padded"
cp "$REP"/solution/plans/*.json "$CASES/padded/"
python3 -c "import sys; open(sys.argv[1],'a').write(' '*5_000_001)" "$CASES/padded/harbour-lanes.json"
receipt() {  # name tree
  local name=$1 tree=$2 out rc snap
  out=$(cd "$CASES" && DISPATCH_PLANS="$CASES/padded" python3 -I -m pytest -p no:cacheprovider -q "$tree/tests/test_outputs.py" 2>&1); rc=$?
  snap=$(python3 "$LEDGER" "$tree" x --print-snapshot)
  python3 - "$R/$name.json" "$tree" "$rc" "$snap" "$out" <<'PY'
import json, sys
path, tree, rc, snap, out = sys.argv[1:]
json.dump({"command": f"DISPATCH_PLANS=rev4-cases/padded python3 -I -m pytest -q {tree}/tests/test_outputs.py",
           "case": "reference plans, harbour-lanes.json padded with 5,000,001 trailing spaces (valid JSON, routes unchanged)",
           "exit_code": int(rc), "task_snapshot_sha256": snap, "tail": out.strip().splitlines()[-3:]},
          open(path, "w"), indent=2)
PY
  echo "$name rc=$rc"
}
receipt rev4-repro-size-cap "$RET"
receipt rev4-closure-size-cap "$REP"
