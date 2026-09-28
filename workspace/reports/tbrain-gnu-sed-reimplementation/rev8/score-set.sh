#!/bin/bash
# score-set.sh <task> <mutdir> <snapshot> <prefix>: score every mutant app in <mutdir>, 4 at a time,
# writing snapshot-bound receipts to ledger-receipts-v8/<prefix>-<id>.json
ROOT=/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3
R=$ROOT/workspace/reports/tbrain-gnu-sed-reimplementation
export T=$1 M=$2 SNAP=$3 P=$4 R ROOT
cd "$ROOT"
one() {
  id=$1
  python3 "$R/rev7/receipt.py" "$R/ledger-receipts-v8/$P-$id.json" "$SNAP" "mutant $id scored by the verifier of snapshot $SNAP" -- \
    CTRF_OUT="$R/rev8/$P-$id.ctrf.json" bash "$ROOT/workspace/tools/score.sh" "$T" "$M/$id/app"
}
export -f one
ls "$M" | grep -v '\.patch$' | xargs -P 4 -n 1 bash -c 'one "$0"'
for f in "$R"/ledger-receipts-v8/$P-*.json; do
  python3 - "$f" "$R/rev8/$P-$(basename "$f" .json | sed "s/^$P-//").ctrf.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
try:
    c = json.load(open(sys.argv[2]))
    failed = [t["name"] for t in c["results"]["tests"] if t["status"] != "passed"]
except Exception as e:
    failed = f"no ctrf ({e})"
print(sys.argv[1].rsplit("/", 1)[1], r["stdout"].strip(), failed)
PY
done
