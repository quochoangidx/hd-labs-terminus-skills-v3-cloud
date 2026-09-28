#!/bin/bash
# score-set.sh <task> <mutdir> <snapshot> <prefix>: score every mutant app in <mutdir> with the
# verifier of <task>, 4 at a time; receipts in ledger-receipts-p09c/<prefix>-<id>.json
ROOT=/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3
R=$ROOT/workspace/reports/tbrain-gnu-sed-reimplementation
export T=$1 M=$2 SNAP=$3 PFX=$4 R ROOT
cd "$ROOT"
one() {
  id=$1
  python3 "$R/rev7/receipt.py" "$R/ledger-receipts-p09c/$PFX-$id.json" "$SNAP" "mutant $id scored by the verifier of snapshot $SNAP" -- \
    CTRF_OUT="$R/p09c-rev1/$PFX-$id.ctrf.json" bash "$ROOT/workspace/tools/score.sh" "$T" "$M/$id/app" >/dev/null
  python3 - "$R/ledger-receipts-p09c/$PFX-$id.json" "$R/p09c-rev1/$PFX-$id.ctrf.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
try:
    c = json.load(open(sys.argv[2])); failed = [t["name"] for t in c["results"]["tests"] if t["status"] != "passed"]
except Exception as e:
    failed = f"no ctrf ({e})"
r["failed_tests"] = failed; json.dump(r, open(sys.argv[1], "w"), indent=1)
print(sys.argv[1].rsplit("/", 1)[1], r["stdout"].strip(), failed)
PY
}
export -f one
ls "$M" | grep -v '\.patch$' | xargs -P 4 -n 1 bash -c 'one "$0"'
