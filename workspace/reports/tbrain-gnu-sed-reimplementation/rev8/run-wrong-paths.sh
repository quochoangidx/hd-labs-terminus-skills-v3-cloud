#!/bin/bash
# rev8: every wrong path (rev7 regression suite + the v8 panel mutants) through the separate verifier.
ROOT=/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3
R=$ROOT/workspace/reports/tbrain-gnu-sed-reimplementation
T=$ROOT/workspace/tasks/tbrain-gnu-sed-reimplementation
S=$ROOT/.agent/skills/terminus-regular-task-authoring/scripts
export ROOT R T S
find "$T" -name .DS_Store -delete
cd "$ROOT"
[ -n "$WPLIST" ] || { cat "$R/rev7/wp-list.txt" > "$R/rev8/wp-list.txt"
cat >> "$R/rev8/wp-list.txt" <<'LIST'
long-line-chunked-reader test_sweep_long_lines
plus-offset-one-digit test_sweep_numbers
interval-bounds-one-digit test_sweep_numbers
cntrl-without-del test_sweep_classes
s-backslash-delimiter-rejected test_sweep_delimiters
empty-regex-bound-at-parse-time test_sweep_empty_regex
leading-hyphen-starts-range test_sweep_bracket_edges
readds-site-packages test_several_files
LIST
}
one() {
  id=$1; witness=$2
  cp "$R/rev8/wp-mut/$id.patch" "$R/wrong-paths/$id.patch"
  CTRF_OUT="$R/rev8/wp-$id.ctrf.json" python3 "$S/wrong_path_runner.py" "$T" --id "$id" --patch "$R/wrong-paths/$id.patch" \
    --expect-failing "test_outputs.py::$witness" --verifier "$ROOT/workspace/tools/score.sh" \
    --ctrf "$R/rev8/wp-$id.ctrf.json" --receipt "$R/wrong-paths/$id.json" > "$R/rev8/wp-$id.log" 2>&1
  echo "$id exit=$? $(tail -1 "$R/rev8/wp-$id.log")"
}
export -f one
xargs -P 4 -L 1 bash -c 'one "$0" "$1"' < "${WPLIST:-$R/rev8/wp-list.txt}"
echo ALL-DONE
