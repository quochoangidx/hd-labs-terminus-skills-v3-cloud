#!/bin/sh
# grade_mut.sh <mutant-id>: grade one mutant app with the task verifier and list failing tests
cd /Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3/workspace
R=reports/tbrain-gnu-dc-reimplementation/work
CTRF_OUT=$PWD/$R/mut/$1.ctrf.json tools/score.sh tasks/tbrain-gnu-dc-reimplementation $PWD/$R/mut/$1/app >/dev/null 2>&1
python3 - "$R/mut/$1.ctrf.json" "$1" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))["results"]["tests"]
print(sys.argv[2] + ":", [t["name"].split("::")[-1] for t in d if t["status"] != "passed"])
PY
