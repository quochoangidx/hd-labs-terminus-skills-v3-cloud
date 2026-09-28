#!/bin/bash
ROOT=/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3
R=$ROOT/workspace/reports/tbrain-gnu-sed-reimplementation
T=$ROOT/workspace/tasks/tbrain-gnu-sed-reimplementation
S=$ROOT/.agent/skills/terminus-regular-task-authoring/scripts
export ROOT R T S
find "$T" -name .DS_Store -delete
cd "$ROOT"
one() {
  id=$1; witness=$2
  cp "$R/p09c-rev1/wp-all/$id.patch" "$R/wrong-paths/$id.patch"
  CTRF_OUT="$R/p09c-rev1/wp-$id.ctrf.json" python3 "$S/wrong_path_runner.py" "$T" --id "$id" --patch "$R/wrong-paths/$id.patch" \
    --expect-failing "test_outputs.py::$witness" --verifier "$ROOT/workspace/tools/score.sh" \
    --ctrf "$R/p09c-rev1/wp-$id.ctrf.json" --receipt "$R/wrong-paths/$id.json" > "$R/p09c-rev1/wp-$id.log" 2>&1
  echo "$id exit=$? $(tail -1 "$R/p09c-rev1/wp-$id.log")"
}
export -f one
xargs -P 4 -L 1 bash -c 'one "$0" "$1"' < "$R/p09c-rev1/wp-list.txt"
echo ALL-DONE
