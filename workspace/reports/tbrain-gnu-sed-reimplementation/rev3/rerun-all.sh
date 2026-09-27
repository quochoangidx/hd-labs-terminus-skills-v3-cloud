#!/bin/bash
ROOT=/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3
R=$ROOT/workspace/reports/tbrain-gnu-sed-reimplementation
T=$ROOT/workspace/tasks/tbrain-gnu-sed-reimplementation
find "$T" -name .DS_Store -delete
"$R/rev3/run-wrong-paths.sh" > "$R/rev3/run-wrong-paths.log" 2>&1
cd "$ROOT" && scripts/preflight.sh "$T" --strict --determinism --report-json "$R/preflight.json" --evidence-dir "$R/preflight-evidence" > "$R/preflight.log" 2>&1
echo "RERUN-DONE preflight_exit=$?" >> "$R/rev3/run-wrong-paths.log"
