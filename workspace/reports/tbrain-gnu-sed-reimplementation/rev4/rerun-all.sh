#!/bin/bash
# Strict preflight on the current snapshot, then the wrong-path suite.
ROOT=/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3
R=workspace/reports/tbrain-gnu-sed-reimplementation
T=workspace/tasks/tbrain-gnu-sed-reimplementation
cd "$ROOT"
find "$T" -name .DS_Store -delete
rm -rf "$R/rev4/preflight-evidence"
scripts/preflight.sh "$T" --strict --determinism --report-json "$R/rev4/preflight.json" --evidence-dir "$R/rev4/preflight-evidence" > "$R/rev4/preflight.log" 2>&1
echo "PREFLIGHT exit=$?"
"$R/rev4/run-wrong-paths.sh" > "$R/rev4/run-wrong-paths.log" 2>&1
echo "WRONG-PATHS exit=$?"
